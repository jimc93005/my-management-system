
from django.db import models
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    # We use boolean fields to easily check a user's role
    is_teacher = models.BooleanField(default=False)
    is_hod = models.BooleanField(default=False)
    is_headteacher = models.BooleanField(default=False)
    is_deputy = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    def get_role_display(self):
        if self.is_teacher: return "Teacher"
        if self.is_hod: return "HOD"
        if self.is_headteacher: return "Headteacher"
        if self.is_deputy: return "Deputy"
        return "Admin/Other"
