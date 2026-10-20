"""
Roles and state machine for the result-approval workflow.
Not wired into any view yet.
"""
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone
from django.db.models import Q
from django.db.models import Exists, OuterRef, Q
import logging

from django.contrib.auth import get_user_model

from .models import (
    ApprovalLog, AssessmentGrade, Grade, ResultApproval, Students, SubjectTermSetup,
)
from .models import (
    ApprovalLog, AssessmentGrade, Grade, ResultApproval, StaffNotification,
    Students, SubjectDepartment, SubjectTermSetup,
)

logger = logging.getLogger(__name__)

Status = ResultApproval.Status
Action = ApprovalLog.Action

LOCKED_STATUSES = (Status.PENDING_HOD, Status.PENDING_HEAD, Status.APPROVED)


class ApprovalError(Exception):
    """A move that is not allowed right now (wrong status, missing reason...)."""


# ---------------------------------------------------------------------
# ROLES: the only place that decides who can do what
# ---------------------------------------------------------------------

def _in_groups(user, names):
    return user.groups.filter(name__in=names).exists()


def is_final_approver(user):
    """Headteacher, deputy, admin."""
    return bool(
        user.is_superuser
        or getattr(user, 'is_headteacher', False)
        or getattr(user, 'is_deputy', False)
        or _in_groups(user, ['Headteacher', 'Admin', 'Deputy'])
    )


def can_reopen(user):
    """Headteacher and admin only (not deputy)."""
    return bool(
        user.is_superuser
        or getattr(user, 'is_headteacher', False)
        or _in_groups(user, ['Headteacher', 'Admin'])
    )


def is_subject_hod(user, subject):
    return subject.departments.head_of_department_id == user.pk


def can_submit(user, subject):
    return (
        subject.teacher_subject_id == user.pk
        or is_subject_hod(user, subject)
        or is_final_approver(user)
    )


def can_hod_review(user, subject):
    """The department's HOD. If the department has no HOD, headteacher level covers."""
    if is_subject_hod(user, subject):
        return True
    return subject.departments.head_of_department_id is None and is_final_approver(user)


def can_final_review(user, subject=None):
    return is_final_approver(user)


def can_reopen_result(user, subject=None):
    return can_reopen(user)


# ---------------------------------------------------------------------
# LOOKUPS (used by the locks and pages in later steps)
# ---------------------------------------------------------------------

def get_or_create_approval(subject, academic_year, term):
    approval, _ = ResultApproval.objects.get_or_create(
        subject=subject, academic_year=academic_year, term=term
    )
    return approval


def is_locked(subject, academic_year, term):
    """True when grades for this subject/year/term must not be changed."""
    return ResultApproval.objects.filter(
        subject=subject, academic_year=academic_year, term=term,
        status__in=LOCKED_STATUSES,
    ).exists()


# ---------------------------------------------------------------------
# THE ENGINE: one guarded move between statuses
# ---------------------------------------------------------------------

def _move(approval, user, *, allowed_from, to_status, action, permission,
          comment='', require_comment=False, apply=None):
    with transaction.atomic():
        locked = (
            ResultApproval.objects
            .select_for_update(of=('self',))
            .select_related('subject__departments')
            .get(pk=approval.pk)
        )

        if not permission(user, locked.subject):
            raise PermissionDenied("You are not allowed to do this.")

        if locked.status not in allowed_from:
            raise ApprovalError(
                f"This result is currently '{locked.get_status_display()}', "
                f"so that action is not available."
            )

        comment = (comment or '').strip()
        if require_comment and not comment:
            raise ApprovalError("Please give a reason.")

        old_status = locked.status
        locked.status = to_status
        if apply:
            apply(locked, user, comment, timezone.now())
        locked.save()

    ApprovalLog.objects.create(
        approval=locked, action=action, actor=user,
        from_status=old_status, to_status=to_status, comment=comment,
    )
    _notify_transition(locked, action, user, comment)
    return locked


def _set_publish_flag(approval, value):
    SubjectTermSetup.objects.filter(
        subject=approval.subject,
        academic_year=approval.academic_year,
        term=approval.term,
    ).update(is_published=value)


# ---------------------------------------------------------------------
# THE MOVES
# ---------------------------------------------------------------------

def submit_for_approval(approval, user):
    def apply(a, u, comment, now):
        a.submitted_by, a.submitted_at = u, now
        a.rejection_reason, a.rejected_at_stage = '', ''
        a.hod_reviewed_by = a.hod_reviewed_at = None
        a.head_reviewed_by = a.head_reviewed_at = None
        a.hod_note = a.head_note = ''

    return _move(approval, user,
                 allowed_from=(Status.DRAFT, Status.REJECTED),
                 to_status=Status.PENDING_HOD, action=Action.SUBMIT,
                 permission=can_submit, apply=apply)


def withdraw_submission(approval, user):
    return _move(approval, user,
                 allowed_from=(Status.PENDING_HOD,),
                 to_status=Status.DRAFT, action=Action.WITHDRAW,
                 permission=can_submit)


