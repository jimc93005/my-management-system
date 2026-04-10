from django.contrib.auth.decorators import login_required
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404

from django.views.decorators.http import require_POST
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Sum, Avg
from django.contrib import messages
from django.utils.timezone import now
from weasyprint import HTML
from pathlib import Path
from django.conf import settings

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, Http404
from django.template.loader import render_to_string
from .forms import TeacherRegistrationForm




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



def index(request):
    return render(request, 'students_app/index.html')

# VIEWS FOR STUDENTS FUNCTIONS


@login_required
def student_list(request):
    query = request.GET.get('q', '')
    students = Students.objects.all()

    if query:
        students = students.filter(
            Q(first_name__icontains=query) |
            Q(surname__icontains=query) |
            Q(student_id__icontains=query) |
            Q(created_at__icontains=query)
        )

    paginator = Paginator(students, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {'students': page_obj, 'query':query,'page_obj':page_obj}

    return render(request, 'students_app/students_list.html', context)

# MODIFYING STUDENTS DATA


# Make sure Subject is imported at the top!

def add_student(request):
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


def delete_student(request, student_id):
    student = get_object_or_404(Students, pk=student_id)
    if request.method == 'POST':
        student.delete()
        return redirect('students_app:students_list')
    context = {'student':student}

    return render(request, 'students_app/delete_student.html', context)

# editing student


import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages


# Make sure Subject is imported at the top of your views.py

def edit_student(request, student_id):
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

def subjects_list(request):
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
def add_subject(request):
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


def edit_subject(request, subject_id):
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


def delete_subject(request, subject_id):
    subject = get_object_or_404(Subject, pk=subject_id)
    if request.method == 'POST':
        subject.delete()
        return redirect('students_app:subjects_list')

    context = {'subject': subject}

    return render(request, 'students_app/delete_subject.html', context)


# GROUPING STUDENTS BY CLASS

def class_list(request):
    classes = ClassLevel.CLASS_LEVELS
    return render(request, 'students_app/class_list.html', {'classes': classes})


def students_by_class(request, class_level):
    query = request.GET.get('q', '')  # Get search term from URL
    student_list = Students.objects.filter(class_level=class_level)

    if query:
        # Filter by name or ID
        student_list = student_list.filter(
            Q(first_name__icontains=query) |
            Q(surname__icontains=query) |
            Q(student_id__icontains=query)
        )

    student_list = student_list.order_by('surname')

    # Pagination
    paginator = Paginator(student_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'class_level': class_level,
        'count': student_list.count(),
        'query': query  # Pass back to template to keep text in search box
    }
    return render(request, 'students_app/students_by_class.html', context)
# GRADES VIEWS

# students_app/views.py
# students_app/views.py

@login_required
def add_grade(request, student_id):
    student = get_object_or_404(Students, id=student_id)
    user = request.user

    # -------------------------------------------------------
    # 1. SECURITY FILTER: Only fetch subjects permitted for this user
    # -------------------------------------------------------
    if user.is_headteacher or user.is_deputy:
        # Admins can grade any subject the student is taking
        subjects = student.subject.all()

    elif user.is_hod:
        # HODs can only grade subjects within their department
        if hasattr(user, 'department'):
            subjects = student.subject.filter(department=user.department)
        else:
            subjects = student.subject.none()

    elif user.is_teacher:
        # ---> THE FOREIGN KEY UPGRADE IS HERE <---
        # We now compare the student's Class object directly to the Subject's Class object!
        subjects = student.subject.filter(
            teacher_subject=user,
            target_class=student.class_level
        )

    else:
        subjects = student.subject.none()

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


def student_profile(request, student_id):
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


def edit_grade(request, grade_id):
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
def delete_grade(request, grade_id):
    grade = get_object_or_404(Grade, id=grade_id)

    grade.delete()   # permanent delete

    messages.success(request, "Grade permanently deleted.")
    return redirect("students_app:student_profile", student_id=grade.student.id)

# -----------------------------
# Delete all grades in a specific term
# -----------------------------
@require_POST
def delete_term_grades(request, student_id, year, term):
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
def delete_year_grades(request, student_id, year):
    student = get_object_or_404(Students, id=student_id)

    Grade.objects.filter(
        student=student,
        academic_year=year
    ).delete()   # permanent delete

    messages.success(request, f"All grades for Year {year} permanently deleted.")
    return redirect("students_app:student_profile", student_id=student.id)


# SCHOOL REPORT FORMATION AND VIEWS

def edit_school_profile(request):
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
def school_report(request, student_id, academic_year, term):
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


def school_report_pdf(request, student_id, academic_year, term):
    student = get_object_or_404(Students, id=student_id)
    school_profile = SchoolProfile.objects.first()

    # (Your existing logic for report data...)
    term_reports, total_students = build_term_reports(student)
    report_data = term_reports.get(academic_year, {}).get(term)

    if not report_data:
        raise Http404("Report not found")

    # --- THE FIX: ROBUST PATH HANDLING ---
    school_logo_uri = None
    if school_profile and school_profile.logo:
        # 1. Get the absolute path on the hard drive
        #    e.g., C:\Users\You\Project\media\logos\school.png
        image_path = Path(school_profile.logo.path)

        # 2. Verify it exists
        if image_path.exists():
            # 3. Convert to URI automatically (handles file:/// and slashes for you)
            school_logo_uri = image_path.as_uri()
        else:
            print(f"DEBUG: Image missing at {image_path}")

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

        # Pass the formatted URI
        'school_logo_uri': school_logo_uri,

        # Also pass STATIC_ROOT for any CSS files if needed later
        'static_root': settings.STATIC_ROOT,
    }

    html_string = render_to_string(
        'students_app/school_report_pdf.html',
        context
    )

    # Enable "presentational_hints" to support HTML attributes like width/height better
    pdf = HTML(
        string=html_string,
        base_url=request.build_absolute_uri()
    ).write_pdf(presentational_hints=True)

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = (
        f'filename="school_report_{student.id}_{academic_year}_term_{term}.pdf"'
    )

    return response


