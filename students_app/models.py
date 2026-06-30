from django.db import models
import datetime
from django.conf import settings

from django.db import models
from django.conf import settings  # Make sure this is imported at the top!


class SubjectDepartment(models.Model):
    DEPARTMENT_SUBJECT_CHOICES = [
        ('science', 'science'),
        ('language', 'language'),
        ('humanities', 'humanities')
    ]

    # Note: I added max_length=100 here. Django requires max_length for CharFields!
    departments = models.CharField(max_length=100, null=True, blank=True, choices=DEPARTMENT_SUBJECT_CHOICES)

    # 1. THE HOD (Only one person in charge)
    head_of_department = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='my_headed_department',
        help_text="The HOD responsible for this department."
    )

    # 👇 2. NEW: THE STAFF MEMBERS 👇
    # This perfectly replaces the field we deleted from CustomUser!
    staff_members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='departments_assigned',
        help_text="Teachers belonging to this department."
    )

    def __str__(self):
        return f'{self.departments}'
# SUBJECTS MODELS

class ClassLevel(models.Model):
    CLASS_LEVELS = [
        ('1', 'Form 1'),
        ('2', 'Form 2'),
        ('3', 'Form 3'),
        ('4', 'Form 4'),
        ]

    class_level = models.CharField(max_length=20, choices=CLASS_LEVELS)
    form_teacher = models.OneToOneField(
        settings.AUTH_USER_MODEL,  # Or 'Teacher' if you use a separate model
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='my_form_class',
        help_text="The teacher responsible for this entire class."
    )

    def __str__(self):
        return self.get_class_level_display()

class MasterSubject(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="e.g., Mathematics, Computer Science, Economics")

    def __str__(self):
        return self.name
class Subject(models.Model):
    name = models.ForeignKey(MasterSubject, on_delete=models.CASCADE, related_name='class_instances')

    code = models.CharField(max_length=10, unique=True)

    teacher_subject = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'is_teacher': True},
        related_name='subjects_taught'
    )

    departments = models.ForeignKey('SubjectDepartment', on_delete=models.CASCADE)

    target_class = models.ForeignKey(
        'ClassLevel',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='assigned_subjects'
    )

    class Meta:
        # NEW: This stops you from creating two "Physics" subjects for the same class!
        unique_together = ('name', 'target_class')

    def __str__(self):
        # NEW: This ensures it shows up in dropdown menus as "Physics - Form 1"
        if self.target_class:
            return f'{self.name} - {self.target_class}'
        return self.name

class Students(models.Model):
    current_year = datetime.date.today().year


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


    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Graduated', 'Graduated'),
        ('Transferred', 'Transferred'),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    first_name = models.CharField(max_length=20)
    surname = models.CharField(max_length=20)
    student_id = models.CharField(max_length=10, unique=True)
    age = models.PositiveIntegerField(null=True, blank=True)
    class_level = models.ForeignKey(ClassLevel, on_delete=models.CASCADE)
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


from django.db import models


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
    class_level_snapshot = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        unique_together = ("student", "subject", "academic_year", "term",)

    def __str__(self):
        return (f'{self.student.first_name} - '
                f'{self.student.surname} - '
                f'{self.subject.name} - '
                f'{self.score} - '
                f'{self.term} -'
                f' {self.academic_year}')

    def save(self, *args, **kwargs):
        # Capture the class level at the time this grade is recorded
        if not self.class_level_snapshot and self.student and self.student.class_level:
            self.class_level_snapshot = str(self.student.class_level.class_level)
        super().save(*args, **kwargs)

    def get_remark(self):
        """
        Returns the grade (A–F for Form 1–2, 1–9 for Form 3–4)
        based on the score and the class level recorded at the time.
        """
        # 1. Convert the level to a lowercase string so we can safely search it
        level_to_check = str(self.class_level_snapshot or self.student.class_level).lower()

        # 2. Check if the string CONTAINS the number '1' or '2'
        if '1' in level_to_check or '2' in level_to_check:
            # ---------- FORM 1 & 2 (A, B, C, D, F) ----------
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

        else:
            # ---------- FORM 3 & 4 (1–9) ----------
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
from django.db import models
from django.db import connection


def tenant_logo_path(instance, filename):
    """
    Dynamically generates a path based on the current tenant's schema name.
    Example output: 'school_logos/mangochi/my_logo.png'
    """
    tenant_name = connection.schema_name
    return f'school_logos/{tenant_name}/{filename}'


