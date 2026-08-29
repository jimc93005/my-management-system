
from django.db import models
from django_tenants.models import TenantMixin, DomainMixin

import os
import shutil
from django.conf import settings
from django.db.models.signals import post_delete
from django.dispatch import receiver


# 1. THE TENANT MODEL
class School(TenantMixin):
    name = models.CharField(max_length=100)
    allocated_storage_mb = models.FloatField(
        default=500.0,
        help_text="Maximum storage allowed in Megabytes"
    )
    used_storage_mb = models.FloatField(default=0.0)
    created_on = models.DateField(auto_now_add=True)

    # default true, schema will be automatically created and synced when it is saved
    auto_create_schema = True
    auto_drop_schema = True # Be careful with this in production!

    def delete(self, force_drop=False, *args, **kwargs):
        """
        Overrides the default delete method to ensure media files
        are wiped when the tenant is deleted.
        """
        # 1. Grab the exact folder path BEFORE the database record is gone
        tenant_media_path = os.path.join(settings.MEDIA_ROOT, self.schema_name)

        # 2. Delete the tenant from the database (this drops the schema in django-tenants)
        super().delete(force_drop=force_drop, *args, **kwargs)

        # 3. Wipe the folder from the hard drive
        if os.path.exists(tenant_media_path) and os.path.isdir(tenant_media_path):
            shutil.rmtree(tenant_media_path)
            print(f"🗑️ SUCCESS: Wiped media folder for {self.schema_name}")

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





# AUTOMATED LANDING PAGE

from django.db import models
from django.core.exceptions import ValidationError


# 1. THE MAIN CONFIGURATION (Singleton Model)
class LandingPageConfig(models.Model):
    # Global Brand
    site_name = models.CharField(max_length=100, default="Three Angels Cloud")
    primary_color = models.CharField(max_length=7, default="#4f46e5", help_text="Hex color code (e.g., #4f46e5)")

    # Hero Section
    hero_title = models.CharField(max_length=255, default="Manage Your School with Ease")
    hero_subtitle = models.TextField(blank=True, help_text="The descriptive text under the main headline.")
    hero_image = models.ImageField(upload_to='landing_assets/', blank=True, null=True,
                                   help_text="Upload your software mockup dashboard image here.")

    # Calls to Action (CTA)
    primary_cta_text = models.CharField(max_length=50, default="Get Started")
    primary_cta_link = models.CharField(max_length=255, default="/apply/")
    secondary_cta_text = models.CharField(max_length=50, default="View Demo", blank=True)
    secondary_cta_link = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Landing Page Configuration"
        verbose_name_plural = "Landing Page Configuration"

    def __str__(self):
        return "Master Landing Page Settings"

    def save(self, *args, **kwargs):
        # This ensures we only ever have ONE settings row in the database
        if LandingPageConfig.objects.exists() and not self.pk:
            raise ValidationError("You can only have one Landing Page Configuration. Update the existing one instead.")
        self.pk = 1
        super(LandingPageConfig, self).save(*args, **kwargs)


# 2. FEATURE CARDS
class Feature(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    icon_class = models.CharField(max_length=50, default="fas fa-check-circle",
                                  help_text="FontAwesome class (e.g., fas fa-bolt)")
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['display_order']

    def __str__(self):
        return self.title



# 5. FAQs
class FAQ(models.Model):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['display_order']
        verbose_name = "FAQ"

    def __str__(self):
        return self.question


# 6. NEWSLETTER SUBSCRIBERS
class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True, help_text="Subscriber's email address")
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, help_text="Uncheck if the user unsubscribes")

    class Meta:
        ordering = ['-subscribed_at'] # Shows newest subscribers first
        verbose_name = "Newsletter Subscriber"
        verbose_name_plural = "Newsletter Subscribers"

    def __str__(self):
        return f"{self.email} - {'Active' if self.is_active else 'Unsubscribed'}"


# 7. COMPANY PROFILE (About Us - Singleton Model)
class CompanyProfile(models.Model):
    headline = models.CharField(max_length=255, default="Empowering Education Through Technology")
    mission_statement = models.TextField(blank=True, help_text="A short, powerful sentence about your core mission.")
    company_history = models.TextField(blank=True,
                                       help_text="The detailed background story of how and why the company started.")

    class Meta:
        verbose_name = "Company Profile (About Us)"
        verbose_name_plural = "Company Profile (About Us)"

    def __str__(self):
        return "Master Company Profile"

    def save(self, *args, **kwargs):
        # Ensures only ONE company profile exists
        if CompanyProfile.objects.exists() and not self.pk:
            raise ValidationError("You can only have one Company Profile. Update the existing one instead.")
        self.pk = 1
        super(CompanyProfile, self).save(*args, **kwargs)


# 8. TEAM MEMBERS (Staff & Leadership)
class TeamMember(models.Model):
    name = models.CharField(max_length=100, help_text="e.g., John Doe")
    role = models.CharField(max_length=100, help_text="e.g., Chief Executive Officer (CEO), Lead Developer")
    bio = models.TextField(blank=True, help_text="A brief 1-2 sentence description about their expertise.")
    photo = models.ImageField(upload_to='team_photos/', blank=True, null=True,
                              help_text="Upload a professional headshot.")

    # Professional Social Links
    linkedin_url = models.URLField(blank=True, null=True, help_text="Optional: Link to their LinkedIn profile")
    twitter_url = models.URLField(blank=True, null=True, help_text="Optional: Link to their X/Twitter profile")

    display_order = models.PositiveIntegerField(default=0, help_text="Lower numbers appear first (e.g., put 1 for CEO)")
    is_active = models.BooleanField(default=True, help_text="Uncheck to hide this member from the website")

    class Meta:
        ordering = ['display_order']
        verbose_name = "Team Member"
        verbose_name_plural = "Team Members"

    def __str__(self):
        return f"{self.name} - {self.role}"


# 9. MEDIA SHOWCASE (Images & Videos)
class MediaShowcase(models.Model):
    MEDIA_CHOICES = (
        ('IMAGE', 'Image'),
        ('VIDEO', 'Video'),
    )

    title = models.CharField(max_length=150, help_text="e.g., Dashboard Overview, Student Portal Walkthrough")
    media_type = models.CharField(max_length=10, choices=MEDIA_CHOICES, default='IMAGE')

    # For Image Uploads
    image = models.ImageField(upload_to='showcase_images/', blank=True, null=True,
                              help_text="Upload if Media Type is 'Image'")

    # For Video Uploads / Embeds
    video_url = models.URLField(blank=True, null=True,
                                help_text="Paste a YouTube or Vimeo link here for faster loading.")
    video_file = models.FileField(upload_to='showcase_videos/', blank=True, null=True,
                                  help_text="Or upload an MP4 file directly (Keep file size small).")

    description = models.TextField(blank=True, help_text="A brief explanation of what is happening in this media.")

    # Download permissions
    allow_download = models.BooleanField(default=False,
                                         help_text="Check this to show a 'Download' button to the public.")

    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, help_text="Uncheck to hide from the landing page")

    class Meta:
        ordering = ['display_order']
        verbose_name = "Media Showcase Item"
        verbose_name_plural = "Media Showcase Items"

    def __str__(self):
        return f"{self.title} - {self.get_media_type_display()}"

    def clean(self):
        # Basic validation to ensure the right files are provided
        if self.media_type == 'IMAGE' and not self.image:
            raise ValidationError("You must upload an image if the media type is set to 'Image'.")
        if self.media_type == 'VIDEO' and not self.video_url and not self.video_file:
            raise ValidationError(
                "You must provide either a Video URL or upload a Video File if the media type is 'Video'.")