def hod_approve(approval, user, comment=''):
    def apply(a, u, comment, now):
        a.hod_reviewed_by, a.hod_reviewed_at, a.hod_note = u, now, comment

    return _move(approval, user,
                 allowed_from=(Status.PENDING_HOD,),
                 to_status=Status.PENDING_HEAD, action=Action.HOD_APPROVE,
                 permission=can_hod_review, comment=comment, apply=apply)


def hod_reject(approval, user, reason):
    def apply(a, u, comment, now):
        a.hod_reviewed_by, a.hod_reviewed_at, a.hod_note = u, now, comment
        a.rejection_reason, a.rejected_at_stage = comment, 'HOD'

    return _move(approval, user,
                 allowed_from=(Status.PENDING_HOD,),
                 to_status=Status.REJECTED, action=Action.HOD_REJECT,
                 permission=can_hod_review, comment=reason,
                 require_comment=True, apply=apply)


def final_approve(approval, user, comment=''):
    def apply(a, u, comment, now):
        a.head_reviewed_by, a.head_reviewed_at, a.head_note = u, now, comment
        _set_publish_flag(a, True)

    return _move(approval, user,
                 allowed_from=(Status.PENDING_HEAD,),
                 to_status=Status.APPROVED, action=Action.HEAD_APPROVE,
                 permission=can_final_review, comment=comment, apply=apply)


def final_reject(approval, user, reason):
    def apply(a, u, comment, now):
        a.head_reviewed_by, a.head_reviewed_at, a.head_note = u, now, comment
        a.rejection_reason, a.rejected_at_stage = comment, 'HEAD'

    return _move(approval, user,
                 allowed_from=(Status.PENDING_HEAD,),
                 to_status=Status.REJECTED, action=Action.HEAD_REJECT,
                 permission=can_final_review, comment=reason,
                 require_comment=True, apply=apply)


def reopen_result(approval, user, reason):
    def apply(a, u, comment, now):
        a.rejection_reason, a.rejected_at_stage = '', ''
        _set_publish_flag(a, False)

    return _move(approval, user,
                 allowed_from=(Status.APPROVED,),
                 to_status=Status.DRAFT, action=Action.REOPEN,
                 permission=can_reopen_result, comment=reason,
                 require_comment=True, apply=apply)

# def is_locked(subject, academic_year, term):
#     """True when grades for this subject/year/term must not be changed."""
    return ResultApproval.objects.filter(
        subject=subject, academic_year=academic_year, term=term,
        status__in=LOCKED_STATUSES,
    ).exists()


def get_approval(subject, academic_year, term):
    """The approval record, or None if nothing has been submitted yet."""
    return ResultApproval.objects.filter(
        subject=subject, academic_year=academic_year, term=term
    ).first()






# ---------------------------------------------------------------------
# PRE-SUBMISSION CHECKS AND PAGE HELPERS
# ---------------------------------------------------------------------

def _names(students, limit=5):
    shown = [f"{s.first_name} {s.surname}" for s in students[:limit]]
    extra = len(students) - limit
    return ", ".join(shown) + (f" and {extra} more" if extra > 0 else "")


def get_submission_problems(subject, academic_year, term):
    """Returns a list of reasons the term cannot be submitted yet (empty = ready)."""
    students = list(Students.objects.filter(subject=subject, status='Active')
                    .order_by('surname', 'first_name'))
    if not students:
        return ["No active students are enrolled in this subject."]

    setup = SubjectTermSetup.objects.filter(
        subject=subject, academic_year=academic_year, term=term
    ).first()

    # Older results entered directly (no assessment setup)
    if setup is None:
        graded = set(Grade.objects.filter(
            subject=subject, academic_year=academic_year, term=term
        ).values_list('student_id', flat=True))
        if not graded:
            return ["No results have been entered for this term."]
        missing = [s for s in students if s.pk not in graded]
        if missing:
            return [f"{len(missing)} student(s) have no result: {_names(missing)}."]
        return []

    assessments = list(setup.assessments.all())
    problems = []
    if not any(a.category == 'CA' for a in assessments):
        problems.append("Add at least one Continuous Assessment (CA).")
    if not any(a.category == 'EXAM' for a in assessments):
        problems.append("Add at least one Exam paper.")
    if problems:
        return problems

    entered = set(
        AssessmentGrade.objects
        .filter(assessment__in=assessments)
        .filter(Q(raw_score__isnull=False) | Q(is_absent=True))
        .values_list('student_id', 'assessment_id')
    )
    missing = [s for s in students if any((s.pk, a.pk) not in entered for a in assessments)]
    if missing:
        problems.append(
            f"{len(missing)} student(s) still have missing marks "
            f"(enter a mark or tick absent): {_names(missing)}."
        )
    return problems


