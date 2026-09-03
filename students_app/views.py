
import json


from django.views.decorators.http import require_POST
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Sum, Avg
from django.contrib import messages
from django.utils.timezone import now
from weasyprint import HTML
from pathlib import Path
from django.conf import settings

from django.http import HttpResponse, Http404
from django.template.loader import render_to_string
from .forms import TeacherRegistrationForm
from django.utils.dateparse import parse_date
from datetime import date
from .models import Attendance
from .models import StaffNotification
from django.contrib.auth import get_user_model
from .models import GradingSystem, GradeBoundary, ClassLevel
from .forms import GradingSystemForm, GradeBoundaryForm, ClassLevelForm
from .models import SubjectDepartment
from .models import CalendarEvent
from .forms import SubjectDepartmentForm






from .utils import build_term_reports

from .models import Students
from .models import Subject
from .models import Grade
from .models import SchoolProfile
from .models import Teacher

from .forms import SchoolProfileForm
from .forms import StudentForm
from .forms import SubjectForm

from .models import Department
from .forms import DepartmentForm
from .forms import SubDepartmentForm
from .models import SubDepartment
from .models import ClassLevel
from .models import TeachingAssignment
from .models import SubDepartmentRole
from .forms import SubDepartmentRoleForm
from .forms import TeacherForm
from .forms import ClassLevelForm
from .models import ClassLevel
from .forms import MasterSubjectForm
from .models import MasterSubject

from django.contrib.auth.decorators import login_required
from .models import SubDepartment, DepartmentEvent
from .forms import DepartmentEventForm

# Make sure these are imported at the top of your views.py!
from .models import SchoolCoverPhoto, CarouselEvent

from django.shortcuts import render
# Make sure to import the new models alongside your existing ones!
from .models import SchoolCoverPhoto, CarouselEvent, Announcement, NewsArticle, LeadershipProfile


def index(request):
    # 1. Grab the school's profile (for the cover photo)
    school_profile = SchoolCoverPhoto.objects.filter(pk=1).first()

    # 2. Grab all the sliding event photos
    carousel_events = CarouselEvent.objects.all()

    # --- NEW CMS DATA ---
    # 3. Fetch the 5 most recent active announcements
    announcements = Announcement.objects.filter(is_active=True).order_by('-date_posted')[:5]

    # 4. Fetch the 4 most recent news articles (fits perfectly in your 4-column grid)
    news_articles = NewsArticle.objects.filter(is_active=True).order_by('-publish_date')[:4]

    # 5. Fetch leadership ordered by their assigned display order
    leaders = LeadershipProfile.objects.filter(is_active=True).order_by('display_order')

    # 6. Pack them into the context dictionary
    context = {
        'school_profile': school_profile,
        'carousel_events': carousel_events,
        'announcements': announcements,
        'news_articles': news_articles,
        'leaders': leaders,
    }

    return render(request, 'students_app/index.html', context)

    return render(request, 'students_app/index.html', context)

# VIEWS FOR STUDENTS FUNCTIONS