# DEPARTMENTS VIEWS
def department_list(request):

    departments = Department.objects.all().order_by('name')
    context = {'departments': departments}

    return render(request, 'students_app/department_list.html', context)


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

def edit_department(request, department_id):
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



def department_delete(request, department_id):
    department = get_object_or_404(Department, id=department_id)

    if request.method == 'POST':
        department.delete()

    return redirect('students_app:department_list')


def subdepartment_list(request, department_id):
    department = get_object_or_404(Department, id=department_id)
    sub_departments = department.sub_departments.all()
    context = {'department': department, 'sub_departments': sub_departments}

    return render(request, 'students_app/subdepartment_list.html', context)


def subdepartment_create(request, department_id):
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


def subdepartment_roles(request, subdepartment_id):
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


def subdepartment_role_create(request, subdepartment_id):
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
def teachers_list(request):

    teachers = Teacher.objects.all().order_by('first_name')
    context = {'teachers':teachers}

    return render(request, 'students_app/teachers_list.html', context)


def edit_teachers(request, teachers_id):
    teachers = get_object_or_404(Teacher, id=teachers_id)

    if request.method != 'POST':
        form = TeacherForm(instance=teachers)

    else:
        form = TeacherForm(instance=teachers, data=request.POST)
        if form.is_valid():
            teachers_instance = form.save(commit=False)
            teachers_instance.save()
            messages.success(request, "teacher details updated successfully.")

            return redirect('students_app:teachers_list')

    context = {'form': form, 'teachers': teachers}

    return render(request, 'students_app/edit_teachers.html', context)


def delete_teachers(request, teachers_id):
    teachers = get_object_or_404(Teacher, id=teachers_id)
    if request.method == "POST":
        teachers.delete()
        return redirect('students_app:teachers_list')


def add_teachers(request):
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