def recalculate_term_grades(subject, academic_year, term):
    """Refresh every student's final score from the raw marks before submitting."""
    from .utils import recalculate_student_subject_grade

    if not SubjectTermSetup.objects.filter(
            subject=subject, academic_year=academic_year, term=term).exists():
        return
    for student in Students.objects.filter(subject=subject, status='Active'):
        recalculate_student_subject_grade(student, subject, academic_year, term)


def approval_panel_context(user, subject, academic_year, term):
    """Everything the approval panel template needs."""
    approval = get_approval(subject, academic_year, term)
    status = approval.status if approval else Status.DRAFT
    submittable = status in (Status.DRAFT, Status.REJECTED)
    allowed = can_submit(user, subject)
    return {
        'approval': approval,
        'approval_status': status,
        'approval_label': approval.get_status_display() if approval else 'Draft',
        'submission_problems': (
            get_submission_problems(subject, academic_year, term) if submittable else []
        ),
        'can_submit_results': allowed and submittable,
        'can_withdraw_results': allowed and status == Status.PENDING_HOD,
        'is_locked': status in LOCKED_STATUSES,
    }



def approved_grades(queryset=None):
    """Only Grade rows whose subject + year + term has final approval."""
    if queryset is None:
        queryset = Grade.objects.all()
    approved = ResultApproval.objects.filter(
        subject=OuterRef('subject'),
        academic_year=OuterRef('academic_year'),
        term=OuterRef('term'),
        status=Status.APPROVED,
    )
    return queryset.filter(Exists(approved))






# ---------------------------------------------------------------------
# NOTIFICATIONS AND DASHBOARD COUNTS
# ---------------------------------------------------------------------

def _final_approvers():
    User = get_user_model()
    return list(
        User.objects.filter(is_active=True).filter(
            Q(is_headteacher=True) | Q(is_deputy=True)
            | Q(groups__name__in=['Headteacher', 'Deputy', 'Admin'])
        ).distinct()
    )


def _person(user):
    return (user.get_full_name() or user.get_username()) if user else 'Someone'


def _notify_transition(approval, action, actor, comment):
    """Tell the next person that something needs them. Never blocks the workflow."""
    try:
        with transaction.atomic():
            subject = approval.subject
            what = f"{subject} ({approval.academic_year}, Term {approval.term})"
            who = _person(actor)
            hod = subject.departments.head_of_department
            teachers = [approval.submitted_by, subject.teacher_subject]
            reason = f" Reason: {comment}" if comment else ''

            if action == Action.SUBMIT:
                recipients = [hod] if hod else _final_approvers()
                title = f"Results awaiting your review: {subject}"
                text = f"{who} submitted {what}. Open Results Review to approve or reject them."
            elif action == Action.WITHDRAW:
                recipients = [hod] if hod else _final_approvers()
                title = f"Submission withdrawn: {subject}"
                text = f"{who} withdrew {what}. There is nothing to review for now."
            elif action == Action.HOD_APPROVE:
                recipients = _final_approvers()
                title = f"Results awaiting final approval: {subject}"
                text = f"{who} (HOD) approved {what}. Open Final Approval to approve or reject them."
            elif action == Action.HOD_REJECT:
                recipients = teachers
                title = f"Results sent back by the HOD: {subject}"
                text = f"{who} rejected {what}.{reason} Fix the marks and submit again."
            elif action == Action.HEAD_APPROVE:
                recipients = teachers + [hod]
                title = f"Results approved: {subject}"
                text = f"{who} gave final approval to {what}. The results are now final."
            elif action == Action.HEAD_REJECT:
                recipients = teachers + [hod]
                title = f"Results sent back by the headteacher: {subject}"
                text = f"{who} rejected {what}.{reason} The teacher can fix the marks and submit again."
            elif action == Action.REOPEN:
                recipients = teachers + [hod]
                title = f"Results reopened: {subject}"
                text = f"{who} reopened {what} for corrections.{reason}"
            else:
                return

            seen, rows = set(), []
            for person in recipients:
                if person is None or person.pk == actor.pk or person.pk in seen:
                    continue
                seen.add(person.pk)
                rows.append(StaffNotification(recipient=person, title=title, message=text))
            StaffNotification.objects.bulk_create(rows)
    except Exception:
        logger.exception("Could not create approval notifications")


def pending_counts_for(user):
    """How many approval items need this user's attention (for the dashboard)."""
    counts = {'hod': 0, 'final': 0, 'rejected': 0}

    final = is_final_approver(user)
    if final or SubjectDepartment.objects.filter(head_of_department=user).exists():
        scope = Q(subject__departments__head_of_department=user)
        if final:
            scope |= Q(subject__departments__head_of_department__isnull=True)
        counts['hod'] = ResultApproval.objects.filter(scope, status=Status.PENDING_HOD).count()

    if final:
        counts['final'] = ResultApproval.objects.filter(status=Status.PENDING_HEAD).count()

    counts['rejected'] = ResultApproval.objects.filter(
        status=Status.REJECTED, subject__teacher_subject=user
    ).count()
    return counts