@login_required()
def student_list(request):
    if not request.user.has_perm('students_app.view_students'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " access the students list. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    query = request.GET.get('q', '')

    # 1. CRITICAL UPDATE: Only fetch 'Active' students
    # 2. ADDED order_by: Paginator requires ordered lists to prevent duplicates
    students = Students.objects.filter(status='Active').order_by('class_level', 'surname')

    if query:
        students = students.filter(
            Q(first_name__icontains=query) |
            Q(surname__icontains=query) |
            Q(student_id__icontains=query) |
            Q(created_at__icontains=query)
        )

    # Keep your excellent pagination logic
    paginator = Paginator(students, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'students': page_obj,
        'query': query,
        'page_obj': page_obj,
    }

    return render(request, 'students_app/students_list.html', context)

# MODIFYING STUDENTS DATA


# Make sure Subject is imported at the top!
@login_required(login_url='login')
def add_student(request):
    if not request.user.has_perm('students_app.add_students'):
        messages.warning(request, "🔒 Oops! You don't have permission to add students."
                                  " Please contact the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
        # Bounce them back to the safe dashboard (change this URL if your dashboard has a different name)
        return redirect('students_app:dashboard')
    if request.method == 'POST':
        form = StudentForm(request.POST)

        if form.is_valid():
            student = form.save(commit=False)
            student.save()
            form.save_m2m()  # Saves the many-to-many subjects

            messages.success(request, f"Student {student.first_name} successfully registered!")
            return redirect('students_app:students_list')
    else:
        form = StudentForm()

    # --- DYNAMIC DROPDOWN LOGIC ---
    # Create a dictionary mapping Class Level IDs to lists of Subject IDs
    # Example format: {"1": ["3", "5"], "2": ["4", "6"]}
    subject_map = {}

    # Get all subjects that have a class assigned
    subjects = Subject.objects.exclude(target_class__isnull=True)

    for sub in subjects:
        class_id = str(sub.target_class_id)
        if class_id not in subject_map:
            subject_map[class_id] = []
        # Save subject ID as a string to match the HTML form values
        subject_map[class_id].append(str(sub.id))

    # Convert the python dictionary to a JSON string
    subject_map_json = json.dumps(subject_map)

    context = {
        'form': form,
        'subject_map_json': subject_map_json
    }

    return render(request, 'students_app/add_student.html', context)

# deleting student from the list of students

@login_required(login_url='login')
def delete_student(request, student_id):
    if not request.user.has_perm('students_app.change_students'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " access deletion of students. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    student = get_object_or_404(Students, pk=student_id)
    if request.method == 'POST':
        student.delete()
        return redirect('students_app:students_list')
    context = {'student':student}

    return render(request, 'students_app/delete_student.html', context)



def edit_student(request, student_id):
    if not request.user.has_perm('students_app.change_students'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " access the edit of students. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    student = get_object_or_404(Students, pk=student_id)

    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)

        if form.is_valid():
            student_instance = form.save(commit=False)
            student_instance.save()
            form.save_m2m()  # ✅ THIS IS THE KEY LINE

            messages.success(request, f"Student {student.first_name}'s details updated successfully.")
            return redirect('students_app:students_list')

    else:
        form = StudentForm(instance=student)

    # --- DYNAMIC DROPDOWN LOGIC (Same as add_student) ---
    subject_map = {}
    subjects = Subject.objects.exclude(target_class__isnull=True)

    for sub in subjects:
        class_id = str(sub.target_class_id)
        if class_id not in subject_map:
            subject_map[class_id] = []
        subject_map[class_id].append(str(sub.id))

    subject_map_json = json.dumps(subject_map)

    context = {
        'form': form,
        'student': student,
        'subject_map_json': subject_map_json
    }
    return render(request, 'students_app/edit_student.html', context)

# VIEWS FOR SUBJECT FUNCTIONS
@login_required()
def subjects_list(request):
    if not request.user.has_perm('students_app.view_students'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " access the subject list. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    query = request.GET.get('q', '')

    # Use select_related to fetch the ForeignKey data efficiently in one query!
    subjects = Subject.objects.select_related(
        'teacher_subject', 'departments', 'target_class'
    ).order_by('target_class', 'name')

    if query:
        subjects = subjects.filter(
            Q(name__icontains=query) |
            Q(code__icontains=query) |
            Q(subject_teacher__icontains=query) |  # Your legacy field
            Q(teacher_subject__first_name__icontains=query) |  # The new User relation
            Q(teacher_subject__last_name__icontains=query) |
            Q(teacher_subject__username__icontains=query)
        ).distinct()

    paginator = Paginator(subjects, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        # We pass page_obj as 'subjects' so the template can loop through it easily
        'subjects': page_obj,
        'page_obj': page_obj,
        'query': query,
    }
    return render(request, 'students_app/subjects_list.html', context)

# adding_subjects
@login_required(login_url='login')
def add_subject(request):
    if not request.user.has_perm('students_app.add_subject'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " access the adding of subjects . Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    if request.method == 'POST':
        form = SubjectForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('students_app:subjects_list')
    else:
        form = SubjectForm()

    context = {'form': form}
    return render(request, 'students_app/add_subject.html', context)

# editing subjects

@login_required(login_url='login')
def edit_subject(request, subject_id):
    if not request.user.has_perm('students_app.change_subject'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " access the edit of subjects. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    subject = get_object_or_404(Subject, pk=subject_id)

    if request.method != 'POST':
        form = SubjectForm(instance=subject)

    else:
        form = SubjectForm(instance=subject, data=request.POST)
        if form.is_valid():
            student_instance = form.save(commit=False)
            student_instance.save()

            return redirect('students_app:students_list')

    context = {'form': form, 'subject': subject}
    messages.success(request, "Student details updated successfully.")
    return render(request, 'students_app/edit_subjects.html', context)

@login_required(login_url='login')
def delete_subject(request, subject_id):
    if not request.user.has_perm('students_app.change_students'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " delete subject. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    subject = get_object_or_404(Subject, pk=subject_id)
    if request.method == 'POST':
        subject.delete()
        return redirect('students_app:subjects_list')

    context = {'subject': subject}

    return render(request, 'students_app/delete_subject.html', context)


# GROUPING STUDENTS BY CLASS
@login_required()
def class_list(request):
    if not request.user.has_perm('students_app.view_classlevel'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " access this operation. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')

    # Grab the classes dynamically from the database
    class_objects = ClassLevel.objects.all().order_by('level_order')

    # Package them as (value, label) pairs to keep the HTML template's loop happy!
    classes = [(c.class_level, c.class_level) for c in class_objects]

    return render(request, 'students_app/class_list.html', {'classes': classes})


# PLACING THE STUDENTS IN THEIR RESPECTIVE CLASSES

import datetime
from django.db.models import Q, Count  # <-- Ensure Count is imported!
from django.core.paginator import Paginator

from .models import Students, ClassLevel, Grade


def students_by_class(request, class_level):
    if not request.user.has_perm('students_app.view_classlevel'):
        messages.warning(request,
                         "🔒 Oops! You don't have permission to access this operation. Please contact the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')

    query = request.GET.get('q', '')

    # 1. Base Query
    student_list = Students.objects.filter(class_level__class_level=class_level, status='Active')

    # 2. Grab the actual class object
    try:
        class_obj = ClassLevel.objects.get(class_level=class_level)
    except ClassLevel.DoesNotExist:
        messages.error(request, "Class not found.")
        return redirect('students_app:class_list')

    # Ensure we have the exact string used in the snapshot (e.g., "Form 1")
    class_name_str = str(class_obj.class_level)

    # 3. Auto-Detect Current Year and Term (NOW FILTERED BY SNAPSHOT)
    latest_grade = Grade.objects.filter(
        student__class_level=class_obj,
        class_level_snapshot=class_name_str  # <--- THE FIX: Must belong to this class!
    ).order_by('-academic_year', '-term').first()

    if latest_grade:
        current_year = latest_grade.academic_year
        current_term = latest_grade.term
    else:
        current_year = str(datetime.date.today().year)
        current_term = '1'

    # 4. Search Filter
    if query:
        student_list = student_list.filter(
            Q(first_name__icontains=query) |
            Q(surname__icontains=query) |
            Q(student_id__icontains=query)
        )

    # 5. THE MAGIC DATABASE SWEEP (NOW FILTERED BY SNAPSHOT)
    student_list = student_list.annotate(
        expected_grades=Count('subject', distinct=True),
        entered_grades=Count(
            'grades',
            filter=Q(
                grades__academic_year=current_year,
                grades__term=current_term,
                grades__class_level_snapshot=class_name_str  # <--- THE FIX
            ),
            distinct=True
        )
    ).order_by('surname')

    # 6. Pagination
    paginator = Paginator(student_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # 7. Safe Percentage Calculation
    for student in page_obj:
        if student.expected_grades > 0:
            student.grade_progress = int((student.entered_grades / student.expected_grades) * 100)
            student.is_completed = student.entered_grades >= student.expected_grades
        else:
            student.grade_progress = 0
            student.is_completed = False

    context = {
        'page_obj': page_obj,
        'class_level': class_level,
        'class_obj': class_obj,
        'count': student_list.count(),
        'query': query,
        'current_year': current_year,
        'current_term': current_term,
    }
    return render(request, 'students_app/students_by_class.html', context)

@login_required(login_url='login')
def add_grade(request, student_id):
    if not request.user.has_perm('students_app.add_grade'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " access this operation. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    student = get_object_or_404(Students, id=student_id)
    user = request.user

    # -------------------------------------------------------
    # 1. SECURITY FILTER: Only fetch subjects permitted for this user
    # -------------------------------------------------------
    # -------------------------------------------------------
    # 1. SECURITY FILTER: Only fetch subjects permitted for this user
    # -------------------------------------------------------
    if user.is_headteacher or user.is_deputy:
        # Admins can grade any subject the student is taking
        subjects = student.subject.all()
    else:
        # Start with empty lists
        hod_subjects = student.subject.none()
        teacher_subjects = student.subject.none()

        # Check HOD privileges
        if user.is_hod and hasattr(user, 'department') and user.department:
            hod_subjects = student.subject.filter(departments=user.department)

        # Check direct Teacher privileges
        if user.is_teacher:
            teacher_subjects = student.subject.filter(teacher_subject=user)

        # MERGE THEM! The '|' symbol safely combines both lists of subjects.
        subjects = hod_subjects | teacher_subjects

    # If the filter results in zero subjects, bounce them out!
    if not subjects.exists():
        messages.error(request, f"You do not teach any subjects to {student.first_name} for their current class level.")
        return redirect('students_app:dashboard')
    # -------------------------------------------------------
    # 2. Academic years for dropdown
    # -------------------------------------------------------
    import datetime
    current_year = datetime.datetime.now().year
    years = list(range(current_year - 2, current_year + 5))  # Dynamic year list

    # -------------------------------------------------------
    # 3. Handle form submission
    # -------------------------------------------------------
    if request.method == "POST":
        academic_year = request.POST.get('academic_year')
        term = request.POST.get('term')

        # Validation
        if not academic_year or not term:
            messages.error(request, "Please select an academic year and term.")
            return render(request, 'students_app/add_grade.html', {
                'student': student, 'subjects': subjects, 'years': years
            })

        # Loop through the SECURE list of subjects and save grades
        for subject in subjects:
            score = request.POST.get(f'score_{subject.id}')
            if score:
                Grade.objects.update_or_create(
                    student=student,
                    subject=subject,
                    academic_year=academic_year,
                    term=term,
                    defaults={
                        "score": score,
                        # Snapshot the class level string for historical records
                        "class_level_snapshot": str(student.class_level)
                    }
                )

        messages.success(request, f"Grades successfully saved for {student.first_name}!")
        return redirect('students_app:student_profile', student_id=student.id)

    # -------------------------------------------------------
    # 4. Show the form initially
    # -------------------------------------------------------
    context = {
        "student": student,
        "subjects": subjects,
        "years": years,
    }
    return render(request, "students_app/add_grade.html", context)
# STUDENT PROFILE

@login_required(login_url='login')
def student_profile(request, student_id):
    if not request.user.has_perm('students_app.change_students'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " access this operation. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    student = get_object_or_404(Students, id=student_id)
    level_filter = request.GET.get('level')

    term_reports, total_students = build_term_reports(student, level_filter)
    historical_levels = Grade.objects.filter(student=student) \
        .values_list('class_level_snapshot', flat=True) \
        .distinct()


    context = {
        'student': student,
        'term_reports': term_reports,
        'total_students': total_students,
        'historical_levels': historical_levels,  # Pass the levels to the template
        'current_filter': level_filter,  # Let the template know what is currently selected
    }

    return render(
        request,
        "students_app/student_profile.html",
        context
    )



# DELETE FUNTIONS IN THE STUDENT PROFILE AND EDITING FUNCTION




# EDITING GRADES

@login_required(login_url='login')
def edit_grade(request, grade_id):
    if not request.user.has_perm('students_app.change_students'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " access this operation. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    grade = get_object_or_404(Grade, id=grade_id)
    student = grade.student

    if request.method == "POST":
        score = request.POST.get("score")
        academic_year = request.POST.get("academic_year")
        term = request.POST.get("term")

        # Validate fields
        if not score or not academic_year or not term:
            messages.error(request, "All fields are required.")
            return redirect("students_app:edit_grade", grade_id=grade.id)

        grade.score = score
        grade.academic_year = academic_year
        grade.term = term
        grade.save()

        messages.success(request, "Grade updated successfully.")
        return redirect("students_app:student_profile", student_id=student.id)

    years = range(2020, 2050)
    terms = ["1", "2", "3"]

    context = {
        "grade": grade,
        "student": student,
        "years": years,
        "terms": terms,
    }

    return render(request, "students_app/edit_grade.html", context)



# DELETING GRADES FUNCTIONS

# -----------------------------
# Delete a single grade
# -----------------------------
@require_POST
@login_required(login_url='login')
def delete_grade(request, grade_id):
    if not request.user.has_perm('students_app.change_students'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " delete grade. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    grade = get_object_or_404(Grade, id=grade_id)

    grade.delete()   # permanent delete

    messages.success(request, "Grade permanently deleted.")
    return redirect("students_app:student_profile", student_id=grade.student.id)

# -----------------------------
# Delete all grades in a specific term
# -----------------------------
@require_POST
@login_required(login_url='login')
def delete_term_grades(request, student_id, year, term):
    if not request.user.has_perm('students_app.delete_grade'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " to delete term grades. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    student = get_object_or_404(Students, id=student_id)

    Grade.objects.filter(
        student=student,
        academic_year=year,
        term=term
    ).delete()   # permanent delete

    messages.success(request, f"All grades for Term {term}, {year} permanently deleted.")
    return redirect("students_app:student_profile", student_id=student.id)


# -----------------------------
# Delete all grades in a specific year
# -----------------------------
@require_POST
@login_required(login_url='login')
def delete_year_grades(request, student_id, year):
    if not request.user.has_perm('students_app.change_students'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " delete year grade. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    student = get_object_or_404(Students, id=student_id)

    Grade.objects.filter(
        student=student,
        academic_year=year
    ).delete()   # permanent delete

    messages.success(request, f"All grades for Year {year} permanently deleted.")
    return redirect("students_app:student_profile", student_id=student.id)


# SCHOOL REPORT FORMATION AND VIEWS
@login_required(login_url='login')
def edit_school_profile(request):
    if not request.user.has_perm('students_app.change_students'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " access this operation. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    # Get the existing profile, or None
    school_profile, created = SchoolProfile.objects.get_or_create(id=1)  # assuming single school

    if request.method == "POST":
        form = SchoolProfileForm(request.POST, request.FILES, instance=school_profile)
        if form.is_valid():
            form.save()
            return redirect('students_app:index')  # redirect to the report page
    else:
        form = SchoolProfileForm(instance=school_profile)

    context = {'form': form}
    return render(request, 'students_app/edit_school_profile.html', context)


# SCHOOL REPORT VIEW:
@login_required(login_url='login')
def school_report(request, student_id, academic_year, term):
    if not request.user.has_perm('students_app.change_students'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " access this operation. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    student = get_object_or_404(Students, id=student_id)

    term_reports, total_students = build_term_reports(student)
    school_profile = SchoolProfile.objects.first()

    # Extract ONE term only
    report_data = term_reports.get(academic_year, {}).get(term)

    if not report_data:
        raise Http404("Report not found")

    context = {
        'student': student,
        'academic_year': academic_year,
        'term': term,
        'grades': report_data['grades'],
        'average': report_data['average'],
        'position': report_data['position'],
        'promotion_status': report_data['promotion_status'],
        'head_remark': report_data['head_remark'],
        'total_students': total_students,
        'school_profile': school_profile,
    }

    return render(
        request,
        "students_app/school_report.html",
        context
    )

# PDF GENERATION VIEWSz


@login_required(login_url='users:login')
def school_report_pdf(request, student_id, academic_year, term):
    # 1. SECURITY CHECK
    if not request.user.has_perm('students_app.change_students'):
        messages.warning(request,
                         "🔒 Oops! You don't have permission to access this operation. Please contact the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')

    student = get_object_or_404(Students, id=student_id)
    school_profile = SchoolProfile.objects.first()

    # 2. FETCH REPORT DATA (Your existing logic)
    term_reports, total_students = build_term_reports(student)
    report_data = term_reports.get(academic_year, {}).get(term)

    if not report_data:
        raise Http404("Report not found")

    # 3. HELPER FUNCTION: Convert Database Images to Secure Local URIs for WeasyPrint
    def get_image_uri(image_field):
        if image_field and hasattr(image_field, 'path'):
            image_path = Path(image_field.path)
            if image_path.exists():
                return image_path.as_uri()
        return None

    # 4. GRAB THE IMAGES
    school_logo_uri = get_image_uri(school_profile.logo) if school_profile else None
    head_sig_uri = get_image_uri(school_profile.headteacher_signature) if school_profile else None

    # Safely navigate relationships to get the Form Teacher's signature
    teacher_sig_uri = None
    if getattr(student, 'class_level', None) and getattr(student.class_level, 'form_teacher', None):
        teacher_sig_uri = get_image_uri(student.class_level.form_teacher.signature)

    # 5. BUILD CONTEXT
    context = {
        'student': student,
        'academic_year': academic_year,
        'term': term,
        'grades': report_data['grades'],
        'average': report_data['average'],
        'position': report_data['position'],
        'promotion_status': report_data['promotion_status'],
        'head_remark': report_data['head_remark'],
        'class_comment': report_data['class_comment'],
        'total_students': total_students,
        'school_profile': school_profile,

        # Pass the formatted URIs to the template
        'school_logo_uri': school_logo_uri,
        'head_sig_uri': head_sig_uri,
        'teacher_sig_uri': teacher_sig_uri,

        'static_root': settings.STATIC_ROOT,
    }

    # 6. GENERATE PDF
    html_string = render_to_string('students_app/school_report_pdf.html', context)

    # Enable presentational_hints to support HTML attributes like width/height
    pdf = HTML(
        string=html_string,
        base_url=request.build_absolute_uri()
    ).write_pdf(presentational_hints=True)

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'filename="school_report_{student.id}_{academic_year}_term_{term}.pdf"'

    return response

# DEPARTMENTS VIEWS
@login_required()
def department_list(request):
    if not request.user.has_perm('students_app.view_department'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " access this operation. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')

    departments = Department.objects.all().order_by('name')
    context = {'departments': departments}

    return render(request, 'students_app/department_list.html', context)

@login_required(login_url='login')
def add_department(request):
    departments = Department.objects.all().order_by('name')
    if request.method == 'POST':
        form = DepartmentForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('students_app:department_list')
    else:
        form = DepartmentForm()

    context = {
        'departments': departments,
        'form': form,
    }

    return render(request, 'students_app/add_department.html', context)
@login_required(login_url='login')
def edit_department(request, department_id):
    if not request.user.has_perm('students_app.change_students'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " access this operation. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    departments = get_object_or_404(Department, id=department_id)

    if request.method != 'POST':
        form = DepartmentForm(instance=departments)

    else:
        form = DepartmentForm(instance=departments, data=request.POST)
        if form.is_valid():
            student_instance = form.save(commit=False)
            student_instance.save()
            messages.success(request, "Department details updated successfully.")

            return redirect('students_app:department_list')

    context = {'form': form, 'departments': departments}

    return render(request, 'students_app/edit_department.html', context)


@login_required(login_url='login')
def department_delete(request, department_id):
    if not request.user.has_perm('students_app.change_students'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " access this operation. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    department = get_object_or_404(Department, id=department_id)

    if request.method == 'POST':
        department.delete()

    return redirect('students_app:department_list')

@login_required(login_url='login')
def subdepartment_list(request, department_id):
    if not request.user.has_perm('students_app.view_department'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " access this operation. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    department = get_object_or_404(Department, id=department_id)
    sub_departments = department.sub_departments.all()
    context = {'department': department, 'sub_departments': sub_departments}

    return render(request, 'students_app/subdepartment_list.html', context)

@login_required(login_url='login')
def subdepartment_create(request, department_id):
    if not request.user.has_perm('students_app.change_students'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " access this operation. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    department = get_object_or_404(Department, id=department_id)

    if request.method == 'POST':
        form = SubDepartmentForm(request.POST)
        if form.is_valid():
            sub = form.save(commit=False)
            sub.department = department
            sub.save()
            return redirect('students_app:subdepartment_list',department_id=department.id)
    else:
        form = SubDepartmentForm()

    context = {'department': department, 'form': form}
    return render(request,'students_app/subdepartment_create.html', context)

@login_required(login_url='login')
def subdepartment_roles(request, subdepartment_id):
    if not request.user.has_perm('students_app.view_department'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " access this operation. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    sub_department = get_object_or_404(SubDepartment, id=subdepartment_id)

    roles = SubDepartmentRole.objects.filter(
        sub_department=sub_department
    )

    return render(
        request,
        'students_app/subdepartment_roles.html',
        {
            'sub_department': sub_department,
            'roles': roles,
        }
    )

@login_required(login_url='login')
def subdepartment_role_create(request, subdepartment_id):
    if not request.user.has_perm('students_app.change_students'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " access this operation. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    sub_department = get_object_or_404(SubDepartment, id=subdepartment_id)

    if request.method == 'POST':
        form = SubDepartmentRoleForm(request.POST)

        if form.is_valid():
            role = form.cleaned_data['role']

            # STRICT RULE CHECK
            if role in ['HEAD', 'VICE']:
                exists = SubDepartmentRole.objects.filter(
                    sub_department=sub_department,
                    role=role
                ).exists()

                if exists:
                    messages.error(
                        request,
                        f"This sub-department already has a {role.lower()}."
                    )
                else:
                    assignment = form.save(commit=False)
                    assignment.sub_department = sub_department
                    assignment.save()
                    return redirect(
                        'students_app:subdepartment_roles',
                        subdepartment_id=sub_department.id
                    )
            else:
                assignment = form.save(commit=False)
                assignment.sub_department = sub_department
                assignment.save()
                return redirect(
                    'students_app:subdepartment_roles',
                    subdepartment_id=sub_department.id
                )
    else:
        form = SubDepartmentRoleForm()

    return render(
        request,
        'students_app/subdepartment_role_create.html',
        {
            'sub_department': sub_department,
            'form': form
        }
    )


# TEACHERS VIEWES



# Fetch your CustomUser model
User = get_user_model()


# Ensure we are using your unified CustomUser model
User = get_user_model()


@login_required(login_url='users:login')
def teachers_list(request):
    user = request.user

    # 1. SECURITY CHECK
    # Simplified using your unified CustomUser boolean fields
    is_admin = user.is_headteacher or user.is_superuser or user.groups.filter(
        name__in=['Headteacher', 'Admin']).exists()

    if not is_admin:
        messages.warning(request,
                         "🔒 Oops! You don't have permission to access the staff directory. Please contact the Headteacher.")
        return redirect('students_app:dashboard')

    # 2. CAPTURE SEARCH QUERY (.strip() removes accidental spaces)
    query = request.GET.get('q', '').strip()

    # 3. BASE QUERY
    # We pull anyone who is a teacher.
    # Added 'last_name' to order_by to properly sort people with the same first name!
    teachers_queryset = User.objects.filter(
        Q(is_teacher=True) | Q(groups__name__iexact='teachers')
    ).distinct().order_by('first_name', 'last_name')

    # 4. APPLY SEARCH FILTER
    if query:
        teachers_queryset = teachers_queryset.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(employment_number__icontains=query) |
            Q(username__icontains=query) |
            Q(email__icontains=query)  # Added email search capability!
        ).distinct()

    # 5. PAGINATION
    paginator = Paginator(teachers_queryset, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # 6. CONTEXT & RENDER
    context = {
        'teachers': page_obj,
        'page_obj': page_obj,
        'query': query,
        'total_teachers': teachers_queryset.count(),  # Added this so you can display the total count in HTML
    }

    return render(request, 'students_app/teachers_list.html', context)


User = get_user_model()
@login_required(login_url='login')
def edit_teachers(request, teachers_id):
    if not request.user.has_perm('students_app.change_students'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " access this operation. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')

    # --- THE FIX: We now look for the ID inside the User table! ---
    teachers = get_object_or_404(User, id=teachers_id)

    if request.method != 'POST':
        form = TeacherForm(instance=teachers)

    else:
        form = TeacherForm(instance=teachers, data=request.POST)
        if form.is_valid():
            teachers_instance = form.save(commit=False)
            teachers_instance.save()
            messages.success(request, f"{teachers.first_name}'s details updated successfully.")

            return redirect('students_app:teachers_list')

    context = {'form': form, 'teachers': teachers}

    return render(request, 'students_app/edit_teachers.html', context)


@login_required(login_url='login')
def delete_teachers(request, teachers_id):
    if not request.user.has_perm('students_app.change_students'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " access this operation. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')

    # --- THE FIX: We now look for the ID inside the User table! ---
    teachers = get_object_or_404(User, id=teachers_id)

    if request.method == "POST":
        teacher_name = f"{teachers.first_name} {teachers.last_name}"
        teachers.delete()
        messages.success(request, f"Teacher {teacher_name} has been successfully deleted.")
        return redirect('students_app:teachers_list')

    # Fallback just in case someone tries to load the delete URL directly
    return redirect('students_app:teachers_list')

@login_required(login_url='login')
def add_teachers(request):
    if not request.user.has_perm('students_app.change_students'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " access this operation. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    teachers = Teacher.objects.all().order_by('first_name')
    if request.method == 'POST':
        form = TeacherForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('students_app:teachers_list')
    else:
        form = TeacherForm()

    context = {
        'teachers': teachers,
        'form': form,
    }

    return render(request, 'students_app/add_teachers.html', context)


from django.contrib.auth import get_user_model

User = get_user_model()


@login_required(login_url='login')
def teacher_subject_list(request, teachers_id):
    # 1. STRICT SECURITY: Only Headteachers/Admins should manage staff profiles!
    is_admin = getattr(request.user, 'is_headteacher', False) or request.user.groups.filter(
        name__in=['Headteacher', 'Admin']).exists()
    if not is_admin:
        messages.warning(request, "🔒 Access Denied: Only Administrators can view and manage staff profiles.")
        return redirect('students_app:dashboard')

    # 2. Fetch the Staff Member from the USER model (where roles live!)
    # Note: If your URLs pass the old 'Teacher' model ID, you might need to fetch the User linked to that Teacher.
    teacher = get_object_or_404(User, id=teachers_id)

    # 3. Fetch their curriculum
    # (Adjust 'teacher_subject' to match whatever ForeignKey links Subject to User)
    teachers_assignments = Subject.objects.filter(teacher_subject=teacher).select_related('target_class')

    # 4. Figure out what roles this teacher currently holds for the UI Badges
    is_hod = getattr(teacher, 'is_hod', False) or teacher.groups.filter(name__iexact='HOD').exists()
    is_form_teacher = hasattr(teacher, 'my_form_class') and teacher.my_form_class is not None

    context = {
        'teacher': teacher,
        'teachers_assignments': teachers_assignments,
        'is_hod': is_hod,
        'is_form_teacher': is_form_teacher,
        'my_dept': getattr(teacher, 'department', None) if is_hod else None,
        'my_class': teacher.my_form_class if is_form_teacher else None,
    }

    return render(request, 'students_app/teacher_subject_list.html', context)

# VIEWS FOR PROMOTING STUDENTS FROM ONE CLASS TO ANOTHER
@login_required(login_url='login')
def change_class_level(request, student_id):
    if not request.user.has_perm('students_app.change_students'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " access this operation. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    # Fetch the specific student using the URL ID
    student = get_object_or_404(Students, id=student_id)

    if request.method == "POST":
        # Check which button was pressed in the HTML form (promote or graduate)
        action_type = request.POST.get('action_type')

        if action_type == 'graduate':
            # Soft-delete: Move them to the Alumni Archive
            student.status = 'Graduated'
            student.save()
            messages.success(request, f"🎓 {student.first_name} {student.surname} has been moved to the Alumni Archive.")
            return redirect('students_app:alumni_list')

        elif action_type == 'promote':
            # Standard promotion: Move to a new class
            new_class_id = request.POST.get('new_class')
            if new_class_id:
                student.class_level_id = new_class_id
                student.save()
                messages.success(request, f"✅ {student.first_name} was successfully moved to their new class.")
                return redirect('students_app:student_profile', student_id=student.id)
            else:
                messages.error(request, "⚠️ Please select a valid target class from the dropdown.")
                return redirect('students_app:change_class_level', student_id=student.id)

    # --- GET REQUEST: Load the Page ---
    # Fetch all classes to populate the dropdown menu
    all_classes = ClassLevel.objects.all().order_by('class_level')

    context = {
        'student': student,
        'all_classes': all_classes
    }
    return render(request, "students_app/change_class.html", context)
# LOG IN AND LOG OUR VIEWS AND AUTHENTICATION SYSTEMS
# Make sure to import your User model at the top if you haven't!
from django.contrib.auth import get_user_model

User = get_user_model()
from datetime import date


# Make sure Attendance and AttendanceWarning are imported at the top!
# from .models import Students, Subject, Grade, ClassLevel, StaffNotification, Attendance, AttendanceWarning

@login_required()
def dashboard(request):
    user = request.user

    # 👇 HANDLE RESOLVING RED FLAGS 👇
    if request.method == 'POST' and 'resolve_warning' in request.POST:
        warning_id = request.POST.get('warning_id')
        resolution_notes = request.POST.get('resolution_notes', '')

        warning = AttendanceWarning.objects.filter(id=warning_id).first()
        if warning:
            warning.is_resolved = True
            warning.resolved_by = user
            warning.resolution_notes = resolution_notes
            warning.save()
            messages.success(request, f"Warning for {warning.student.first_name} has been resolved and cleared.")
        return redirect('students_app:dashboard')
    # 👆 END NEW LOGIC 👆

    # --- Role Checks ---
    is_admin = getattr(user, 'is_headteacher', False) or getattr(user, 'is_deputy', False) or user.groups.filter(
        name__in=['Headteacher', 'Admin', 'Deputy']).exists()
    is_hod = getattr(user, 'is_hod', False) or user.groups.filter(name__iexact='HOD').exists()

    my_class = user.my_form_class.first()
    is_form_teacher = my_class is not None
    is_teacher = getattr(user, 'is_teacher', False) or user.groups.filter(name__iexact='teachers').exists()

    # --- Notifications ---
    unread_notifications = StaffNotification.objects.filter(recipient=user, is_read=False)

    # Base Context
    context = {
        'dashboard_title': "Staff Portal",
        'is_admin': is_admin,
        'is_hod': is_hod,
        'is_form_teacher': is_form_teacher,
        'is_teacher': is_teacher,
        'unread_notifications': unread_notifications,
        'unread_count': unread_notifications.count(),
    }

    # -----------------------------------------------------
    # 1. ADMIN DATA
    # -----------------------------------------------------
    if is_admin:
        context['total_students'] = Students.objects.filter(status='Active').count()

        User = get_user_model()
        context['total_teachers'] = User.objects.filter(
            Q(is_teacher=True) | Q(groups__name__iexact='teachers')
        ).distinct().count()

        context['total_subjects'] = Subject.objects.count()
        context['recent_students'] = Students.objects.order_by('-id')[:5]

    # -----------------------------------------------------
    # 2. HOD DATA
    # -----------------------------------------------------
    if is_hod:
        my_dept = getattr(user, 'my_headed_department', None)
        context['my_dept'] = my_dept

        context['total_dept_subjects'] = 0
        context['total_dept_teachers'] = 0
        context['overall_pass_rate'] = 0
        context['class_stats'] = []

        if my_dept:
            dept_subjects = Subject.objects.filter(departments=my_dept)
            dept_grades = Grade.objects.filter(subject__in=dept_subjects)
            total_grades = dept_grades.count()
            passed_grades = dept_grades.filter(score__gte=50).count()

            context['overall_pass_rate'] = round((passed_grades / total_grades * 100), 1) if total_grades > 0 else 0
            context['total_dept_subjects'] = dept_subjects.count()

            context['total_dept_teachers'] = dept_subjects.exclude(teacher_subject__isnull=True).values(
                'teacher_subject').distinct().count()

            class_stats = []
            classes_taught = ClassLevel.objects.filter(assigned_subjects__in=dept_subjects).distinct().order_by(
                'class_level')

            for cl in classes_taught:
                subjects_in_class = dept_subjects.filter(target_class=cl).select_related('teacher_subject')
                c_total = Grade.objects.filter(subject__in=subjects_in_class).count()
                c_pass = Grade.objects.filter(subject__in=subjects_in_class, score__gte=50).count()

                subj_details = []
                for sub in subjects_in_class:
                    s_total = Grade.objects.filter(subject=sub).count()
                    s_pass = Grade.objects.filter(subject=sub, score__gte=50).count()
                    subj_details.append({
                        'name': sub.name,
                        'teacher': sub.teacher_subject,
                        'pass_rate': round((s_pass / s_total * 100), 1) if s_total > 0 else 0
                    })

                class_stats.append({
                    'class_name': cl.class_level,
                    'pass_rate': round((c_pass / c_total * 100), 1) if c_total > 0 else 0,
                    'subjects': subj_details
                })
            context['class_stats'] = class_stats





    # -----------------------------------------------------
    # 3. FORM TEACHER DATA
    # -----------------------------------------------------
        # -----------------------------------------------------
        # 3. FORM TEACHER DATA
        # -----------------------------------------------------

    # -----------------------------------------------------
    # 4. REGULAR TEACHER DATA
    # -----------------------------------------------------

    if is_form_teacher:
        my_class = user.my_form_class.first()
        my_class_name_str = str(my_class.class_level)  # Get the exact string for snapshot matching

        class_students = Students.objects.filter(class_level=my_class, status='Active')

        # =========================================================
        # 1. AUTO-DETECT CURRENT YEAR & TERM FIRST
        # =========================================================
        latest_class_grade = Grade.objects.filter(
            student__in=class_students,
            class_level_snapshot=my_class_name_str
        ).order_by('-academic_year', '-term').first()

        if latest_class_grade:
            track_year = latest_class_grade.academic_year
            track_term = latest_class_grade.term
        else:
            track_year = str(date.today().year)
            track_term = '1'

        # =========================================================
        # 2. FILTER GRADES STRICTLY BY CURRENT CLASS & TERM
        # =========================================================
        class_grades = Grade.objects.filter(
            student__in=class_students,
            academic_year=track_year,
            term=track_term,
            class_level_snapshot=my_class_name_str
        )

        context['my_class'] = my_class
        context['class_students'] = class_students[:5]
        context['class_subjects'] = Subject.objects.filter(target_class=my_class).select_related('teacher_subject')

        t_grades = class_grades.count()
        p_grades = class_grades.filter(score__gte=50).count()

        # Gender pass rates
        b_grades = class_grades.filter(student__gender='Male')
        g_grades = class_grades.filter(student__gender='Female')

        context['stats'] = {
            'total': class_students.count(),
            'boys': class_students.filter(gender='Male').count(),
            'girls': class_students.filter(gender='Female').count(),
            'pass_rate': round((p_grades / t_grades * 100), 1) if t_grades > 0 else 0,
            'boys_pass': round((b_grades.filter(score__gte=50).count() / b_grades.count() * 100),
                               1) if b_grades.count() > 0 else 0,
            'girls_pass': round((g_grades.filter(score__gte=50).count() / g_grades.count() * 100),
                                1) if g_grades.count() > 0 else 0,
        }

        # --- SMART ATTENDANCE DASHBOARD LOGIC ---
        today = date.today()

        # If students were promoted today, their morning attendance from the old class will carry over
        # unless filtered. If your Attendance model has a 'term' or 'class_level' field, add it here.
        todays_attendance = Attendance.objects.filter(
            student__in=class_students,
            date=today
            # class_level=my_class  <-- UNCOMMENT if your model tracks the class the attendance was taken in
        )

        context['attendance_stats'] = {
            'present': todays_attendance.filter(status='Present').count(),
            'absent': todays_attendance.filter(status='Absent').count(),
            'late': todays_attendance.filter(status='Late').count(),
            'not_recorded': class_students.count() - todays_attendance.count()
        }

        # Ensure old warnings from previous classes don't show up in the new class
        context['active_warnings'] = AttendanceWarning.objects.filter(
            student__in=class_students,
            is_resolved=False,
            date_flagged__year=int(track_year)  # Prevents previous years' warnings from showing
        ).select_related('student').order_by('-date_flagged')

        # =========================================================
        # 3. MASTER CLASS GRADING PROGRESS LOGIC
        # =========================================================
        expected_result = class_students.annotate(
            sub_count=Count('subject')
        ).aggregate(total=Sum('sub_count'))

        total_expected = expected_result['total'] or 0
        total_entered = class_grades.count()  # Reusing our strictly filtered query from above

        if total_expected > 0:
            class_grading_progress = int((total_entered / total_expected) * 100)
        else:
            class_grading_progress = 0

        context.update({
            'track_year': track_year,
            'track_term': track_term,
            'total_expected': total_expected,
            'total_entered': total_entered,
            'class_grading_progress': class_grading_progress,
        })
    # 👆 END PROGRESS LOGIC 👆

    if is_teacher:
        context['subjects'] = Subject.objects.filter(teacher_subject=user)

    return render(request, 'students_app/dashboard.html', context)


@login_required(login_url='login')
def subject_detail(request, subject_id):
    if not request.user.has_perm('students_app.add_grade'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " access this operation. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    subject = get_object_or_404(Subject, id=subject_id)
    user = request.user

    # 1. SECURITY CHECK
    if user.is_teacher and subject.teacher_subject != user:
        messages.error(request, "You do not have permission to view this subject.")
        return redirect('students_app:dashboard')

    # 2. BASE QUERY (WITH THE NEW FOREIGN KEY LOGIC)
    # ---------------------------------------------------------
    # This is exactly where the new logic goes! We filter the students
    # before we do any searching or paginating.
    if subject.target_class:
        enrolled_students = Students.objects.filter(
            subject=subject,
            class_level=subject.target_class
        ).order_by('surname', 'first_name')
    else:
        # Fallback if you forgot to assign a target class in the admin panel
        enrolled_students = Students.objects.filter(subject=subject).order_by('surname', 'first_name')
    # ---------------------------------------------------------

    # 3. SEARCH LOGIC
    search_query = request.GET.get('q', '')
    if search_query:
        enrolled_students = enrolled_students.filter(
            Q(first_name__icontains=search_query) |
            Q(surname__icontains=search_query) |
            Q(student_id__icontains=search_query)
        )

    # 4. PAGINATION LOGIC
    paginator = Paginator(enrolled_students, 10)
    page_number = request.GET.get('page')

    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)

    # 5. CONTEXT & RENDER
    context = {
        'subject': subject,
        'students': page_obj,
        'search_query': search_query,
        'total_count': enrolled_students.count(),
    }

    return render(request, 'students_app/subject_detail.html', context)



@login_required(login_url='login')
def add_staff(request):
    # 1. SECURITY LOCK: The Friendly Bouncer
    # We check if they have the built-in Django permission to add users
    # (Or you can keep your custom 'is_headteacher' check here if you prefer!)
    if not (request.user.has_perm('auth.add_user') or getattr(request.user, 'is_headteacher', False)):
        messages.warning(request,
                         "🔒 Oops! You don't have permission to access the Staff Registration portal. Please contact the Headteacher.")
        return redirect('students_app:dashboard')

    # 2. Process the Form
    if request.method == 'POST':
        form = TeacherRegistrationForm(request.POST)
        if form.is_valid():
            # Pause saving so we can configure the password securely
            new_staff = form.save(commit=False)
            new_staff.set_password(form.cleaned_data['password'])

            # (Optional) If your custom user model still requires this boolean, keep it.
            # Otherwise, the Groups system makes this line obsolete!
            if hasattr(new_staff, 'is_teacher'):
                new_staff.is_teacher = True

            # STEP A: Save the user to the database FIRST
            new_staff.save()

            # STEP B: Grab the ticked checkboxes and assign the Roles/Groups
            # You must do this AFTER new_staff.save()
            selected_groups = form.cleaned_data.get('groups')
            if selected_groups:
                for group in selected_groups:
                    new_staff.groups.add(group)

            messages.success(request,
                             f"✅ Success! {new_staff.first_name} {new_staff.last_name} has been registered and assigned their system roles.")
            return redirect('students_app:dashboard')
        else:
            messages.error(request, "⚠️ Please correct the errors below.")
    else:
        form = TeacherRegistrationForm()

    context = {
        'form': form
    }
    return render(request, 'students_app/add_staff.html', context)

# SCHOLASTIC PDF VIEWS
@login_required(login_url='login')
def scholastic_report_pdf(request, class_level, academic_year, term):
    if not request.user.has_perm('students_app.change_students'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " access this operation. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    # 1. We use __icontains so that "2" will match "Form 2" or "2" perfectly!
    student_ids = Grade.objects.filter(
        class_level_snapshot__icontains=class_level,
        academic_year=academic_year,
        term=term
    ).values_list('student_id', flat=True).distinct()

    # 2. INSTEAD of a scary 404 error, we send them back with a polite message
    if not student_ids:
        messages.warning(
            request,
            f"No grades have been recorded yet for Form {class_level}, {academic_year} (Term {term})."
        )
        return redirect('students_app:scholastic_selector')

    students_in_class = Students.objects.filter(id__in=student_ids)

    student_list = []
    all_subjects_set = set()

    # 2. RE-USE YOUR EXISTING FUNCTION! Loop through the students and run it.
    for student in students_in_class:
        # We pass the level_filter so it only processes the relevant historical data
        term_reports, _ = build_term_reports(student, level_filter=class_level)

        # Extract the data specifically for the requested year and term
        report_data = term_reports.get(academic_year, {}).get(term)

        if report_data:
            # Gather all unique subjects taken by this class for the table headers
            for grade in report_data['grades']:
                all_subjects_set.add(grade.subject)

            # Your function didn't save the raw total_score in the dict,
            # so we quickly sum it up here for the PDF display.
            total_score = sum(g.score for g in report_data['grades'])

            student_list.append({
                'student': student,
                'average': report_data['average'],
                'position': report_data['position'],  # Uses your EXACT position logic!
                'total_score': total_score,
                'grades_list': report_data['grades']
            })

    # 3. Prepare the subjects list for the column headers (Alphabetical)
    subjects = sorted(list(all_subjects_set), key=lambda s: str(s))

    # 4. Map the grades to the exact columns so they line up perfectly in the PDF table
    for data in student_list:
        ordered_grades = []
        # USE GET_REMARK() INSTEAD OF .SCORE!
        score_map = {g.subject.id: g.get_remark() for g in data['grades_list']}

        for sub in subjects:
            # If they didn't take the subject, print a dash (-)
            ordered_grades.append(score_map.get(sub.id, '-'))

        data['ordered_grades'] = ordered_grades

    # 5. Sort the final list by the position your function generated (1st, 2nd, 3rd...)
    # We use `or 999` just in case a position somehow calculated to None
    student_list.sort(key=lambda x: x['position'] or 999)

    # 6. --- YOUR ROBUST LOGO PATH HANDLING ---
    school_profile = SchoolProfile.objects.first()
    school_logo_uri = None
    if school_profile and school_profile.logo:
        image_path = Path(school_profile.logo.path)
        if image_path.exists():
            school_logo_uri = image_path.as_uri()

    # 7. Render Context
    context = {
        'class_level': class_level,
        'academic_year': academic_year,
        'term': term,
        'subjects': subjects,
        'student_list': student_list,
        'school_profile': school_profile,
        'school_logo_uri': school_logo_uri,
    }

    html_string = render_to_string('students_app/scholastic_report_pdf.html', context)

    # 8. Generate PDF
    pdf = HTML(
        string=html_string,
        base_url=request.build_absolute_uri()
    ).write_pdf(presentational_hints=True)

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'filename="Master_Grades_Form_{class_level}_{academic_year}_Term_{term}.pdf"'

    return response


@login_required(login_url='login')
def scholastic_selector(request):
    if not request.user.has_perm('students_app.change_students'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " access this operation. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    if request.method == 'POST':
        # Grab the choices the Headteacher made in the form
        class_level = request.POST.get('class_level')
        academic_year = request.POST.get('academic_year')
        term = request.POST.get('term')

        # Redirect them to the actual PDF download link with the correct data!
        return redirect('students_app:scholastic_report_pdf', class_level=class_level, academic_year=academic_year,
                        term=term)

    # If they just clicked the button on the dashboard, show them the form
    return render(request, 'students_app/scholastic_selector.html')


# aluminai views
@login_required()

def alumni_list(request):
    if not request.user.has_perm('students_app.view_students'):
        messages.warning(request,   "🔒 Oops! You don't have permission to"
                                    " access the list of alumni. Please contact"
                                    " the Headteacher if you need this feature.")
        # Bounce them back to the safe dashboard (change this URL if your dashboard has a different name)
        return redirect('students_app:dashboard')
    alumni = Students.objects.exclude(status='Active').order_by('-year_enrolled', 'surname')
    return render(request, 'students_app/alumni_list.html', {'alumni': alumni})

# ATTENDANCE VIEW FUNCTIONS
@login_required()
def attendance_selector(request):
    if not request.user.has_perm('students_app.view_attendance'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " access this operation. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    if request.method == 'POST':
        # Grab the chosen class and date, and send the teacher to the roster page
        class_id = request.POST.get('class_level')
        date_selected = request.POST.get('attendance_date')
        return redirect('students_app:take_attendance', class_id=class_id, date_str=date_selected)

    all_classes = ClassLevel.objects.all()
    # Automatically fill the date picker with today's date
    today = date.today().strftime('%Y-%m-%d')

    return render(request, 'students_app/attendance_selector.html', {'classes': all_classes, 'today': today})


@login_required(login_url='login')
def take_attendance(request, class_id, date_str):
    if not request.user.has_perm('students_app.view_attendance'):
        messages.warning(request, "🔒 Oops! You don't have permission to access this operation.")
        return redirect('students_app:dashboard')

    attendance_date = parse_date(date_str)
    if not attendance_date:
        messages.error(request, "Invalid date format.")
        return redirect('students_app:attendance_selector')

    students = Students.objects.filter(class_level_id=class_id, status='Active').order_by('surname')
    class_obj = get_object_or_404(ClassLevel, id=class_id)


    if not students.exists():
        messages.warning(request, f"No active students found in Form {class_obj.class_level}.")
        return redirect('students_app:attendance_selector')

    # --- SAVE THE ATTENDANCE (POST REQUEST) ---
    if request.method == 'POST':
        for student in students:
            status = request.POST.get(f'status_{student.id}')
            if status:
                # 1. Save the daily attendance
                Attendance.objects.update_or_create(
                    student=student,
                    date=attendance_date,
                    defaults={'status': status}
                )

                # 👇 NEW: 2. SMART WARNING LOGIC 👇
                if status == 'Absent':
                    # Grab the 3 most recent attendance records for this student
                    last_three = Attendance.objects.filter(student=student).order_by('-date')[:3]

                    # If there are exactly 3 records, and EVERY SINGLE ONE is 'Absent'
                    if last_three.count() == 3 and all(record.status == 'Absent' for record in last_three):

                        # Check if a warning already exists so we don't spam the headteacher
                        warning_exists = AttendanceWarning.objects.filter(
                            student=student,
                            is_resolved=False
                        ).exists()

                        if not warning_exists:
                            # Trigger the Red Flag!
                            AttendanceWarning.objects.create(
                                student=student,
                                reason=f"Missed 3 consecutive days ending on {attendance_date}"
                            )

        messages.success(request, f"Attendance for form {class_obj.class_level} on {attendance_date} saved successfully!")
        return redirect('students_app:attendance_selector')

    # --- LOAD THE ROSTER (GET REQUEST) ---
    existing_records = Attendance.objects.filter(student__in=students, date=attendance_date)
    status_map = {record.student_id: record.status for record in existing_records}

    context = {
        'students': students,
        'class_obj': class_obj,
        'attendance_date': attendance_date,
        'status_map': status_map,
    }
    return render(request, 'students_app/take_attendance.html', context)


from .models import Students, Attendance, AttendanceWarning
from django.shortcuts import get_object_or_404


@login_required(login_url='login')
def student_attendance_history(request, student_id):
    student = get_object_or_404(Students, id=student_id)
    warnings = AttendanceWarning.objects.filter(student=student).order_by('-date_flagged')

    # 1. Grab filter dates from the URL (if the user clicked "Filter")
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    is_filtered = False

    # 2. Base query for all records to calculate overall stats accurately
    all_records = Attendance.objects.filter(student=student)
    total_days = all_records.exclude(status='Holiday').count()  # We don't count Holidays against them!
    present_days = all_records.filter(status='Present').count()
    absent_days = all_records.filter(status='Absent').count()
    late_days = all_records.filter(status='Late').count()

    attendance_percentage = round((present_days / total_days * 100), 1) if total_days > 0 else 0

    # 3. Apply the filter OR default to the last 5 days for the Log UI
    if start_date and end_date:
        # User requested a specific date range
        attendance_records = all_records.filter(date__range=[start_date, end_date]).order_by('-date')
        is_filtered = True
    else:
        # Default: Show only the most recent 5 records in the table
        attendance_records = all_records.order_by('-date')[:5]

    context = {
        'student': student,
        'attendance_records': attendance_records,
        'warnings': warnings,
        'is_filtered': is_filtered,  # Tells HTML to show the "Custom Filter Active" badge
        'stats': {
            'total': total_days,
            'present': present_days,
            'absent': absent_days,
            'late': late_days,
            'percentage': attendance_percentage
        }
    }
    return render(request, 'students_app/student_attendance_history.html', context)



# STATISTICS VIEW
@login_required()
def academic_statistics(request):
    if not request.user.has_perm('students_app.view_subject'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " access this operation. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')

    classes = ClassLevel.objects.all()

    selected_class = request.GET.get('class_level')
    selected_term = request.GET.get('term')
    selected_year = request.GET.get('academic_year', '2024')

    context = {
        'classes': classes,
        'selected_class': selected_class,
        'selected_term': selected_term,
        'selected_year': selected_year,
    }

    if selected_class and selected_term:
        # 1. DEMOGRAPHICS
        students = Students.objects.filter(class_level_id=selected_class, status='Active')
        total_students = students.count()
        total_boys = students.filter(gender='Male').count()
        total_girls = students.filter(gender='Female').count()

        # 2. GRADES DATA
        # 🚀 SPEED UPGRADE: select_related fetches all student and subject text names in ONE trip!
        grades = Grade.objects.filter(
            student__in=students,
            term=selected_term,
            academic_year=selected_year
        ).select_related('subject', 'student')

        def calc_pass_rate(total, passed):
            return round((passed / total * 100), 1) if total > 0 else 0

        total_exams = grades.count()
        passed_exams = grades.filter(score__gte=50).count()
        overall_pass_rate = calc_pass_rate(total_exams, passed_exams)

        # In memory filtering is faster since we already fetched `grades`
        boys_total = sum(1 for g in grades if g.student.gender == 'Male')
        boys_passed = sum(1 for g in grades if g.student.gender == 'Male' and g.score >= 50)
        boys_pass_rate = calc_pass_rate(boys_total, boys_passed)

        girls_total = sum(1 for g in grades if g.student.gender == 'Female')
        girls_passed = sum(1 for g in grades if g.student.gender == 'Female' and g.score >= 50)
        girls_pass_rate = calc_pass_rate(girls_total, girls_passed)

        # 3. SUBJECT PERFORMANCE (Best and Worst)
        # THE FIX: We group the scores in Python to force Django to give us the text names!
        from collections import defaultdict

        subject_totals = defaultdict(list)
        for grade in grades:
            # By wrapping it in str(), we FORCE Django to use the text Name Tag instead of the ID number
            text_name = str(grade.subject.name)
            subject_totals[text_name].append(grade.score)

        # Calculate the averages
        subject_stats = []
        for text_name, scores in subject_totals.items():
            avg = sum(scores) / len(scores)
            subject_stats.append({
                'subject__name': text_name,  # We keep this key name so your HTML doesn't need to change!
                'avg_score': avg
            })

        # Sort the list from highest average to lowest
        subject_stats.sort(key=lambda x: x['avg_score'], reverse=True)

        # Assign best and worst
        best_subject = subject_stats[0] if subject_stats else None
        worst_subject = subject_stats[-1] if subject_stats else None

        # Give the text names to the chart!
        chart_labels = [sub['subject__name'] for sub in subject_stats]
        chart_data = [round(sub['avg_score'], 1) for sub in subject_stats]
        # 4. OVERALL PROGRESS (Line Graph)
        progress_data = []
        for term in [1, 2, 3]:
            term_avg = Grade.objects.filter(
                student__in=students, academic_year=selected_year, term=term
            ).aggregate(Avg('score'))['score__avg']
            progress_data.append(round(term_avg, 1) if term_avg else 0)

        # ==========================================
        # 5. GRADE DISTRIBUTION BREAKDOWN
        # ==========================================

        class_obj = get_object_or_404(ClassLevel, id=selected_class)
        class_name = class_obj.class_level.lower()

        if '1' in class_name or '2' in class_name:
            remark_headers = ['A', 'B', 'C', 'D', 'F']
        else:
            remark_headers = ['1', '2', '3', '4', '5', '6', '7', '8', '9']

        subject_breakdown = {}

        # Loop through every grade and tally the remarks
        for grade in grades:
            sub_name = grade.subject.name
            remark = str(grade.get_remark())

            if sub_name not in subject_breakdown:
                subject_breakdown[sub_name] = {hdr: 0 for hdr in remark_headers}

            if remark in subject_breakdown[sub_name]:
                subject_breakdown[sub_name][remark] += 1

        breakdown_list = []
        for sub, counts in subject_breakdown.items():
            breakdown_list.append({
                'subject': sub,
                'counts': [counts[hdr] for hdr in remark_headers]
            })

        context.update({
            'has_data': True,
            'total_students': total_students,
            'total_boys': total_boys,
            'total_girls': total_girls,
            'overall_pass_rate': overall_pass_rate,
            'boys_pass_rate': boys_pass_rate,
            'girls_pass_rate': girls_pass_rate,
            'best_subject': best_subject,
            'worst_subject': worst_subject,
            'chart_labels_json': json.dumps(chart_labels),
            'chart_data_json': json.dumps(chart_data),
            'progress_data_json': json.dumps(progress_data),
            'remark_headers': remark_headers,
            'subject_breakdown': breakdown_list,
        })

    return render(request, 'students_app/statistics.html', context)

@login_required()
def calendar_of_events(request):
    if not request.user.has_perm('students_app.view_calendarevent'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " view calender of events. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    # 1. Permission Check
    # 2. Handle adding a new event via POST
    if request.method == 'POST':
        if not request.user.has_perm('students_app.add_calendarevent'):
            messages.warning(request, "🔒 Oops! You don't have permission to"
                                      " creat calendar of events. Please contact"
                                      " the Headteacher if you need this feature.")
            return redirect('students_app:dashboard')
        date_text = request.POST.get('date_text')
        activity = request.POST.get('activity')
        display_order = request.POST.get('display_order', 0)

        if date_text and activity:
            CalendarEvent.objects.create(
                date_text=date_text,
                activity=activity,
                display_order=display_order
            )
            messages.success(request, "Event added to the calendar successfully!")
            return redirect('students_app:calendar_of_events')

    # 3. Fetch all saved events to display on the template
    events = CalendarEvent.objects.all()

    context = {
        'events': events
    }

    # Now it loads a template with data, not just a blank one!
    return render(request, 'students_app/calendar.html', context)
@login_required(login_url='login')
def delete_calendar_event(request, event_id):
    if not request.user.has_perm('students_app.view_subjectdepartment'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " to delete the calendar of events. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    if request.method == 'POST':
        event = get_object_or_404(CalendarEvent, id=event_id)
        event.delete()
        messages.success(request, "Event removed successfully.")

    return redirect('students_app:calendar_of_events')

# VIEWS FOR BULKY PROMOTIONS
@login_required(login_url='login')
def promote_students(request):
    if not request.user.has_perm('students_app.change_students'):
        messages.warning(request,
                         "🔒 Oops! You don't have permission to access this operation. Please contact the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')

    classes = ClassLevel.objects.all().order_by('class_level')

    # 1. GET: Which class are we looking at right now?
    source_class_id = request.GET.get('class_filter')
    students = None
    source_class_obj = None

    if source_class_id:
        students = Students.objects.filter(class_level_id=source_class_id, status='Active').order_by('surname')
        source_class_obj = get_object_or_404(ClassLevel, id=source_class_id)

    # 2. POST: Handle the form submission
    if request.method == 'POST':
        action_type = request.POST.get('action_type')
        target_class_id = request.POST.get('target_class')
        student_ids = request.POST.getlist('selected_students')

        # Need the hidden source class ID to know who to promote if "Promote All" is clicked
        hidden_source_id = request.POST.get('hidden_source_class')

        # ACTION A: PROMOTE THE ENTIRE CLASS (No checkboxes needed)
        if action_type == 'promote_all':
            if not target_class_id:
                messages.error(request, "Please select a Target Class to promote them to.")
            else:
                target_class = get_object_or_404(ClassLevel, id=target_class_id)
                class_to_update = Students.objects.filter(class_level_id=hidden_source_id, status='Active')
                count = class_to_update.count()

                # Get a list of the students BEFORE updating, so we can loop through them
                students_list = list(class_to_update)

                # 1. Promote them to the new class
                class_to_update.update(class_level=target_class)

                # 2. Fetch the subjects assigned to the NEW class
                target_subjects = Subject.objects.filter(target_class=target_class)

                # 3. Auto-assign the new curriculum to every student
                for student in students_list:
                    student.subject.set(target_subjects)

                messages.success(request,
                                 f"Successfully promoted {count} students to {target_class.class_level}. Subjects have been auto-updated!")

            return redirect(f"{request.path}?class_filter={hidden_source_id}")

        # Ensure they ticked boxes for the next actions
        if not student_ids:
            messages.error(request, "You must tick at least one student for this action.")
            return redirect(f"{request.path}?class_filter={hidden_source_id}")

        students_to_update = Students.objects.filter(id__in=student_ids)
        count = students_to_update.count()

        # ACTION B: PROMOTE ONLY SELECTED STUDENTS
        if action_type == 'promote_selected':
            if not target_class_id:
                messages.error(request, "Please select a Target Class.")
            else:
                target_class = get_object_or_404(ClassLevel, id=target_class_id)

                # Grab instances before updating
                students_list = list(students_to_update)

                # 1. Promote class level
                students_to_update.update(class_level=target_class)

                # 2. Fetch new subjects
                target_subjects = Subject.objects.filter(target_class=target_class)

                # 3. Reassign curriculum
                for student in students_list:
                    student.subject.set(target_subjects)

                messages.success(request,
                                 f"Successfully promoted {count} selected students to {target_class.class_level}. Subjects have been auto-updated!")

        # ACTION C: GRADUATE & ARCHIVE
        elif action_type == 'graduate_selected':
            # We don't wipe subjects on graduation so they keep their historical final-year record
            students_to_update.update(status='Graduated')
            messages.success(request, f"Successfully graduated {count} students. They are now in the Alumni Archive.")

        return redirect(f"{request.path}?class_filter={hidden_source_id}")

    context = {
        'classes': classes,
        'students': students,
        'source_class_obj': source_class_obj,
        'current_class_filter': source_class_id
    }
    return render(request, 'students_app/promote_students.html', context)


from django.http import JsonResponse


# Make sure your Grades model is imported at the top!
def get_existing_grades(request, student_id):
    year = request.GET.get('year')
    term = request.GET.get('term')

    if year and term:
        # Assuming your model is called 'Grades' or 'Grade'
        existing_grades = Grade.objects.filter(student_id=student_id, academic_year=year, term=term)

        if existing_grades.exists():
            # Build a dictionary of { "score_1": 85, "score_2": 92 } matching subject IDs
            grade_dict = {f"score_{grade.subject.id}": grade.score for grade in existing_grades}
            return JsonResponse({'exists': True, 'grades': grade_dict})

    return JsonResponse({'exists': False})


from django.contrib.auth import authenticate, login, update_session_auth_hash


def change_temp_password(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        # 1. Verify the user and the temporary password
        user = authenticate(request, username=username, password=old_password)

        if user is not None:
            # 2. Check if new passwords match
            if new_password == confirm_password:
                # Basic backend length check (JavaScript handles the complex checks)
                if len(new_password) >= 8:
                    # 3. Securely set the new password
                    user.set_password(new_password)
                    user.save()

                    # 4. Log them in automatically with the new password
                    update_session_auth_hash(request, user)  # Prevents them from getting logged out
                    login(request, user)

                    messages.success(request,
                                     f"🎉 Password updated successfully! Welcome to the portal, {user.first_name}.")
                    return redirect('students_app:dashboard')
                else:
                    messages.error(request, "Your new password must be at least 8 characters long.")
            else:
                messages.error(request, "The new passwords do not match. Please try again.")
        else:
            messages.error(request, "Invalid Username or Temporary Password.")

    # If anything fails, bounce them back to the login page
    return redirect('login')  # Replace 'login' with your actual login URL name if it's different


from .forms import EditStaffProfileForm, ManageStaffRolesForm


# -----------------------------------------
# 1. EDIT PROFILE VIEW
# -----------------------------------------
@login_required(login_url='login')
def edit_staff_profile(request, user_id):
    is_admin = getattr(request.user, 'is_headteacher', False) or request.user.groups.filter(
        name__in=['Headteacher', 'Admin']).exists()
    if not is_admin:
        messages.error(request, "Access Denied.")
        return redirect('students_app:dashboard')

    staff = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        form = EditStaffProfileForm(request.POST, request.FILES, instance=staff)
        if form.is_valid():
            form.save()
            messages.success(request, f"Profile for {staff.first_name} updated successfully.")
            return redirect('students_app:teacher_subject_list', teachers_id=staff.id)
    else:
        form = EditStaffProfileForm(instance=staff)

    return render(request, 'students_app/edit_staff.html', {'form': form, 'staff': staff})


# -----------------------------------------
# 2. MANAGE ROLES VIEW
# -----------------------------------------
@login_required(login_url='login')
def manage_staff_roles(request, user_id):
    is_admin = getattr(request.user, 'is_headteacher', False) or request.user.groups.filter(
        name__in=['Headteacher', 'Admin']).exists()
    if not is_admin:
        messages.error(request, "Access Denied.")
        return redirect('students_app:dashboard')

    staff = get_object_or_404(User, id=user_id)

    # Find their current form class if they have one
    current_form_class = staff.my_form_class.first()

    # NEW: Find their current department if they are an HOD
    current_dept = getattr(staff, 'my_headed_department', None)

    if request.method == 'POST':
        form = ManageStaffRolesForm(request.POST)
        if form.is_valid():
            # 1. Update Booleans
            staff.is_teacher = form.cleaned_data['is_teacher']
            staff.is_hod = form.cleaned_data['is_hod']
            staff.is_deputy = form.cleaned_data['is_deputy']
            staff.is_headteacher = form.cleaned_data['is_headteacher']

            # 2. Update Groups
            staff.groups.set(form.cleaned_data['groups'])
            staff.save()

            # 3. Update Form Class Assignment safely
            new_form_class = form.cleaned_data['form_class']

            # If they had a class, and it changed or was removed, clear the old one first
            if current_form_class and current_form_class != new_form_class:
                current_form_class.form_teacher = None
                current_form_class.save()

            # Assign the new class
            if new_form_class:
                new_form_class.form_teacher = staff
                new_form_class.save()

            # 4. NEW: Update Department HOD safely!
            new_dept = form.cleaned_data['department']

            # Clear old department if it changed or was removed
            if current_dept and current_dept != new_dept:
                current_dept.head_of_department = None
                current_dept.save()

            # Assign new department
            if new_dept:
                new_dept.head_of_department = staff
                new_dept.save()

            messages.success(request, f"Roles for {staff.first_name} updated successfully.")
            return redirect('students_app:teacher_subject_list', teachers_id=staff.id)
    else:
        # Pre-fill the form with their current data
        initial_data = {
            'groups': staff.groups.all(),
            'is_teacher': staff.is_teacher,
            'is_hod': staff.is_hod,
            'is_deputy': staff.is_deputy,
            'is_headteacher': staff.is_headteacher,
            'form_class': current_form_class,
            'department': current_dept  # NEW: Pre-fills the department dropdown
        }
        form = ManageStaffRolesForm(initial=initial_data)

    return render(request, 'students_app/manage_roles.html', {'form': form, 'staff': staff})

# -----------------------------------------
# 3. REMOVE STAFF VIEW
# -----------------------------------------
@login_required(login_url='login')
def delete_staff(request, user_id):
    is_admin = getattr(request.user, 'is_headteacher', False) or request.user.groups.filter(
        name__in=['Headteacher', 'Admin']).exists()
    if not is_admin:
        messages.error(request, "Access Denied.")
        return redirect('students_app:dashboard')

    staff = get_object_or_404(User, id=user_id)

    # Prevent the Headteacher from accidentally deleting themselves!
    if staff == request.user:
        messages.error(request, "You cannot delete your own account.")
        return redirect('students_app:teachers_list')

    if request.method == 'POST':
        name = staff.first_name
        staff.delete()
        messages.success(request, f"Staff member {name} has been permanently removed.")
        return redirect('students_app:teachers_list')

    return render(request, 'students_app/delete_staff.html', {'staff': staff})


@login_required()
def add_class_level(request):
    # Security Check: Only Headteacher/Admin can create classes
    is_admin = getattr(request.user, 'is_headteacher', False) or request.user.groups.filter(name__in=['Headteacher', 'Admin']).exists()
    if not is_admin:
        messages.error(request, "Access Denied. Only administrators can add new classes.")
        return redirect('students_app:dashboard')

    if request.method == 'POST':
        form = ClassLevelForm(request.POST)
        if form.is_valid():
            # Check if this specific class level already exists to prevent duplicates
            class_level = form.cleaned_data.get('class_level')
            if ClassLevel.objects.filter(class_level=class_level).exists():
                messages.warning(request, f"Form {class_level} already exists in the system!")
            else:
                form.save()
                messages.success(request, f"Form {class_level} has been successfully created!")
                return redirect('students_app:dashboard') # Change this to wherever you want them to land
    else:
        form = ClassLevelForm()

    return render(request, 'students_app/add_class.html', {'form': form})


@login_required(login_url='login')
def add_master_subject(request):
    is_admin = getattr(request.user, 'is_headteacher', False) or request.user.groups.filter(name__in=['Headteacher', 'Admin']).exists()
    if not is_admin:
        messages.error(request, "Access Denied. Only administrators can add new curriculum subjects.")
        return redirect('students_app:dashboard')

    if request.method == 'POST':
        form = MasterSubjectForm(request.POST)
        if form.is_valid():
            subject_name = form.cleaned_data.get('name')
            form.save()
            messages.success(request, f"The subject '{subject_name}' has been added to the school curriculum!")
            if "save_add_another" in request.POST:
                return redirect(
                    "students_app:add_master_subject"
                )
            return redirect('students_app:dashboard')
    else:
        form = MasterSubjectForm()

    return render(request, 'students_app/add_master_subject.html', {'form': form})


@login_required(login_url='login')
def department_events(request, subdept_id):
    sub_dept = get_object_or_404(SubDepartment, id=subdept_id)
    # Fetch events ordered by start date
    events = DepartmentEvent.objects.filter(sub_department=sub_dept).order_by('start_date')

    context = {
        'sub_dept': sub_dept,
        'events': events,
    }
    return render(request, 'students_app/department_events.html', context)


@login_required(login_url='login')
def add_department_event(request, subdept_id):
    sub_dept = get_object_or_404(SubDepartment, id=subdept_id)

    if request.method == 'POST':
        form = DepartmentEventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.sub_department = sub_dept
            event.save()
            messages.success(request, f"Event '{event.title}' added successfully!")
            return redirect('students_app:department_events', subdept_id=sub_dept.id)
    else:
        form = DepartmentEventForm()

    return render(request, 'students_app/add_department_event.html', {'form': form, 'sub_dept': sub_dept})


@login_required(login_url='login')
def print_department_events(request, subdept_id):
    """A clean, stripped-down view optimized for 'Save as PDF'"""
    sub_dept = get_object_or_404(SubDepartment, id=subdept_id)
    events = DepartmentEvent.objects.filter(sub_department=sub_dept).order_by('start_date')

    return render(request, 'students_app/print_department_events.html', {'sub_dept': sub_dept, 'events': events})




User = get_user_model()


@login_required(login_url='login')
def broadcast_message(request):
    """View for Headteacher to send messages to all staff."""
    is_admin = getattr(request.user, 'is_headteacher', False) or request.user.groups.filter(
        name__in=['Headteacher', 'Admin']).exists()

    if not is_admin:
        messages.error(request, "Access Denied. Only administration can broadcast messages.")
        return redirect('students_app:dashboard')

    if request.method == 'POST':
        title = request.POST.get('title')
        message = request.POST.get('message')

        # Find ALL staff members (Teachers, HODs, Deputies)
        staff_members = User.objects.filter(
            Q(is_teacher=True) | Q(is_hod=True) | Q(is_deputy=True) | Q(groups__name__in=['teachers', 'HOD', 'Deputy'])
        ).distinct()

        # Bulk create notifications efficiently
        notifications = [
            StaffNotification(recipient=staff, title=title, message=message)
            for staff in staff_members
        ]
        StaffNotification.objects.bulk_create(notifications)

        messages.success(request, f"Message successfully broadcasted to {len(notifications)} staff members!")
        return redirect('students_app:dashboard')

    return render(request, 'students_app/broadcast_message.html')


@login_required(login_url='login')
def read_notification(request, notification_id):
    """View for staff to read the message and mark it as read."""
    # Ensure staff can only read THEIR OWN notifications
    notification = get_object_or_404(StaffNotification, id=notification_id, recipient=request.user)

    # Mark as read
    if not notification.is_read:
        notification.is_read = True
        notification.save()

    return render(request, 'students_app/read_notification.html', {'notification': notification})


@login_required(login_url='login')
def notification_list(request):
    """View for staff to see all their received messages (Inbox)."""
    # Fetch all notifications, newest first
    notifications = StaffNotification.objects.filter(recipient=request.user).order_by('-created_at')

    return render(request, 'students_app/notification_list.html', {'notifications': notifications})

# DOCUMENT UPLOADING AND ARCHIVE VIEWS

from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Folder, Document
from .forms import FolderForm, DocumentForm

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages


# Make sure to import your models and forms here


from django.core.exceptions import ValidationError
@login_required()
def document_manager(request):
    # BASE PERMISSION: Can they view the page at all?
    if not request.user.has_perm('students_app.view_folder'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " view folders. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')

    folders = Folder.objects.all().prefetch_related('documents')

    if request.method == 'POST':

        # 1. CREATE FOLDER
        if 'create_folder' in request.POST:
            if not request.user.has_perm('students_app.add_folder'):
                messages.error(request, "⛔ You do not have permission to create folders.")
                return redirect('students_app:document_manager')

            folder_form = FolderForm(request.POST)
            if folder_form.is_valid():
                folder_form.save()
                messages.success(request, "Folder created successfully!")
                return redirect('students_app:document_manager')

        # 2. BULK UPLOAD DOCUMENTS
        elif 'upload_document' in request.POST:
            if not request.user.has_perm('students_app.add_document'):
                messages.error(request, "⛔ You do not have permission to upload documents.")
                return redirect('students_app:document_manager')

            folder_id = request.POST.get('folder')
            title_input = request.POST.get('title', '').strip()
            files = request.FILES.getlist('file')

            if folder_id and files:
                folder_instance = Folder.objects.filter(id=folder_id).first()
                if folder_instance:
                    uploaded_count = 0
                    for uploaded_file in files:
                        if title_input and len(files) == 1:
                            final_title = title_input
                        elif title_input and len(files) > 1:
                            final_title = f"{title_input} - {uploaded_file.name}"
                        else:
                            final_title = uploaded_file.name

                        doc = Document(
                            title=final_title,
                            folder=folder_instance,
                            file=uploaded_file
                        )
                        try:
                            doc.save()
                            uploaded_count += 1
                        except ValidationError as e:
                            # Quota exceeded (or other validation failure) —
                            # stop here rather than silently skipping the
                            # rest of the batch, and report what happened.
                            messages.error(
                                request,
                                f"⛔ Upload stopped at '{uploaded_file.name}': {'; '.join(e.messages)}"
                            )
                            break

                    if uploaded_count:
                        messages.success(request, f"Successfully uploaded {uploaded_count} document(s)!")
                else:
                    messages.error(request, "The selected folder does not exist.")
            else:
                messages.warning(request, "Please select a folder and at least one file.")

            return redirect('students_app:document_manager')

        # 3. DELETE SPECIFIC DOCUMENT
        elif 'delete_document' in request.POST:
            if not request.user.has_perm('students_app.delete_document'):
                messages.error(request, "⛔ You do not have permission to delete documents.")
                return redirect('students_app:document_manager')

            doc_id = request.POST.get('doc_id')
            doc = Document.objects.filter(id=doc_id).first()
            if doc:
                title = doc.title
                doc.file.delete(save=False)
                doc.delete()  # runs our overridden delete() -> decrements used_storage_mb
                messages.warning(request, f"File '{title}' was permanently deleted.")
            return redirect('students_app:document_manager')

        # 4. DELETE ENTIRE FOLDER
        elif 'delete_folder' in request.POST:
            if not request.user.has_perm('students_app.delete_folder'):
                messages.error(request, "⛔ You do not have permission to delete folders.")
                return redirect('students_app:document_manager')

            folder_id = request.POST.get('folder_id')
            folder = Folder.objects.filter(id=folder_id).first()
            if folder:
                folder_name = folder.name

                # Iterating through documents calling doc.delete() triggers our overridden
                # Document.delete() method for every file inside the folder:
                # 1. Permanently removes physical file from disk
                # 2. Subtracts file size from tenant.used_storage_mb
                # 3. Removes Document record from database
                for doc in folder.documents.all():
                    doc.delete()

                # Permanently delete the Folder record from the database
                folder.delete()

                messages.error(request, f"Folder '{folder_name}' and all its contents were permanently destroyed.")
            else:
                messages.error(request, "The requested folder could not be found.")

            return redirect('students_app:document_manager')
    # GET REQUEST LOAD
    folder_form = FolderForm()
    document_form = DocumentForm()

    # 1. Grab the current tenant (school)
    tenant = request.tenant

    # 2. Calculate storage metrics
    used = tenant.used_storage_mb or 0.0
    allocated = tenant.allocated_storage_mb or 1.0  # Prevent division by zero if not set
    percentage = (used / allocated) * 100

    # 3. Cap values so the UI doesn't break (e.g., progress bar going over 100%)
    storage_percentage = min(percentage, 100)
    remaining_storage = max(allocated - used, 0.0)

    # 4. Update your context dictionary
    context = {
        'folders': folders,
        'folder_form': folder_form,
        'document_form': document_form,

        # 👇 NEW STORAGE VARIABLES 👇
        'storage_percentage': storage_percentage,
        'remaining_storage': remaining_storage,
    }
    return render(request, 'students_app/document_manager.html', context)






from .models import SchoolCoverPhoto, CarouselEvent
from .forms import SchoolCoverPhotoForm, CarouselEventForm

@login_required(login_url='login')
def edit_school_photos(request):
    if not request.user.has_perm('students_app.view_subjectdepartment'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " view departments. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    # Get the school's profile, or create an empty one if they are brand new
    profile, created = SchoolCoverPhoto.objects.get_or_create(pk=1)
    events = CarouselEvent.objects.all()

    if request.method == 'POST':
        # 1. Update Cover Photo
        if 'update_profile' in request.POST:
            profile_form = SchoolCoverPhotoForm(request.POST, request.FILES, instance=profile)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Cover photo updated successfully!")
                return redirect('students_app:edit_school_photos')

        # 2. Add Sliding Event Photo
        elif 'add_event' in request.POST:
            event_form = CarouselEventForm(request.POST, request.FILES)
            if event_form.is_valid():
                event_form.save()
                messages.success(request, "Event photo added to the slide!")
                return redirect('students_app:edit_school_photos')

        # 3. Delete Sliding Photo
        elif 'delete_event' in request.POST:
            event_id = request.POST.get('event_id')
            event = CarouselEvent.objects.filter(id=event_id).first()
            if event:
                event.image.delete(save=False)
                event.delete()
                messages.warning(request, "Event photo removed.")
            return redirect('students_app:edit_school_photos')

    profile_form = SchoolCoverPhotoForm(instance=profile)
    event_form = CarouselEventForm()


    context = {
        'profile_form': profile_form,
        'event_form': event_form,
        'events': events,
    }
    return render(request, 'students_app/edit_school_photos.html', context)




# FLEXIBLE MASTER GRADING SYSETEM


@login_required(login_url='users:login')
def academic_settings(request):
    # Security: Only Admins/Headteachers should access this configuration hub
    is_admin = request.user.is_headteacher or request.user.is_superuser or request.user.groups.filter(
        name__in=['Headteacher', 'Admin']).exists()
    if not is_admin:
        messages.error(request, "🔒 Access Denied: Only administrators can configure academic settings.")
        return redirect('students_app:dashboard')

    # Fetch all grading systems and prefetch their boundaries (rules) to prevent N+1 database queries
    grading_systems = GradingSystem.objects.prefetch_related('boundaries').all()

    # Fetch all classes, ordered by the level_order we defined
    classes = ClassLevel.objects.select_related('grading_system', 'form_teacher').order_by('level_order')

    context = {
        'grading_systems': grading_systems,
        'classes': classes,
        'page_title': 'Academic Configuration Hub'
    }
    return render(request, 'students_app/settings/academic_settings.html', context)




@login_required(login_url='users:login')
def add_grading_system(request):
    if request.method == "POST":
        form = GradingSystemForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✨ Grading System successfully created!")
            return redirect('students_app:academic_settings')
    else:
        form = GradingSystemForm()

    context = {
        'form': form,
        'title': 'Create New Grading Scale',
        'back_url': 'students_app:academic_settings'
    }
    return render(request, 'students_app/settings/generic_form.html', context)


@login_required(login_url='users:login')
def add_grade_boundary(request, system_id):
    # Find the specific grading system from the URL
    system = get_object_or_404(GradingSystem, id=system_id)

    if request.method == "POST":
        form = GradeBoundaryForm(request.POST)
        form.instance.grading_system = system
        if form.is_valid():
            # commit=False creates the object but pauses before saving to the database
            boundary = form.save(commit=False)

            # Automatically link this rule to the system we found in the URL
            boundary.grading_system = system
            boundary.save()

            messages.success(request, f"✅ Rule '{boundary.grade_name}' added to {system.name}!")
            return redirect('students_app:academic_settings')
    else:
        form = GradeBoundaryForm()

    context = {
        'form': form,
        'title': f'Add Grade Rule to: {system.name}',
        'back_url': 'students_app:academic_settings'
    }
    return render(request, 'students_app/settings/generic_form.html', context)





@login_required(login_url='users:login')
def add_class_level(request):
    if request.method == "POST":
        form = ClassLevelForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "🏫 New Class successfully registered!")
            return redirect('students_app:academic_settings')
    else:
        form = ClassLevelForm()

    context = {
        'form': form,
        'title': 'Register New Class',
        'back_url': 'students_app:academic_settings'
    }
    return render(request, 'students_app/settings/generic_form.html', context)




@login_required(login_url='users:login')
def edit_class_level(request, class_id):
    # Fetch the specific class they clicked on
    class_obj = get_object_or_404(ClassLevel, id=class_id)

    if request.method == "POST":
        # Pass instance=class_obj so it UPDATES instead of creating a new one
        form = ClassLevelForm(request.POST, instance=class_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f"🏫 {class_obj.class_level} successfully updated!")
            return redirect('students_app:academic_settings')
    else:
        # Pre-fill the form with the existing class data
        form = ClassLevelForm(instance=class_obj)

    context = {
        'form': form,
        'title': f'Edit Class: {class_obj.class_level}',
        'back_url': 'students_app:academic_settings'
    }
    # We reuse our magical generic form!
    return render(request, 'students_app/settings/generic_form.html', context)



@login_required(login_url='users:login')
def edit_grade_boundary(request, boundary_id):
    # Fetch the specific grade boundary they clicked on
    boundary = get_object_or_404(GradeBoundary, id=boundary_id)

    if request.method == "POST":
        # Pass instance=boundary so it updates instead of creating a new one
        form = GradeBoundaryForm(request.POST, instance=boundary)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                f"✅ Grade rule '{boundary.grade_name}' successfully updated!"
            )

            return redirect('students_app:academic_settings')

    else:
        # Pre-fill the form with the existing boundary data
        form = GradeBoundaryForm(instance=boundary)

    context = {
        'form': form,
        'title': f'Edit Grade Rule: {boundary.grade_name}',
        'back_url': 'students_app:academic_settings',
    }

    # Reuse the same generic form template
    return render(
        request,
        'students_app/settings/generic_form.html',
        context
    )


@login_required()
def subject_department_list(request):
    if not request.user.has_perm('students_app.view_subjectdepartment'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " view departments. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    """The dashboard view showing all created departments."""
    departments = SubjectDepartment.objects.all()
    return render(request, 'students_app/subject_department_list.html', {'departments': departments})

@login_required(login_url='login')
def add_subject_department(request):
    if not request.user.has_perm('students_app.add_subjectdepartment'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " access this operation. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    """Handles displaying and saving the department creation form."""
    if request.method == "POST":
        form = SubjectDepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "🎉 Department created successfully!")
            return redirect('students_app:subject_department_list')
    else:
        form = SubjectDepartmentForm()

    # Feeding data directly into your dynamic template!
    context = {
        'form': form,
        'title': 'Create Subject Department',
        'back_url': 'students_app:subject_department_list'
    }
    return render(request, 'students_app/settings/generic_form.html', context)


@login_required(login_url='users:login')
def edit_subject_department(request, dept_id):
    if not request.user.has_perm('students_app.change_subjectdepartment'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " access this operation. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    # Fetch the specific class they clicked on
    dept_obj = get_object_or_404(SubjectDepartment, id=dept_id)

    if request.method == "POST":
        # Pass instance=class_obj so it UPDATES instead of creating a new one
        form = SubjectDepartmentForm(request.POST, instance=dept_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f"🏫 {dept_obj.departments} successfully updated!")
            return redirect('students_app:subject_department_list')
    else:
        # Pre-fill the form with the existing class data
        form = SubjectDepartmentForm(instance=dept_obj)

    context = {
        'form': form,
        'title': f'Edit : {dept_obj.departments} Department',
        'back_url': 'students_app:subject_department_list'
    }
    # We reuse our magical generic form!
    return render(request, 'students_app/settings/generic_form.html', context)

@login_required(login_url='login')
def delete_subject_department(request, dept_id):
    if not request.user.has_perm('students_app.delete_subjectdepartment'):
        messages.warning(request, "🔒 Oops! You don't have permission to"
                                  " access this operation. Please contact"
                                  " the Headteacher if you need this feature.")
        return redirect('students_app:dashboard')
    # Security check: Only allow deletion via POST request
    if request.method == 'POST':
        # Grab the department or return a 404 if it doesn't exist
        dept = get_object_or_404(SubjectDepartment, id=dept_id)

        # Save the name for the success message before deleting
        dept_name = dept.departments

        # Delete the record
        dept.delete()

        # Send a success message to the template
        messages.success(request, f'Department "{dept_name}" was successfully deleted.')

    # Redirect back to the departments list page
    return redirect('students_app:subject_department_list')  # Replace with your actual list view name






import io
import zipfile
import datetime

@login_required(login_url='users:login')
def download_class_reports(request, class_id, academic_year, term):
    # 1. SECURITY CHECK
    if not request.user.has_perm('students_app.change_attendance'):
        messages.warning(request, "🔒 Oops! You don't have permission to access to download the zip reports.")
        return redirect( request.META.get('HTTP_REFERER', 'students_app:dashboard'))

    # 2. FETCH CLASS AND ACTIVE STUDENTS
    school_class = get_object_or_404(ClassLevel, id=class_id)
    students = Students.objects.filter(class_level=school_class, status='Active')

    if not students.exists():
        messages.warning(request, "No active students found in this class.")
        return redirect(request.META.get('HTTP_REFERER', 'students_app:dashboard'))

    # 3. SETUP IMAGES
    school_profile = SchoolProfile.objects.first()

    def get_image_uri(image_field):
        if image_field and hasattr(image_field, 'path'):
            image_path = Path(image_field.path)
            if image_path.exists():
                return image_path.as_uri()
        return None

    school_logo_uri = get_image_uri(school_profile.logo) if school_profile else None
    head_sig_uri = get_image_uri(school_profile.headteacher_signature) if school_profile else None

    # 4. ZIP BUFFER AND COUNTER
    zip_buffer = io.BytesIO()
    files_added = 0

    # Build possible year strings based on URL
    clean_academic_year = str(academic_year).strip()
    possible_years = [clean_academic_year, clean_academic_year.replace('-', '/')]
    if '-' in clean_academic_year:
        possible_years.extend(clean_academic_year.split('-'))
    elif '/' in clean_academic_year:
        possible_years.extend(clean_academic_year.split('/'))

    target_term_str = str(term).strip().lower()  # E.g., "1"

    # 5. GENERATE PDFS
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for student in students:
            term_reports, total_students = build_term_reports(student)


            # 👇 BULLETPROOF SEARCH 👇
            year_data = {}
            actual_year_used = clean_academic_year
            report_data = None

            # Loop through the database dictionary keys and FORCE them into strings to check
            for db_year, terms_dict in term_reports.items():
                db_year_str = str(db_year).strip()

                # Check if the DB string matches ANY of our possible strings
                if db_year_str in possible_years:
                    year_data = terms_dict
                    actual_year_used = db_year_str

                    for db_term, data in year_data.items():
                        # Compare "1" to "1", handling if DB saved it as "Term 1"
                        db_term_str = str(db_term).strip().lower()
                        if db_term_str == target_term_str or target_term_str in db_term_str:
                            report_data = data

                            break
                    break  # Stop looking for years, we found it

            # Skip students who don't have generated data for this term
            if not report_data :

                continue

            # Safely get Teacher Signature
            teacher_sig_uri = None
            if getattr(student, 'class_level', None) and getattr(student.class_level, 'form_teacher', None):
                teacher_sig_uri = get_image_uri(student.class_level.form_teacher.signature)

            # Build Context
            context = {
                'student': student,
                'academic_year': actual_year_used,
                'term': term,
                'grades': report_data['grades'],
                'average': report_data['average'],
                'position': report_data['position'],
                'promotion_status': report_data['promotion_status'],
                'head_remark': report_data['head_remark'],
                'class_comment': report_data.get('class_comment', ''),
                'total_students': total_students,
                'school_profile': school_profile,
                'school_logo_uri': school_logo_uri,
                'head_sig_uri': head_sig_uri,
                'teacher_sig_uri': teacher_sig_uri,
                'static_root': settings.STATIC_ROOT,
            }

            # Generate PDF bytes
            html_string = render_to_string('students_app/school_report_pdf.html', context)

            pdf_bytes = HTML(
                string=html_string,
                base_url=request.build_absolute_uri()
            ).write_pdf(presentational_hints=True)

            # File output
            safe_first = str(getattr(student, 'first_name', student.id)).strip().replace(' ', '_')
            safe_last = str(getattr(student, 'last_name', '')).strip().replace(' ', '_')
            safe_year = actual_year_used.replace('/', '-')
            filename = f"{safe_first}_{safe_last}_Report_{safe_year}_Term_{term}.pdf"

            zip_file.writestr(filename, pdf_bytes)
            files_added += 1

            # 6. RETURN RESPONSE
    if files_added == 0:
        messages.warning(request,
                         f"No reports could be generated for {clean_academic_year} Term {term}. Ensure grades are fully entered for this class.")
        return redirect(request.META.get('HTTP_REFERER', 'students_app:dashboard'))

    response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')

    class_name_safe = str(school_class).replace(' ', '_')
    safe_year_zip = clean_academic_year.replace('/', '-')
    response[
        'Content-Disposition'] = f'attachment; filename="{class_name_safe}_Reports_{safe_year_zip}_Term_{term}.zip"'

    return response


# =========================================================
# 1. MAIN GRADEBOOK VIEW (Grid & Rank Tabs)
# =========================================================
@login_required(login_url='login')
def subject_gradebook(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    user = request.user

    # SECURITY CHECK: Is this user allowed to grade this subject?
    is_admin = getattr(user, 'is_headteacher', False) or getattr(user, 'is_deputy', False) or user.groups.filter(
        name__in=['Headteacher', 'Admin', 'Deputy']).exists()
    is_subject_teacher = getattr(user, 'is_teacher', False) and subject.teacher_subject == user

    # Optional: Allow HODs to view/edit their department's subjects
    is_hod = getattr(user, 'is_hod', False) and hasattr(user,
                                                        'my_headed_department') and user.my_headed_department == subject.departments

    if not (is_admin or is_subject_teacher or is_hod):
        messages.warning(request, "🔒 You do not have permission to access this subject's gradebook.")
        return redirect('students_app:dashboard')

    # Fetch all active students taking this specific subject
    students = Students.objects.filter(subject=subject, status='Active').order_by('surname', 'first_name')

    # Dynamic years for the dropdown
    current_year = datetime.datetime.now().year
    years = list(range(current_year - 2, current_year + 5))

    # --- HANDLE FORM SUBMISSION (BULK SAVE) ---
    if request.method == "POST":
        academic_year = request.POST.get('academic_year')
        term = request.POST.get('term')

        if not academic_year or not term:
            messages.error(request, "Please select an academic year and term.")
            return redirect('students_app:subject_gradebook', subject_id=subject.id)

        grades_saved = 0
        # Loop through all students in the class
        for student in students:
            # Look for an input field named e.g., 'score_45'
            score_val = request.POST.get(f'score_{student.id}')

            if score_val and score_val.strip() != '':
                try:
                    score = float(score_val)
                    # Create or update the grade in a single rapid action
                    Grade.objects.update_or_create(
                        student=student,
                        subject=subject,
                        academic_year=academic_year,
                        term=term,
                        defaults={
                            "score": score,
                            "class_level_snapshot": str(student.class_level) if student.class_level else "Unassigned"
                        }
                    )
                    grades_saved += 1
                except ValueError:
                    pass  # Ignore if they accidentally typed text instead of a number

        messages.success(request, f"Successfully saved {grades_saved} grades for {subject.name}!")
        return redirect('students_app:subject_gradebook', subject_id=subject.id)

    context = {
        'subject': subject,
        'students': students,
        'years': years,
    }
    return render(request, 'students_app/subject_gradebook.html', context)


# =========================================================
# 2. AJAX ENDPOINT (Fetches Live Data for the Form)
# =========================================================
@login_required
def fetch_subject_grades(request, subject_id):
    """
    Silently called by Javascript when the teacher changes the Year/Term dropdown.
    Returns existing grades so the input boxes can be pre-filled.
    """
    year = request.GET.get('year')
    term = request.GET.get('term')

    grades = Grade.objects.filter(subject_id=subject_id, academic_year=year, term=term)

    # Build a dictionary formatted as { "student_id": "score" }
    grades_dict = {str(grade.student.id): grade.score for grade in grades}

    return JsonResponse({
        'exists': len(grades_dict) > 0,
        'grades': grades_dict
    })


# =========================================================
# 3. PDF EXPORT (Ranked Student Results)
# =========================================================
@login_required
def export_subject_ranked_pdf(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    year = request.GET.get('academic_year')
    term = request.GET.get('term')

    if not year or not term:
        messages.error(request, "Please select an academic year and term to generate a PDF.")
        return redirect('students_app:subject_gradebook', subject_id=subject.id)

    # Fetch grades and sort them automatically by highest score
    ranked_grades = Grade.objects.filter(
        subject=subject, academic_year=year, term=term
    ).select_related('student').order_by('-score')

    school_profile = SchoolProfile.objects.first()

    context = {
        'subject': subject,
        'academic_year': year,
        'term': term,
        'ranked_grades': ranked_grades,
        'school_profile': school_profile,
    }

    # Generate PDF
    html_string = render_to_string('students_app/subject_ranked_pdf.html', context)
    pdf_bytes = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    filename = f"{subject.name}_Ranked_Results_Term_{term}_{year.replace('/', '-')}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response




# DETAILS OF THE ANNOUCEMENTS AND NEWS ARTICLES


def news_detail(request, pk):
    # Fetch the specific active article using its primary key (pk)
    article = get_object_or_404(NewsArticle, pk=pk, is_active=True)
    return render(request, 'students_app/news_detail.html', {'article': article})



def announcement_detail(request, pk):
    # Fetch the specific active announcement
    announcement = get_object_or_404(Announcement, pk=pk, is_active=True)
    return render(request, 'students_app/announcement_detail.html', {'announcement': announcement})




