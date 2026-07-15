
from django.db import models
from django.contrib.auth.models import AbstractUser

import os

# 1. Create the dynamic mail-sorter function
def staff_signature_path(instance, filename):
    # This creates a unique folder for every single staff member!
    # Example path: signatures/staff/collins_jim/signature.png
    return f'signatures/staff/{instance.username}/{filename}'


class CustomUser(AbstractUser):
    # We use boolean fields to easily check a user's role
    is_teacher = models.BooleanField(default=False)
    is_hod = models.BooleanField(default=False)
    is_headteacher = models.BooleanField(default=False)
    is_deputy = models.BooleanField(default=False)
    # Ensure it points to students_app.SubjectDepartment
   
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

    signature = models.ImageField(
        upload_to=staff_signature_path,
        null=True,
        blank=True,
        help_text="Upload a transparent PNG of the signature"
    )

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