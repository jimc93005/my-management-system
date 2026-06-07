from django.contrib import admin
from .models import School, Domain

# 1. Create a custom Admin Site just for managing tenants
class TenantAdminSite(admin.AdminSite):
    site_header = "Master Landlord Administration"
    site_title = "Tenant Manager"
    index_title = "Welcome to the Master Portal"

# 2. Initialize it
tenant_admin_site = TenantAdminSite(name="tenant_admin_site")

# 3. Register your models to THIS custom site (NOT the default admin.site)
tenant_admin_site.register(School)
tenant_admin_site.register(Domain)