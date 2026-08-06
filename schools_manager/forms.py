from django import forms
from .models import SchoolRegistrationRequest
import re


class SchoolRegistrationForm(forms.ModelForm):
    class Meta:
        model = SchoolRegistrationRequest
        fields = ['school_name', 'subdomain', 'email', 'phone_number', 'proof_of_payment']

        widgets = {
            'school_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter official school name'
            }),
            'subdomain': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., greenwood (no spaces or special characters)'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'admin@school.com'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+2658834561198'
            }),
            'proof_of_payment': forms.FileInput(attrs={
                'class': 'form-control-file'
            }),
        }

    def clean_subdomain(self):
        subdomain = self.cleaned_data.get('subdomain').lower()
        # Ensure the subdomain only contains letters, numbers, and hyphens
        if not re.match(r'^[a-z0-9]+$', subdomain):
            raise forms.ValidationError("Subdomain can only contain lowercase letters, numbers, and hyphens.")

        # Reserved subdomains we don't want people taking
        if subdomain in ['www', 'admin', 'api', 'public', 'test']:
            raise forms.ValidationError("This subdomain is reserved.")

        return subdomain