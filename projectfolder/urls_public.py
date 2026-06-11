from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView, TemplateView

# Import the custom admin site we just built
from schools_manager.admin import tenant_admin_site

urlpatterns = [
    # The normal admin (You can keep this or remove it for the public schema)
    path('', TemplateView.as_view(template_name='landing.html'), name='public_landing'),
    path('admin/', admin.site.urls),

    # 👇 THE SECRET LANDLORD ADMIN 👇
    path('admin_tenants/', tenant_admin_site.urls),
    path('lobby-auth/', include(([
        # When the Lobby looks for 'users:login' after a logout,
        # it hits this line and redirects you cleanly to the home page (/).
        path('login/', RedirectView.as_view(url='/', permanent=False), name='login'),
    ], 'users'))),

    # You can also include your public landing page here later!
    # path('', include('public_app.urls')),
]