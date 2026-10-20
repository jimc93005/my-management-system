"""
Review pages for the approval workflow.
HOD page now; the headteacher page reuses build_subject_review in the next step.
"""
from collections import Counter, OrderedDict, defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import urlencode
from django.views.decorators.http import require_POST



from .approvals import (
    ApprovalError, Status, can_hod_review, hod_approve, hod_reject, is_final_approver,
)
from .views import TERM_CHOICES, current_academic_year, get_period
from .models import (
    AssessmentGrade, Grade, ResultApproval, Subject, SubjectDepartment, SubjectTermSetup,
)


from .approvals import (
    ApprovalError, Status, can_hod_review, can_reopen, final_approve, final_reject,
    hod_approve, hod_reject, is_final_approver, reopen_result,
)
PASS_MARK = 50


# ---------------------------------------------------------------------
# DATA: one subject's results, built from Grade rows (not current enrolment)
# ---------------------------------------------------------------------

def build_subject_review(approval):
    subject = approval.subject
    year, term = approval.academic_year, approval.term

    grades = list(
        Grade.objects.filter(subject=subject, academic_year=year, term=term)
        .select_related('student')
        .order_by('-score', 'student__surname', 'student__first_name')
    )

    setup = SubjectTermSetup.objects.filter(
        subject=subject, academic_year=year, term=term
    ).first()

    ca_max = exam_max = 0.0
    earned = defaultdict(lambda: {'CA': 0.0, 'EXAM': 0.0})
    absent = Counter()

    if setup:
        assessments = list(setup.assessments.all())
        category = {a.pk: a.category for a in assessments}
        ca_max = sum(a.max_raw_score for a in assessments if a.category == 'CA')
        exam_max = sum(a.max_raw_score for a in assessments if a.category == 'EXAM')
        marks = AssessmentGrade.objects.filter(assessment__in=assessments).values(
            'student_id', 'assessment_id', 'raw_score', 'is_absent'
        )
        for row in marks:
            if row['is_absent']:
                absent[row['student_id']] += 1
            elif row['raw_score'] is not None:
                earned[row['student_id']][category[row['assessment_id']]] += row['raw_score']

    has_breakdown = bool(setup and (ca_max or exam_max))

    rows, last_score, position = [], None, 0
    for index, g in enumerate(grades):
        if g.score != last_score:
            position = index + 1
        last_score = g.score

        row = {
            'rank': position,
            'student': g.student,
            'score': g.score,
            'letter': g.grade_letter_snapshot or '',
            'remark': g.remark_snapshot or '',
            'absent': absent[g.student_id],
        }
        if has_breakdown:
            e = earned[g.student_id]
            row['ca_points'] = round(e['CA'] / ca_max * setup.ca_weight_percentage, 1) if ca_max else None
            row['exam_points'] = round(e['EXAM'] / exam_max * setup.exam_weight_percentage, 1) if exam_max else None
        rows.append(row)

    scores = [g.score for g in grades]
    stats = {
        'count': len(scores),
        'average': round(sum(scores) / len(scores), 1) if scores else 0,
        'highest': max(scores) if scores else 0,
        'lowest': min(scores) if scores else 0,
        'pass_rate': round(sum(1 for s in scores if s >= PASS_MARK) / len(scores) * 100) if scores else 0,
    }

    return {
        'rows': rows,
        'stats': stats,
        'has_breakdown': has_breakdown,
        'ca_weight': setup.ca_weight_percentage if setup else None,
        'exam_weight': setup.exam_weight_percentage if setup else None,
    }


# ---------------------------------------------------------------------
# WHO SEES WHAT
# ---------------------------------------------------------------------

def user_can_review_as_hod(user):
    return SubjectDepartment.objects.filter(head_of_department=user).exists() or is_final_approver(user)


def hod_scope_subjects(user):
    """Subjects in departments the user heads (plus departments with no HOD, for headteacher level)."""
    scope = Q(departments__head_of_department=user)
    if is_final_approver(user):
        scope |= Q(departments__head_of_department__isnull=True)
    return Subject.objects.filter(scope)


def _bucket(status):
    if status == Status.PENDING_HOD:
        return 'awaiting'
    if status == Status.REJECTED:
        return 'rejected'
    return 'forwarded'


# ---------------------------------------------------------------------
# HOD REVIEW PAGE
# ---------------------------------------------------------------------