class SchoolProfile(models.Model):
    name = models.CharField(max_length=255)  # School name

    # 👇 UPDATED: Changed upload_to to use the new function (no quotes around it!)
    logo = models.ImageField(upload_to=tenant_logo_path, blank=True, null=True)

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
    employment_number = models.IntegerField(unique=True, blank=True, null=True)
    gender = models.CharField(max_length=50, choices=GENDER_CHOICES)
    subject = models.ManyToManyField(Subject)
    class_level = models.ForeignKey(ClassLevel, on_delete=models.CASCADE)


    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class TeachingAssignment(models.Model):
        teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="assignments")
        subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
        class_level = models.ForeignKey(ClassLevel, on_delete=models.CASCADE,null=True, blank=True)
        class Meta:
            unique_together = ('teacher', 'subject', 'class_level')

        def __str__(self):
            return f"{self.teacher} - {self.subject} ({self.class_level})"


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


from django.conf import settings


class SubDepartmentRole(models.Model):
    ROLE_CHOICES = [
        ('HEAD', 'Head of Department'),
        ('VICE', 'Vice Head'),
        ('MEMBER', 'Member'),
    ]

    sub_department = models.ForeignKey(
        'SubDepartment',
        on_delete=models.CASCADE,
        related_name='roles'
    )

    # --- THE FIX ---
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Now points to your CustomUser table!
        on_delete=models.CASCADE,
        related_name='department_roles',
        limit_choices_to={'is_teacher': True}  # Ensures only teachers are selectable
    )
    # ---------------

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES
    )

    def __str__(self):
        return f"{self.teacher.first_name} {self.teacher.last_name} - {self.get_role_display()} ({self.sub_department.name})"

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


# ATTENDANCE REGISTER MODELS
class Attendance(models.Model):
    STATUS_CHOICES = [
        ('Present', 'Present'),
        ('Absent', 'Absent'),
        ('Late', 'Late'),
        ('Holiday', 'Holiday'),
    ]

    student = models.ForeignKey(Students, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Present')

    class Meta:
        # This guarantees a student can only have ONE attendance record per day!
        unique_together = ['student', 'date']

    def __str__(self):
        return f"{self.student.first_name} {self.student.surname} - {self.date} - {self.status}"



class AttendanceWarning(models.Model):
    """
    Automatically flags students who miss multiple consecutive days.
    The Headteacher can view these and mark them as resolved.
    """
    student = models.ForeignKey(Students, on_delete=models.CASCADE, related_name='attendance_warnings')
    date_flagged = models.DateField(auto_now_add=True)

    # E.g., "Missed 3 consecutive days ending on 2026-06-15"
    reason = models.CharField(max_length=255)

    # Headteacher action tracking
    is_resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    resolution_notes = models.TextField(blank=True, help_text="What action was taken? (e.g., Called parents)")

    class Meta:
        ordering = ['-date_flagged']

    def __str__(self):
        status = "Resolved" if self.is_resolved else "ACTION REQUIRED"
        return f"[{status}] Warning for {self.student.first_name} {self.student.surname}"


class StaffNotification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']  # Newest messages show up first!

    def __str__(self):
        return f"{self.title} - {self.recipient.username}"


# FILE UPLOADING MODELS
from django.db import connection  # 👈 This lets us see which tenant is active
import os


# 1. The Physical Security Guard
def tenant_directory_path(instance, filename):
    """
    Dynamically creates a file path based on the current tenant and folder.
    Format: media/tenant_name/folder_name/filename.ext
    """
    tenant_name = connection.schema_name
    folder_name = instance.folder.name.replace(" ", "_").lower()
    return f'school_documents/{tenant_name}/{folder_name}/{filename}'


# 2. The Folder Model
class Folder(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']


# 3. The Document Model
class Document(models.Model):
    title = models.CharField(max_length=200, null=True, blank=True)
    folder = models.ForeignKey(Folder, related_name='documents', on_delete=models.CASCADE)

    # Notice we pass our security guard function to 'upload_to'
    file = models.FileField(upload_to=tenant_directory_path)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    # Optional: Track who uploaded it if you have your users set up!
    # uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-uploaded_at']



# 👇 Add this near the top if you don't have it
from django.db import connection

def tenant_image_path(instance, filename):
    """Saves images securely into each school's private folder"""
    tenant_name = connection.schema_name
    return f'school_images/{tenant_name}/{filename}'

class SchoolCoverPhoto(models.Model):
    # This stores the main background Hero image
    cover_photo = models.ImageField(upload_to=tenant_image_path, blank=True, null=True)

    def save(self, *args, **kwargs):
        # This is a cool trick: forcing pk=1 ensures a school can ONLY have 1 profile.
        # If they upload a new cover photo, it overwrites the old record!
        self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return "School Profile Settings"

class CarouselEvent(models.Model):
    # These are the sliding photos
    image = models.ImageField(upload_to=tenant_image_path)
    title = models.CharField(max_length=200, blank=True, help_text="Short title for the event")
    description = models.TextField(blank=True, help_text="Write a short description to appear on the photo")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']



























