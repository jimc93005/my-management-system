from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

# Import the custom admin site we just built
from schools_manager.admin import tenant_admin_site

urlpatterns = [
    # The normal admin (You can keep this or remove it for the public schema)
    path('', RedirectView.as_view(url='/admin_tenants/', permanent=False)),
    path('admin/', admin.site.urls),

    # 👇 THE SECRET LANDLORD ADMIN 👇
    path('admin_tenants/', tenant_admin_site.urls),

    # You can also include your public landing page here later!
    # path('', include('public_app.urls')),
]