@login_required(login_url='users:login')
def hod_review_home(request):
    user = request.user
    if not user_can_review_as_hod(user):
        messages.warning(request, "🔒 Only Heads of Department can review subject results.")
        return redirect('students_app:dashboard')

    year, term = get_period(request)

    approvals = (
        ResultApproval.objects
        .filter(subject__in=hod_scope_subjects(user), academic_year=year, term=term)
        .exclude(status=Status.DRAFT)
        .select_related(
            'subject__name', 'subject__target_class', 'subject__teacher_subject',
            'subject__departments', 'submitted_by', 'hod_reviewed_by', 'head_reviewed_by',
        )
        .order_by('subject__target_class__level_order', 'subject__name__name')
    )

    groups = OrderedDict()
    summary = {'awaiting': 0, 'forwarded': 0, 'rejected': 0}

    for approval in approvals:
        bucket = _bucket(approval.status)
        summary[bucket] += 1

        group = groups.setdefault(approval.subject.target_class_id, {
            'class_level': approval.subject.target_class,
            'cards': [],
            'awaiting': 0,
        })
        if bucket == 'awaiting':
            group['awaiting'] += 1

        group['cards'].append({
            'approval': approval,
            'review': build_subject_review(approval),
            'bucket': bucket,
            'can_act': approval.status == Status.PENDING_HOD and can_hod_review(user, approval.subject),
        })

    years = set(ResultApproval.objects.values_list('academic_year', flat=True).distinct())
    years.update({current_academic_year(), year})

    context = {
        'groups': list(groups.values()),
        'summary': summary,
        'year': year,
        'term': term,
        'term_label': dict(TERM_CHOICES).get(term, f'Term {term}'),
        'term_choices': TERM_CHOICES,
        'year_options': sorted(years, reverse=True),
    }
    return render(request, 'students_app/hod_review.html', context)


@require_POST
@login_required(login_url='users:login')
def hod_decide(request, approval_id):
    approval = get_object_or_404(
        ResultApproval.objects.select_related('subject__departments'), pk=approval_id
    )
    decision = request.POST.get('decision')
    note = request.POST.get('note', '')

    try:
        if decision == 'approve':
            hod_approve(approval, request.user, note)
            messages.success(request, f"{approval.subject} approved and sent to the headteacher.")
        elif decision == 'reject':
            hod_reject(approval, request.user, note)
            messages.success(request, f"{approval.subject} rejected and returned to the teacher.")
        else:
            messages.error(request, "Unknown action.")
    except PermissionDenied:
        messages.error(request, "You are not allowed to review this subject.")
    except ApprovalError as exc:
        messages.error(request, str(exc))

    query = urlencode({'year': approval.academic_year, 'term': approval.term})
    return redirect(f"{reverse('students_app:hod_review')}?{query}")





# ---------------------------------------------------------------------
# FINAL APPROVAL PAGE (headteacher, deputy, admin)
# ---------------------------------------------------------------------

_FINAL_BUCKETS = {
    'PENDING_HEAD': 'awaiting',
    'PENDING_HOD': 'with_hod',
    'APPROVED': 'approved',
    'REJECTED': 'rejected',
}


@login_required(login_url='users:login')
def final_review_home(request):
    user = request.user
    if not is_final_approver(user):
        messages.warning(request, "🔒 Only the headteacher, deputy or admin can give final approval.")
        return redirect('students_app:dashboard')

    year, term = get_period(request)
    may_reopen = can_reopen(user)

    approvals = (
        ResultApproval.objects
        .filter(academic_year=year, term=term)
        .exclude(status=Status.DRAFT)
        .select_related(
            'subject__name', 'subject__target_class', 'subject__teacher_subject',
            'subject__departments', 'submitted_by', 'hod_reviewed_by', 'head_reviewed_by',
        )
        .order_by('subject__target_class__level_order', 'subject__name__name')
    )

    groups = OrderedDict()
    summary = {'awaiting': 0, 'with_hod': 0, 'approved': 0, 'rejected': 0}

    for approval in approvals:
        bucket = _FINAL_BUCKETS.get(approval.status, 'approved')
        summary[bucket] += 1

        group = groups.setdefault(approval.subject.target_class_id, {
            'class_level': approval.subject.target_class,
            'cards': [],
            'awaiting': 0,
        })
        if bucket == 'awaiting':
            group['awaiting'] += 1

        group['cards'].append({
            'approval': approval,
            'review': build_subject_review(approval),
            'bucket': bucket,
            'can_act': approval.status == Status.PENDING_HEAD,
            'can_reopen': may_reopen and approval.status == Status.APPROVED,
        })

    years = set(ResultApproval.objects.values_list('academic_year', flat=True).distinct())
    years.update({current_academic_year(), year})

    context = {
        'groups': list(groups.values()),
        'summary': summary,
        'year': year,
        'term': term,
        'term_label': dict(TERM_CHOICES).get(term, f'Term {term}'),
        'term_choices': TERM_CHOICES,
        'year_options': sorted(years, reverse=True),
    }
    return render(request, 'students_app/final_review.html', context)


@require_POST
@login_required(login_url='users:login')
def final_decide(request, approval_id):
    approval = get_object_or_404(
        ResultApproval.objects.select_related('subject__departments'), pk=approval_id
    )
    decision = request.POST.get('decision')
    note = request.POST.get('note', '')

    try:
        if decision == 'approve':
            final_approve(approval, request.user, note)
            messages.success(request, f"{approval.subject} approved. The results are now final.")
        elif decision == 'reject':
            final_reject(approval, request.user, note)
            messages.success(request, f"{approval.subject} rejected and returned to the teacher.")
        elif decision == 'reopen':
            reopen_result(approval, request.user, note)
            messages.success(request, f"{approval.subject} reopened. The teacher can edit the marks again.")
        else:
            messages.error(request, "Unknown action.")
    except PermissionDenied:
        messages.error(request, "You are not allowed to do that.")
    except ApprovalError as exc:
        messages.error(request, str(exc))

    query = urlencode({'year': approval.academic_year, 'term': approval.term})
    return redirect(f"{reverse('students_app:final_review')}?{query}")