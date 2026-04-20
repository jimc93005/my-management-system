from django import forms
from .models import Students
from .models import Subject
from .models import SchoolProfile
from .models import Department
from .models import SubDepartment
from .models import SubDepartmentRole
from .models import SubjectDepartment
from .models import ClassLevel
from .models import Teacher
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User, Group
from .models import MasterSubject
from .models import DepartmentEvent


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
            'status',
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




User = get_user_model()
class SubDepartmentRoleForm(forms.ModelForm):
    class Meta:
        model = SubDepartmentRole
        fields = ['role', 'teacher']

    def __init__(self, *args, **kwargs):
        super(SubDepartmentRoleForm, self).__init__(*args, **kwargs)
        # Force the dropdown to perfectly populate with staff marked as 'is_teacher'
        self.fields['teacher'].queryset = User.objects.filter(is_teacher=True).order_by('first_name')


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
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        widget=forms.CheckboxSelectMultiple,  # This forces it to render as tick-boxes!
        required=True,
        label="Assign System Roles",
        help_text="Tick all the groups this staff member belongs to."
    )

    # Custom password field so it shows up as hidden dots (***) when typing
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Create a temporary password'})
    )

    class Meta:
        model = User
        # We added the 5 new HR/Demographic fields to the end of this list!
        fields = [
            'first_name', 'last_name', 'email', 'username', 'password', 'groups',
            'employment_number', 'gender', 'phone_number', 'district_of_origin', 'religion'
        ]




class EditStaffProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'employment_number',
            'gender', 'phone_number', 'district_of_origin', 'religion'
        ]


# Make sure to import SubjectDepartment at the top of your forms.py file!
# from students_app.models import ClassLevel, SubjectDepartment

class ManageStaffRolesForm(forms.Form):
    # 1. System Groups
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="System Access Groups"
    )

    # 2. Legacy Booleans (Based on your Custom User model)
    is_teacher = forms.BooleanField(required=False, label="Is a Teacher")
    is_hod = forms.BooleanField(required=False, label="Is Head of Department")
    is_deputy = forms.BooleanField(required=False, label="Is Deputy Head")
    is_headteacher = forms.BooleanField(required=False, label="Is Headteacher")

    # 3. Form Class Assignment
    form_class = forms.ModelChoiceField(
        queryset=ClassLevel.objects.all(),
        required=False,
        empty_label="--- Not a Form Teacher ---",
        label="Assigned Form Class"
    )

    # 4. Academic Department Assignment (For HODs)
    department = forms.ModelChoiceField(
        queryset=SubjectDepartment.objects.all(),
        required=False,
        empty_label="--- Not an HOD / No Department ---",
        label="Academic Department (Science/Language/Humanities)"
    )


User = get_user_model()

class ClassLevelForm(forms.ModelForm):
    class Meta:
        model = ClassLevel
        fields = ['class_level', 'form_teacher']
        labels = {
            'class_level': 'Select Class Level',
            'form_teacher': 'Assign Form Teacher (Optional)'
        }

    def __init__(self, *args, **kwargs):
        super(ClassLevelForm, self).__init__(*args, **kwargs)
        # Only show staff who are marked as teachers in the dropdown
        self.fields['form_teacher'].queryset = User.objects.filter(is_teacher=True).order_by('first_name')


class MasterSubjectForm(forms.ModelForm):
    class Meta:
        model = MasterSubject
        fields = ['name']
        labels = {
            'name': 'Official Subject Name'
        }
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Enter new subject name (e.g., French)'})
        }


class DepartmentEventForm(forms.ModelForm):
    class Meta:
        model = DepartmentEvent
        fields = ['title', 'description', 'academic_year', 'term', 'start_date', 'end_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }