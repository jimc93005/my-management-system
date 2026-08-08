
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

    # Add these to SchoolRegistrationRequest
    selected_plan = models.ForeignKey(
        'SubscriptionPlan',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The plan they selected on the pricing page."
    )
    BILLING_CHOICES = (
        ('monthly', 'Monthly'),
        ('annual', 'Annually'),
    )
    billing_cycle = models.CharField(
        max_length=10,
        choices=BILLING_CHOICES,
        default='monthly'
    )

    admin_notes = models.TextField(blank=True, null=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.school_name} - {self.status}"


from django.db import models


class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100, help_text="e.g., Basic, Premium, Enterprise")
    slug = models.SlugField(unique=True, help_text="URL-friendly name (e.g., basic-plan)")
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price per month")
    annual_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price per year (usually discounted)")
    description = models.TextField(blank=True, help_text="A short summary of who this plan is for.")
    is_active = models.BooleanField(default=True, help_text="Uncheck to hide this plan from the pricing page.")

    # Optional styling field if you want to highlight a specific plan (like "Most Popular")
    is_highlighted = models.BooleanField(default=False)

    class Meta:
        ordering = ['monthly_price']

    def __str__(self):
        return self.name


class PlanFeature(models.Model):
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE, related_name='features')
    feature_text = models.CharField(max_length=255, help_text="e.g., Up to 500 Students")

    # To keep the bullet points in a specific order
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order']

    def __str__(self):
        return f"{self.plan.name} - {self.feature_text}"