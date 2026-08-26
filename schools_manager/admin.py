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