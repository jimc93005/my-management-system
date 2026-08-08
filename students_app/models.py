from django.db import models
import datetime
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator

# 1. THE MASTER TEMPLATE
class GradingSystem(models.Model):
    """e.g., 'Junior Secondary Scale (A-F)', 'Senior Secondary Scale (1-9)'"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


# 2. THE DYNAMIC RULES
class GradeBoundary(models.Model):
    """Replaces your hardcoded if/else statements."""
    grading_system = models.ForeignKey(GradingSystem, on_delete=models.CASCADE, related_name='boundaries')
    min_score = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ],
        help_text="Enter a value between 0 and 100."
    )

    max_score = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ],
        help_text="Enter a value between 0 and 100."
    )
    grade_name = models.CharField(max_length=10)  # e.g., 'A', '1', 'B+'
    remark = models.CharField(max_length=100)  # e.g., 'Excellent', 'Very Good'

    def clean(self):
        super().clean()

        # 1. Safety check: If fields are empty in the form, don't validate them yet
        if self.min_score is None or self.max_score is None:
            return

        # 2. Check if min is greater than max (Your original logic, enhanced for UI)
        if self.min_score > self.max_score:
            raise ValidationError({
                'min_score': "Minimum score cannot be greater than maximum score."
            })
        if self.grading_system_id is None:
            return
        # 3. PREVENT OVERLAPPING RULES:
        # Check if any other rule in THIS specific grading system overlaps with this range
        overlapping_query = GradeBoundary.objects.filter(
            grading_system=self.grading_system,
            min_score__lte=self.max_score,
            max_score__gte=self.min_score
        )

        # If we are EDITING an existing rule, don't let it compare against itself!
        if self.pk:
            overlapping_query = overlapping_query.exclude(pk=self.pk)

        if overlapping_query.exists():
            # Find which rule it clashes with to give a helpful error message
            clashing_rule = overlapping_query.first()
            raise ValidationError(
                f"🚨 Overlap Error: This range ({self.min_score} - {self.max_score}) "
                f"conflicts with the existing rule '{clashing_rule.grade_name}' "
                f"({clashing_rule.min_score} - {clashing_rule.max_score})."
            )

    def save(self, *args, **kwargs):
        self.full_clean()  # Keeps your excellent validation safeguard intact!
        super().save(*args, **kwargs)




    class Meta:
        ordering = ['-min_score']  # Sorts highest to lowest

    def __str__(self):
        system_name = self.grading_system.name if self.grading_system else "No System"
        return f"{system_name}: {self.grading_system.name}: {self.min_score}-{self.max_score} ({self.grade_name})"



# 3. THE DYNAMIC CLASS LEVEL
class ClassLevel(models.Model):
    """Replaces hardcoded 'Form 1', 'Form 2' strings."""
    class_level = models.CharField(max_length=50, unique=True)  # e.g., "Form 1"
    level_order = models.IntegerField(default=0, help_text="Used to sort classes (e.g., 1 for Form 1, 2 for Form 2)")

    # Link the class to a specific grading system!
    grading_system = models.ForeignKey(GradingSystem, on_delete=models.SET_NULL, null=True, blank=True)

    # Link the class to its Form Teacher (solving our signature issue!)
    form_teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="my_form_class",)

    class Meta:
        ordering = ['level_order']

    def __str__(self):
        return self.class_level



class SubjectDepartment(models.Model):
    # 1. THE DEPARTMENT DETAILS
    departments = models.CharField(
        max_length=100,
        unique=True,
        help_text="Enter the department name (e.g., Science, Languages, Humanities)"
    )

    description = models.TextField(
        null=True,
        blank=True,
        help_text="Optional: Briefly describe the focus of this department."
    )

    # 2. THE HOD (Only one person in charge)
    head_of_department = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='my_headed_department',  # Cleaner related name
        help_text="The HOD responsible for this department."
    )

    # 3. THE STAFF MEMBERS
    staff_members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='departments_assigned',
        help_text="Teachers belonging to this department."
    )

    class Meta:
        ordering = ['departments']  # Automatically sorts departments alphabetically in the admin/UI
        verbose_name = "Subject Department"
        verbose_name_plural = "Subject Departments"

    def __str__(self):
        return self.departments




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
# GRADING MASTER MODELS

from django.db import models


class Grade(models.Model):
    TERM_CHOICES = [
        ('1', 'Term 1'),
        ('2', 'Term 2'),
        ('3', 'Term 3'),
    ]
    student = models.ForeignKey('Students', on_delete=models.CASCADE, related_name='grades')
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE)
    score = models.FloatField()
    academic_year = models.CharField(max_length=10)
    term = models.CharField(max_length=10, choices=TERM_CHOICES)

    # -------------------------------------------------------
    # SNAPSHOT FIELDS (Crucial for Historical SaaS Accuracy)
    # -------------------------------------------------------
    class_level_snapshot = models.CharField(max_length=50, null=True, blank=True)
    grade_letter_snapshot = models.CharField(max_length=10, null=True, blank=True)
    remark_snapshot = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        unique_together = ("student", "subject", "academic_year", "term",)

    def __str__(self):
        return (f'{self.student.first_name} - '
                f'{self.student.surname} - '
                f'{self.subject.name} - '
                f'{self.score} - '
                f'Term {self.term} - '
                f'{self.academic_year}')

    def save(self, *args, **kwargs):
        # 1. Capture the class level snapshot
        if not self.class_level_snapshot and self.student and self.student.class_level:
            self.class_level_snapshot = str(self.student.class_level.class_level)

        # 2. DYNAMIC GRADING ENGINE (Calculates exactly once upon saving)
        # Check if the student's class actually has a grading system assigned
        if self.score is not None and self.student and self.student.class_level and getattr(self.student.class_level,
                                                                                            'grading_system', None):

            # Import locally to avoid circular import issues
            from .models import GradeBoundary

            # Ask the database to find the matching rule!
            matching_boundary = GradeBoundary.objects.filter(
                grading_system=self.student.class_level.grading_system,
                min_score__lte=self.score,
                max_score__gte=self.score
            ).first()

            if matching_boundary:
                self.grade_letter_snapshot = matching_boundary.grade_name
                self.remark_snapshot = matching_boundary.remark
            else:
                self.grade_letter_snapshot = "N/A"
                self.remark_snapshot = "Score out of bounds"

        super().save(*args, **kwargs)

    # -------------------------------------------------------
    # LEGACY HELPERS (Prevents your HTML templates from breaking)
    # -------------------------------------------------------
    def get_remark(self):
        """
        Returns the dynamically calculated grade letter from the snapshot.
        This keeps {{ grade.get_remark }} working perfectly in your PDF!
        """
        return self.grade_letter_snapshot or "N/A"

    def get_comment(self):
        """
        Returns the dynamically calculated remark from the snapshot.
        This keeps {{ grade.get_comment }} working perfectly in your PDF!
        """
        return self.remark_snapshot or "No comment"

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
    headteacher_signature = models.ImageField(
        upload_to=tenant_logo_path,
        null=True,
        blank=True,
        help_text="Upload the Headteacher's signature (Transparent PNG preferred)"
    )

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


# FLEXIBLE GRADING SYSTEM FOR SCHOOLS







from django.db import models
from django.db import connection
from django.utils import timezone

# --- DYNAMIC UPLOAD PATHS ---

def news_image_path(instance, filename):
    """Saves news images to media/school_media/schema_name/news/"""
    tenant_name = connection.schema_name
    return f'school_media/{tenant_name}/news/{filename}'

def leadership_photo_path(instance, filename):
    """Saves leadership photos to media/school_media/schema_name/leadership/"""
    tenant_name = connection.schema_name
    return f'school_media/{tenant_name}/leadership/{filename}'


# --- THE CMS MODELS ---

class Announcement(models.Model):
    title = models.CharField(max_length=200, help_text="e.g., Shortlisted Candidates for 2026/2027")
    category = models.CharField(max_length=100, blank=True, help_text="e.g., General, Admissions, Alert")
    content = models.TextField(help_text="The full text of the announcement.")
    date_posted = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True, help_text="Uncheck to hide this from the homepage.")

    class Meta:
        ordering = ['-date_posted']

    def __str__(self):
        return self.title


class NewsArticle(models.Model):
    headline = models.CharField(max_length=255)
    featured_image = models.ImageField(upload_to=news_image_path, help_text="Upload an image for the news card.")
    summary = models.TextField(max_length=300, help_text="A short 2-3 line excerpt for the homepage.")
    body = models.TextField(help_text="The full news article content.")
    publish_date = models.DateField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-publish_date']
        verbose_name_plural = "News Articles"

    def __str__(self):
        return self.headline


class LeadershipProfile(models.Model):
    name = models.CharField(max_length=150, help_text="e.g., Dr. John Doe")
    role = models.CharField(max_length=150, help_text="e.g., Executive Dean: School of Education")
    photo = models.ImageField(upload_to=leadership_photo_path)
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Controls the order they appear on the site (1 comes first, then 2, etc.)"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['display_order']

    def __str__(self):
        return f"{self.name} - {self.role}"