def teacher_subject_list(request, teachers_id):
    teacher = get_object_or_404(Teacher, id=teachers_id)
    teachers_assignments = teacher.assignments.select_related(
        'subject', 'class_level'
    ).all()
    context = {'teachers_assignments': teachers_assignments, 'teacher':teacher}

    return render(request, 'students_app/teacher_subject_list.html', context)


# VIEWS FOR PROMOTING STUDENTS FROM ONE CLASS TO ANOTHER
from django.shortcuts import get_object_or_404, redirect, render


# Import your Class model if class_level is a ForeignKey
# from .models import Students, ClassModel

def change_class_level(request, student_id):
    student = get_object_or_404(Students, id=student_id)

    if request.method == "POST":
        new_class_id = request.POST.get('new_class')

        if new_class_id:
            student.class_level_id = new_class_id
            student.save()

            return redirect('students_app:student_profile', student_id=student.id)

    context = {
        'student': student,
        # 'all_classes': all_classes
    }
    return render(request, "students_app/change_class.html", context)


# LOG IN AND LOG OUR VIEWS AND AUTHENTICATION SYSTEMS
# Make sure to import your User model at the top if you haven't!
from django.contrib.auth import get_user_model

User = get_user_model()


@login_required
def dashboard(request):
    user = request.user
    context = {}

    # -----------------------------------------------------
    # 1. HEADTEACHER & DEPUTY VIEW (The Command Center)
    # -----------------------------------------------------
    if user.is_headteacher or user.is_deputy:
        # Calculate school-wide analytics
        total_students = Students.objects.count()
        total_teachers = User.objects.filter(is_teacher=True).count()
        total_subjects = Subject.objects.count()

        # We can also get a quick list of recently added students
        recent_students = Students.objects.order_by('-id')[:5]

        context = {
            'dashboard_title': "School Administration Dashboard",
            'is_admin': True,  # This tells the HTML to show the Admin UI
            'total_students': total_students,
            'total_teachers': total_teachers,
            'total_subjects': total_subjects,
            'recent_students': recent_students,
        }

    # -----------------------------------------------------
    # 2. HOD VIEW
    # -----------------------------------------------------
    elif user.is_hod:
        # ... your existing HOD logic ...
        pass

    # -----------------------------------------------------
    # 3. TEACHER VIEW
    # -----------------------------------------------------
    elif user.is_teacher:
        subjects_to_display = Subject.objects.filter(teacher_subject=user)
        context = {
            'dashboard_title': "Teacher Dashboard",
            'is_admin': False,  # This tells the HTML to show the Teacher UI
            'subjects': subjects_to_display,
        }

    return render(request, 'students_app/dashboard.html', context)

@login_required
def subject_detail(request, subject_id):
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

@login_required
def add_staff(request):
    # 1. SECURITY LOCK: Only Headteachers and Deputies allowed
    if not (request.user.is_headteacher or request.user.is_deputy):
        messages.error(request, "Security Alert: You do not have permission to access the Staff Registration portal.")
        return redirect('students_app:dashboard')

    # 2. Process the Form
    if request.method == 'POST':
        form = TeacherRegistrationForm(request.POST)
        if form.is_valid():
            # Pause saving so we can configure the backend roles
            new_teacher = form.save(commit=False)

            # Securely hash the password
            new_teacher.set_password(form.cleaned_data['password'])

            # AUTOMATIC ROLE ASSIGNMENT: Make sure they are marked as a teacher!
            new_teacher.is_teacher = True

            # Now save to the database
            new_teacher.save()

            messages.success(request,
                             f"Success! {new_teacher.first_name} {new_teacher.last_name} has been added to the teaching staff.")
            return redirect('students_app:dashboard')
    else:
        form = TeacherRegistrationForm()

    context = {
        'form': form
    }
    return render(request, 'students_app/add_staff.html', context)


# SCHOLASTIC PDF VIEWS
def scholastic_report_pdf(request, class_level, academic_year, term):
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
    subjects = sorted(list(all_subjects_set), key=lambda s: s.name)

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



def scholastic_selector(request):
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
