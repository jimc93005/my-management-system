import secrets
import string
from django.contrib import admin
from django.contrib import messages
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse

from .models import School, Domain, SchoolRegistrationRequest
from .models import SubscriptionPlan, PlanFeature




# 1. Create a custom Admin Site just for managing tenants
class TenantAdminSite(admin.AdminSite):
    site_header = "Three Angels Solutions Master Administration"
    site_title = "Tenant Manager"
    index_title = "Welcome to the Master Portal"


# 2. Initialize it
tenant_admin_site = TenantAdminSite(name="tenant_admin_site")

# 3. Register your models to THIS custom site
tenant_admin_site.register(School)
tenant_admin_site.register(Domain)


# 4. The Magic Registration Dashboard
@admin.register(SchoolRegistrationRequest, site=tenant_admin_site)
class SchoolRegistrationRequestAdmin(admin.ModelAdmin):
    # Added 'admin_actions' column to the list display
    list_display = ['school_name', 'subdomain', 'email', 'status', 'applied_at', 'admin_actions']
    list_filter = ['status', 'applied_at']
    search_fields = ['school_name', 'email', 'subdomain']
    readonly_fields = ['applied_at', 'reviewed_at']

    # Organize the admin form layout
    fieldsets = (
        ('Application Details', {
            'fields': ('school_name', 'subdomain', 'email', 'phone_number')
        }),
        ('Payment Verification', {
            'fields': ('proof_of_payment',)
        }),
        ('Admin Action', {
            'fields': ('status', 'admin_notes', 'reviewed_at', 'applied_at')
        }),
    )

    def admin_actions(self, obj):
        """
        Renders custom Approve and Reject buttons directly in the dashboard row.
        Clicking these routes through views.approve_registration/reject_registration,
        which provisions the schema and fires the emails automatically!
        """
        if obj.status == 'Pending':
            approve_url = reverse('schools_manager:approve_registration', args=[obj.pk])
            reject_url = reverse('schools_manager:reject_registration', args=[obj.pk])

            return format_html(
                '<a class="button" style="background-color: #10b981; color: white; padding: 4px 10px; border-radius: 4px; text-decoration: none; font-weight: bold; margin-right: 4px;" href="{}">Approve</a>'
                '<a class="button" style="background-color: #ef4444; color: white; padding: 4px 10px; border-radius: 4px; text-decoration: none; font-weight: bold;" href="{}">Reject</a>',
                approve_url, reject_url
            )

        return f"Processed ({obj.status})"

    admin_actions.short_description = "Actions"



    # ... inside your ModelAdmin class ...

    def provision_new_tenant(self, request, obj):
        """
        The Magic Automation: Creates Schema, Domain, and Admin User
        """
        # Set your base domain here. For local testing, use 'localhost'.
        BASE_DOMAIN = 'threeangels.cloud'
        PORT = '8000'

        try:
            # 1. Create the Isolated Tenant (School)
            tenant = School(
                schema_name=obj.subdomain.lower(),
                name=obj.school_name,
            )
            tenant.save()

            # 2. Link the Subdomain
            domain_url = f"{obj.subdomain.lower()}.{BASE_DOMAIN}"
            domain = Domain(
                domain=domain_url,
                tenant=tenant,
                is_primary=True
            )
            domain.save()

            # 3. Generate a secure temporary password (matching the view function)
            safe_symbols = "!@#$%^*_+-"
            alphabet = string.ascii_letters + string.digits + safe_symbols
            temp_password = ''.join(secrets.choice(alphabet) for _ in range(12))

            # 4. Create the Admin User INSIDE the new isolated schema
            with schema_context(tenant.schema_name):
                User = get_user_model()

                # Create the superuser for this specific school
                User.objects.create_superuser(
                    username=f"admin_{obj.subdomain.lower()}",
                    email=obj.email,
                    password=temp_password,
                )

            # Success Message for you in the dashboard
            messages.success(
                request,
                f"✅ MAGIC SUCCESS: Tenant '{obj.school_name}' created at {domain_url}. "
                f"Admin account created (Username: admin_{obj.subdomain.lower()} | Password: {temp_password})."
            )
            return True

        except Exception as e:
            messages.error(request, f"❌ FAILED to create tenant: {str(e)}")
            return False






