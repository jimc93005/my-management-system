from django.db import models
import datetime


# SUBJECTS MODELS

class Subject(models.Model):
    AVAILABLE_SUBJECTS = [
        ('Mathematics', 'Mathematics'),
        ('Physics', 'Physics'),
        ('Chemistry', 'Chemistry'),
        ('English', 'English'),
        ('Chichewa', 'Chichewa'),
        ('Agriculture', 'Agriculture'),
        ('Geography', 'Geography'),
        ('Life Skills', 'Life Skills'),
        ('Social', 'Social'),
        ('History', 'History'),
        ('Biology', 'Biology'),

    ]
    name = models.CharField(max_length=20, choices=AVAILABLE_SUBJECTS)
    subject_teacher = models.CharField(max_length=20)
    code = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return f'{self.name}'


class Students(models.Model):
    current_year = datetime.date.today().year
    CLASS_LEVELS = [
        ('1', 'Form 1'),
        ('2', 'Form 2'),
        ('3', 'Form 3'),
        ('4', 'Form 4'),

    ]
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other')

    ]

    ORPHANHOOD_CHOICES = [
        ('Both parents alive', 'Both parents alive'),
        ('Single orphan', 'Single orphan'),
        ('Double orphan', 'Double orphan')
    ]
    YEAR_CHOICES = [
        (year, year) for year in range(current_year, current_year - 6, -1)

    ]
    first_name = models.CharField(max_length=20)
    surname = models.CharField(max_length=20)
    student_id = models.CharField(max_length=10, unique=True)
    age = models.PositiveIntegerField(null=True, blank=True)
    class_level = models.CharField(max_length=10, choices=CLASS_LEVELS)
    year_enrolled = models.IntegerField(null=True, blank=True, choices=YEAR_CHOICES)
    gender = models.CharField(max_length=20,choices=GENDER_CHOICES)
    disability = models.CharField(max_length=20)
    parental_contact = models.CharField(max_length=20, null=True, blank=True)
    address = models.CharField(max_length=30, null=True, blank=True)
    orphanhood = models.CharField(max_length=20, null=True, blank=True, choices=ORPHANHOOD_CHOICES)
    class_teachers_comment = models.CharField(null=True, blank=True)
    Headteachers_comment = models.CharField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    subject = models.ManyToManyField(Subject, blank=True)

    def __str__(self):
        return f'First name: {self.first_name}   Surname: {self.surname}   ID: {self.student_id}'


# GRADING MODELS


class Grade(models.Model):
    TERM_CHOICES = [
        ('1', 'Term 1'),
        ('2', 'Term 2'),
        ('3', 'Term 3'),

        ]
    student = models.ForeignKey(Students, on_delete=models.CASCADE, related_name='grades')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    score = models.FloatField()
    academic_year = models.CharField(max_length=10)
    term = models.CharField(max_length=10, choices=TERM_CHOICES)

    class Meta:
        unique_together = ("student", "subject", "academic_year", "term",)

    def __str__(self):
        return (f'{self.student.first_name} - '
                f'{self.student.surname} - '
                f'{self.subject.name} - '
                f'{self.score} - '
                f'{self.term} -'
                f' {self.academic_year}')

    def get_remark(self):
        """
        Returns the grade (A–F for Form 1–2, 1–9 for Form 3–4)
        based on the score.
        """

        class_level = self.student.class_level

        # ---------- FORM 1 & 2 (A, B, C, D, F) ----------
        if class_level in ['1', '2']:

            if self.score >= 80:
                return 'A'
            elif self.score >= 70:
                return 'B'
            elif self.score >= 60:
                return 'C'
            elif self.score >= 50:
                return 'D'
            else:
                return 'F'

        # ---------- FORM 3 & 4 (1–9) ----------
        else:
            if self.score >= 80:
                return '1'
            elif self.score >= 75:
                return '2'
            elif self.score >= 65:
                return '3'
            elif self.score >= 55:
                return '4'
            elif self.score >= 45:
                return '5'
            elif self.score >= 35:
                return '6'
            elif self.score >= 25:
                return '7'
            elif self.score >= 15:
                return '8'
            else:
                return '9'

        # ---------------------------
        #   COMMENT SYSTEM
        # ---------------------------

    def get_comment(self):
        """
        Returns a human comment based on the remark.
        """

        remark = self.get_remark()

        # Comments for A–F
        comment_map_letters = {
            'A': 'Excellent performance',
            'B': 'Very Good',
            'C': 'Good',
            'D': 'Pass, but needs improvement',
            'F': 'Failed, must work harder'
        }

        # Comments for 1–9
        comment_map_numbers = {
            '1': 'Excellent',
            '2': 'Very Good',
            '3': 'Good',
            '4': 'Credit',
            '5': 'Satisfactory',
            '6': 'Pass',
            '7': 'Weak',
            '8': 'Very Weak',
            '9': 'Fail'
        }

        # Return the correct comments depending on remark type
        if remark in comment_map_letters:
            return comment_map_letters[remark]
        elif remark in comment_map_numbers:
            return comment_map_numbers[remark]
        else:
            return "No comment"


# SCHOOL REPORT MODELS
class SchoolProfile(models.Model):
    name = models.CharField(max_length=255)  # School name
    logo = models.ImageField(upload_to='school_logos/', blank=True, null=True)  # Upload logo
    headteacher_name = models.CharField(max_length=255)  # Headteacher
    contact = models.CharField(max_length=255, blank=True)  # Contact info
    address = models.TextField(blank=True)  # Optional address
    email = models.EmailField(max_length=200, blank=True, null=True)
    motto = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return self.name


# TEACHERS MODELS
class Teacher(models.Model):
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other')
        ]
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    employment_number = models.IntegerField(unique=True)
    gender = models.CharField(max_length=50, choices=GENDER_CHOICES)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


# MANAGEMENT SYSTEMS
class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# SUBDEPARTMENTS
class SubDepartment(models.Model):
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='sub_departments'
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.department.name})"


class SubDepartmentRole(models.Model):
    ROLE_CHOICES = [
        ('HEAD', 'Head of Department'),
        ('VICE', 'Vice Head'),
        ('MEMBER', 'Member'),
    ]

    sub_department = models.ForeignKey(
        SubDepartment,
        on_delete=models.CASCADE,
        related_name='roles'
    )
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name='department_roles'
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES
    )

    def __str__(self):
        return f"{self.teacher} - {self.get_role_display()} ({self.sub_department.name})"



class DepartmentEvent(models.Model):
    sub_department = models.ForeignKey(
        SubDepartment,
        on_delete=models.CASCADE,
        related_name='events'
    )
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    academic_year = models.CharField(max_length=10)
    term = models.CharField(max_length=10)

    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.sub_department.name})"


