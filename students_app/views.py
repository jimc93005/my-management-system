from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404

from django.views.decorators.http import require_POST
from django.db.models import Q
from django.core.paginator import Paginator
from django.db.models import Sum, Avg
from django.contrib import messages
from django.utils.timezone import now
from weasyprint import HTML
from pathlib import Path
from django.conf import settings

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, Http404
from django.template.loader import render_to_string




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
from .models import SubDepartmentRole
from .forms import SubDepartmentRoleForm



def index(request):
    return render(request, 'students_app/index.html')

# VIEWS FOR STUDENTS FUNCTIONS


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


def add_student(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)

        if form.is_valid():
            student = form.save(commit=False)  # save student WITHOUT subjects
            student.save()                      # now student has an ID

            form.save_m2m()                     # 🔑 saves subjects (ManyToMany)

            return redirect('students_app:students_list')
    else:
        form = StudentForm()

    return render(request, 'students_app/add_student.html', {'form': form})

# deleting student from the list of students


def delete_student(request, student_id):
    student = get_object_or_404(Students, pk=student_id)
    if request.method == 'POST':
        student.delete()
        return redirect('students_app:students_list')
    context = {'student':student}

    return render(request, 'students_app/delete_student.html', context)

# editing student


def edit_student(request, student_id):
    student = get_object_or_404(Students, pk=student_id)

    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)

        if form.is_valid():
            student_instance = form.save(commit=False)
            student_instance.save()
            form.save_m2m()  # ✅ THIS IS THE KEY LINE

            messages.success(request, "Student details updated successfully.")
            return redirect('students_app:students_list')

    else:
        form = StudentForm(instance=student)

    context = {
        'form': form,
        'student': student
    }
    return render(request, 'students_app/edit_student.html', context)


# VIEWS FOR SUBJECT FUNCTIONS

def subjects_list(request):
    query = request.GET.get('q', '')
    subjects = Subject.objects.all()
    students = Students.objects.all()

    for student in students:
        latest_grade = student.grades.order_by(
            '-academic_year', '-term'
        ).first()

        if latest_grade:
            student.report_year = latest_grade.academic_year
            student.report_term = latest_grade.term
        else:
            student.report_year = None
            student.report_term = None

    if query:
        subjects = subjects.filter(
            Q(name__icontains=query) |
            Q(subject_teacher__icontains=query) |
            Q(code__icontains=query)

        )

    paginator = Paginator(subjects, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {'subjects': page_obj, 'query': query, 'page_obj': page_obj, 'students':students}
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
    classes = Students.CLASS_LEVELS
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

def add_grade(request, student_id):
    # -------------------------------------------------------
    # 1️⃣ Get the student object or show 404 if not found
    # -------------------------------------------------------
    student = get_object_or_404(Students, id=student_id)

    # -------------------------------------------------------
    # 2️⃣ Get all subjects related to this student
    # If you want all subjects in the school:
    # subjects = Subject.objects.all()
    # If you want only subjects the student already has:
    subjects = student.subject.all()
    # -------------------------------------------------------

    # -------------------------------------------------------
    # 3️⃣ Academic years for dropdown
    # -------------------------------------------------------
    years = list(range(2025, 2050))

    # -------------------------------------------------------
    # 4️⃣ Handle form submission
    # -------------------------------------------------------
    if request.method == "POST":
        academic_year = request.POST.get('academic_year')
        term = request.POST.get('term')

        # Check if year and term are selected
        if not academic_year or not term:
            context = {
                'student': student,
                'subjects': subjects,
                'years': years,
                'error': "Please select academic year and term before submitting."
            }
            return render(request, 'students_app/add_grade.html', context)

        # Loop through subjects and save grades
        for subject in subjects:
            score = request.POST.get(f'score_{subject.id}')
            if score:
                Grade.objects.update_or_create(
                    student=student,
                    subject=subject,
                    academic_year=academic_year,
                    term=term,
                    defaults={"score": score}
                )

        # Redirect to student list with success message
        return redirect('students_app:students_list')

    # -------------------------------------------------------
    # 5️⃣ Show the form initially
    # -------------------------------------------------------
    context = {
        "student": student,
        "subjects": subjects,
        "years": years,
        "message": None  # Can show "Grades saved!" if redirected back with GET
    }
    return render(request, "students_app/add_grade.html", context)


# STUDENT PROFILE


def student_profile(request, student_id):
    student = get_object_or_404(Students, id=student_id)

    term_reports, total_students = build_term_reports(student)

    context = {
        'student': student,
        'term_reports': term_reports,
        'total_students': total_students,
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














