from django import forms
from django.forms import inlineformset_factory
from .models import TimetableSettings, TimetableBreak

DAY_CHOICES = [
    (0, 'Monday'),
    (1, 'Tuesday'),
    (2, 'Wednesday'),
    (3, 'Thursday'),
    (4, 'Friday'),
    (5, 'Saturday'),
    (6, 'Sunday'),
]

class TimetableSettingsForm(forms.ModelForm):
    working_days = forms.MultipleChoiceField(
        choices=DAY_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        help_text="Select teaching days."
    )

    class Meta:
        model = TimetableSettings
        fields = [
            'name',
            'start_time',
            'period_duration',
            'periods_per_day',
            'working_days',
            'default_max_teacher_periods_per_day',
            'default_max_consecutive_periods',
            'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'period_duration': forms.NumberInput(attrs={'class': 'form-control', 'min': 20, 'max': 120}),
            'periods_per_day': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 20}),
            'default_max_teacher_periods_per_day': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 20}),
            'default_max_consecutive_periods': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_working_days(self):
        """Converts string choices from checkboxes back to a list of integers for JSONField storage."""
        days = self.cleaned_data.get('working_days', [])
        return [int(day) for day in days]


TimetableBreakFormSet = inlineformset_factory(
    TimetableSettings,
    TimetableBreak,
    fields=['name', 'after_period', 'duration'],
    extra=1,
    can_delete=True,
    widgets={
        'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Tea Break'}),
        'after_period': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Period #'}),
        'duration': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Minutes'}),
    }
)

from .models import BlockedSlot
BlockedSlotFormSet = inlineformset_factory(
    TimetableSettings,
    BlockedSlot,
    fields=['day', 'period_number', 'label'],
    extra=1,
    can_delete=True,
    widgets={
        'day': forms.Select(attrs={'class': 'form-select form-select-sm'}),
        'period_number': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Period #'}),
        'label': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'e.g., Clubs, Assembly'}),
    }
)




from .models import TimetableRoom

# ... (keep your existing forms)

class TimetableRoomForm(forms.ModelForm):
    class Meta:
        model = TimetableRoom
        fields = ['name', 'code', 'room_type', 'building', 'capacity', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Science Laboratory 1'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., LAB-1'}),
            'room_type': forms.Select(attrs={'class': 'form-select'}),
            'building': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Main Block'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'placeholder': 'e.g., 40'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }



from .models import SubjectConstraint, SubjectRoomRequirement

# ... (keep your existing settings and room forms)

class SubjectConstraintForm(forms.ModelForm):
    class Meta:
        model = SubjectConstraint
        fields = ['periods_per_week', 'allow_double_periods', 'double_periods_per_week']
        widgets = {
            'periods_per_week': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': 1, 'max': 30}),
            'allow_double_periods': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'double_periods_per_week': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': 0, 'max': 10}),
        }

class SubjectRoomRequirementForm(forms.ModelForm):
    class Meta:
        model = SubjectRoomRequirement
        fields = ['required_room_type', 'specific_room']
        widgets = {
            'required_room_type': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'specific_room': forms.Select(attrs={'class': 'form-select form-select-sm'}),
        }





from .models import TeacherUnavailability

class TeacherUnavailabilityForm(forms.ModelForm):
    class Meta:
        model = TeacherUnavailability
        fields = ['teacher', 'day', 'period_number', 'reason']
        widgets = {
            'teacher': forms.Select(attrs={'class': 'form-select'}),
            'day': forms.Select(attrs={'class': 'form-select'}),
            'period_number': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Leave blank for entire day'}),
            'reason': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Part-time off, Admin Day'}),
        }