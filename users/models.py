
from django.db import models
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    # We use boolean fields to easily check a user's role
    is_teacher = models.BooleanField(default=False)
    is_hod = models.BooleanField(default=False)
    is_headteacher = models.BooleanField(default=False)
    is_deputy = models.BooleanField(default=False)
    # Ensure it points to students_app.SubjectDepartment
    department = models.ForeignKey(
        'students_app.SubjectDepartment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hod_staff'
    )
    # Add these to your User / Teacher model
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
    ]

    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    district_of_origin = models.CharField(max_length=100, blank=True, null=True)
    religion = models.CharField(max_length=100, blank=True, null=True)
    employment_number = models.CharField(max_length=50, blank=True, null=True, unique=True,
                                         help_text="Official Government/School ID")

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    def get_role_display(self):
        # We check the highest ranks at the top!
        if self.is_headteacher: return "Headteacher"
        if self.is_deputy: return "Deputy"
        if self.is_hod: return "HOD"
        if self.is_teacher: return "Teacher"

        # If all boxes are empty:
        return "Admin/Other"