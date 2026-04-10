from django import forms
from .models import Students
from .models import Subject
from .models import SchoolProfile
from .models import Department
from .models import SubDepartment
from .models import SubDepartmentRole
from .models import Teacher
from django.contrib.auth import get_user_model


class StudentForm(forms.ModelForm):
    subject = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = Students
        fields = [
            'first_name',
            'surname',
            'age',
            'student_id',
            'class_level',
            'address',
            'gender',
            'disability',
            'parental_contact',
            'year_enrolled',
            'orphanhood',
            'class_teachers_comment',
            'Headteachers_comment',
            'subject',
        ]

        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'surname': forms.TextInput(attrs={'class': 'form-control'}),
            'age': forms.TextInput(attrs={'class': 'form-control'}),
            'student_id': forms.TextInput(attrs={'class': 'form-control'}),
            'class_level': forms.Select(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'disability': forms.TextInput(attrs={'class': 'form-control'}),
            'parental_contact': forms.TextInput(attrs={'class': 'form-control'}),
            'year_enrolled': forms.Select(attrs={'class': 'form-control'}),
            'orphanhood': forms.Select(attrs={'class': 'form-control'}),
            'class_teachers_comment': forms.TextInput(attrs={'class': 'form-control'}),
            'Headteachers_comment': forms.TextInput(attrs={'class': 'form-control'}),
            'subjects': forms.CheckboxSelectMultiple(attrs={'class': 'form-control'})
        }


from django import forms
from .models import Subject # Make sure this matches your actual import

class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = [
            'name',
            'code',
            'target_class',     # NEW: Added target class
            'departments',
            'teacher_subject',  # NEW: Added the secure teacher dropdown
            'subject_teacher'   # Kept your old field just in case!
        ]

        widgets = {
            'name': forms.Select(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'target_class': forms.Select(attrs={'class': 'form-control'}),     # NEW
            'departments': forms.Select(attrs={'class': 'form-control'}),
            'teacher_subject': forms.Select(attrs={'class': 'form-control'}),  # NEW
            'subject_teacher': forms.TextInput(attrs={'class': 'form-control'}),
        }

# SCHOOL REPORT FORMS

class SchoolProfileForm(forms.ModelForm):
    class Meta:
        model = SchoolProfile
        fields = [
            'name',
            'motto',
            'contact',
            'email',
            'headteacher_name',
            'logo',
        ]


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'description']

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Department name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional description'
            }),
        }


class SubDepartmentForm(forms.ModelForm):
    class Meta:
        model = SubDepartment
        fields = ['name', 'description']

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Sub-department name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional description'
            }),
        }


class SubDepartmentRoleForm(forms.ModelForm):
    class Meta:
        model = SubDepartmentRole
        fields = [
            'role',
            'teacher',
        ]


class TeacherForm(forms.ModelForm):
    class Meta:
        model = Teacher
        fields =[
            'first_name',
            'last_name',
            'employment_number',
            'gender',
            'subject',
            'class_level'

        ]




# Fetch your custom User model
User = get_user_model()

class TeacherRegistrationForm(forms.ModelForm):
    # We add a custom password field so it shows up as hidden dots (***) when typing
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Create a secure password'}))

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']