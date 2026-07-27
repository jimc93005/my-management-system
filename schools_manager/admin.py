from django.contrib import admin
from django.contrib import messages
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from .models import School, Domain, SchoolRegistrationRequest
from django.utils import timezone


# 1. Create a custom Admin Site just for managing tenants
class TenantAdminSite(admin.AdminSite):
    site_header = "EduSphere Master Administration"
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
    list_display = ['school_name', 'subdomain', 'email', 'status', 'applied_at']
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

    def save_model(self, request, obj, form, change):
        # Check if this is an existing object being edited
        if change:
            old_obj = SchoolRegistrationRequest.objects.get(pk=obj.pk)

            # TRIGGER PHASE 4: If status changes from Pending -> Approved
            if old_obj.status == 'Pending' and obj.status == 'Approved':
                obj.reviewed_at = timezone.now()
                success = self.provision_new_tenant(request, obj)

                # If provisioning failed, revert the status back to Pending
                if not success:
                    obj.status = 'Pending'

        super().save_model(request, obj, form, change)

    def provision_new_tenant(self, request, obj):
        """
        The Magic Automation: Creates Schema, Domain, and Admin User
        """
        # Set your base domain here. For local testing, use 'localhost'.
        # In production, change this to 'edusphere.com'
        BASE_DOMAIN = 'localhost'

        try:
            # 1. Create the Isolated Tenant (School)
            # Because your model has auto_create_schema=True, saving this creates the PostgreSQL schema instantly.
            tenant = School(
                schema_name=obj.subdomain,
                name=obj.school_name,
            )
            tenant.save()

            # 2. Link the Subdomain
            domain_url = f"{obj.subdomain}.{BASE_DOMAIN}"
            domain = Domain(
                domain=domain_url,
                tenant=tenant,
                is_primary=True
            )
            domain.save()

            # 3. Create the Admin User INSIDE the new isolated schema
            # We use schema_context to ensure the user isn't saved to the public schema
            with schema_context(tenant.schema_name):
                User = get_user_model()

                # Generate a default password
                temp_password = f"{obj.subdomain.capitalize()}2026!"

                # Create the superuser for this specific school
                User.objects.create_superuser(
                    username=f"admin_{obj.subdomain}",
                    email=obj.email,
                    password=temp_password,
                )

            # Success Message for you in the dashboard
            messages.success(
                request,
                f"✅ MAGIC SUCCESS: Tenant '{obj.school_name}' created at {domain_url}. "
                f"Admin account created (Username: admin_{obj.subdomain} | Password: {temp_password})."
            )
            return True

        except Exception as e:
            # If anything fails (e.g., subdomain already exists), catch the error safely
            messages.error(request, f"❌ FAILED to create tenant: {str(e)}")
            return False