class PlanFeatureInline(admin.TabularInline):
    model = PlanFeature
    extra = 3  # Gives you 3 empty rows to add features quickly


@admin.register(SubscriptionPlan, site=tenant_admin_site)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'monthly_price', 'annual_price', 'is_active', 'is_highlighted')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [PlanFeatureInline]



from django.contrib import admin
from .models import (
    LandingPageConfig, Feature,
    FAQ, NewsletterSubscriber, CompanyProfile, TeamMember, MediaShowcase
)
# Assuming you already have your tenant_admin_site defined at the top of this file:
# tenant_admin_site = AdminSite(name='tenant_admin')

# --- 1. SINGLETON ADMINS (For Master Config & Company Profile) ---
class SingletonModelAdmin(admin.ModelAdmin):
    """Prevents the admin from adding more than one configuration record."""
    def has_add_permission(self, request):
        if self.model.objects.exists():
            return False
        return super().has_add_permission(request)

@admin.register(LandingPageConfig, site=tenant_admin_site)
class LandingPageConfigAdmin(SingletonModelAdmin):
    list_display = ('site_name', 'hero_title')
    fieldsets = (
        ('Global Brand', {'fields': ('site_name', 'primary_color')}),
        ('Hero Section', {'fields': ('hero_title', 'hero_subtitle', 'hero_image')}),
        ('Calls to Action', {'fields': ('primary_cta_text', 'primary_cta_link', 'secondary_cta_text', 'secondary_cta_link')}),
    )

@admin.register(CompanyProfile, site=tenant_admin_site)
class CompanyProfileAdmin(SingletonModelAdmin):
    list_display = ('headline',)

@admin.register(Feature, site=tenant_admin_site)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ('title', 'icon_class', 'display_order', 'is_active')
    list_editable = ('display_order', 'is_active')
    ordering = ('display_order',)

@admin.register(FAQ, site=tenant_admin_site)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'display_order', 'is_active')
    list_editable = ('display_order', 'is_active')
    ordering = ('display_order',)

@admin.register(TeamMember, site=tenant_admin_site)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'display_order', 'is_active')
    list_editable = ('display_order', 'is_active')
    list_filter = ('is_active',)
    ordering = ('display_order',)

@admin.register(MediaShowcase, site=tenant_admin_site)
class MediaShowcaseAdmin(admin.ModelAdmin):
    list_display = ('title', 'media_type', 'allow_download', 'display_order', 'is_active')
    list_editable = ('display_order', 'is_active', 'allow_download')
    list_filter = ('media_type', 'is_active')
    ordering = ('display_order',)

@admin.register(NewsletterSubscriber, site=tenant_admin_site)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'subscribed_at', 'is_active')
    list_filter = ('is_active', 'subscribed_at')
    search_fields = ('email',)
    readonly_fields = ('subscribed_at',)





from .models import FooterConfig, FooterLink

@admin.register(FooterConfig, site=tenant_admin_site)
class FooterConfigAdmin(SingletonModelAdmin):
    fieldsets = (
        ('Branding & Bio', {
            'fields': ('company_bio',)
        }),
        ('Contact Information', {
            'fields': ('contact_email', 'contact_phone', 'contact_location')
        }),
        ('System Status', {
            'fields': ('db_is_operational', 'engine_version')
        }),
        ('Bottom Bar', {
            'fields': ('copyright_text',)
        }),
    )

@admin.register(FooterLink, site=tenant_admin_site)
class FooterLinkAdmin(admin.ModelAdmin):
    list_display = ('title', 'link_type', 'url', 'display_order', 'is_active')
    list_editable = ('display_order', 'is_active')
    list_filter = ('link_type', 'is_active')
    ordering = ('link_type', 'display_order')