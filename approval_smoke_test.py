from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from students_app.models import Subject, ResultApproval
from students_app.approvals import *

User = get_user_model()


def attempt(fn, *args):
    try:
        fn(*args)
        return 'ALLOWED'
    except PermissionDenied:
        return 'DENIED'
    except ApprovalError as e:
        return f'BLOCKED: {e}'


subject = Subject.objects.filter(
    departments__head_of_department__isnull=False,
    teacher_subject__isnull=False,
).first()
teacher = subject.teacher_subject
hod = subject.departments.head_of_department
head = User.objects.filter(is_superuser=True).first()
print('Subject:', subject, '| teacher:', teacher, '| hod:', hod, '| head:', head)

ap = get_or_create_approval(subject, '2099', '1')
print('1 start:', ap.status)

print('2 teacher approves as HOD (should be DENIED):', attempt(hod_approve, ap, teacher) if teacher != hod else 'skipped (teacher is the HOD)')
print('3 HOD approves while still draft (BLOCKED):', attempt(hod_approve, ap, hod))

submit_for_approval(ap, teacher);          ap.refresh_from_db(); print('4 submitted:', ap.status)
print('5 HOD rejects with no reason (BLOCKED):', attempt(hod_reject, ap, hod, ''))
hod_reject(ap, hod, 'Check the scores');   ap.refresh_from_db(); print('6 HOD rejected:', ap.status, '| stage:', ap.rejected_at_stage)

submit_for_approval(ap, teacher);          ap.refresh_from_db(); print('7 resubmitted:', ap.status)
hod_approve(ap, hod);                      ap.refresh_from_db(); print('8 HOD approved:', ap.status)
final_reject(ap, head, 'Please recheck');  ap.refresh_from_db(); print('9 head rejected:', ap.status, '| stage:', ap.rejected_at_stage)

submit_for_approval(ap, teacher); hod_approve(ap, hod); final_approve(ap, head)
ap.refresh_from_db();                      print('10 final approved:', ap.status, '| locked:', is_locked(subject, '2099', '1'))
print('11 teacher tries to reopen (DENIED):', attempt(reopen_result, ap, teacher, 'oops') if teacher != head else 'skipped')
reopen_result(ap, head, 'Correction needed'); ap.refresh_from_db(); print('12 reopened:', ap.status, '| locked:', is_locked(subject, '2099', '1'))


print('Log entries:', ap.logs.count())
ap.delete()
print('Cleaned up test record.')