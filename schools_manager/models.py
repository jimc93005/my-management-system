
from django.db import models
from django_tenants.models import TenantMixin, DomainMixin

# 1. THE TENANT MODEL
class School(TenantMixin):
    name = models.CharField(max_length=100)
    created_on = models.DateField(auto_now_add=True)

    # default true, schema will be automatically created and synced when it is saved
    auto_create_schema = True
    auto_drop_schema = True # Be careful with this in production!

    def __str__(self):
        return self.name


# 2. THE DOMAIN MODEL
class Domain(DomainMixin):
    # This comes built-in from DomainMixin.
    # It automatically links the URL (like schoola.com) to the School model above!
    pass


# APPLICATION FOR DOMAIN FORMS AND MODELS


class SchoolRegistrationRequest(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    )

    school_name = models.CharField(max_length=255)
    # The subdomain will be used to automatically create their schema (e.g. 'myschool')
    subdomain = models.CharField(max_length=100, unique=True, help_text="Letters and numbers only, no spaces.")
    email = models.EmailField(help_text="We will send login details here.")
    phone_number = models.CharField(max_length=20)

    proof_of_payment = models.ImageField(upload_to='payment_proofs/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')

    admin_notes = models.TextField(blank=True, null=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.school_name} - {self.status}"