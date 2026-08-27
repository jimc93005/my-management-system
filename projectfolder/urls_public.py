from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView, RedirectView
from django.views.static import serve
from django.contrib.auth.views import LogoutView

# Custom app imports
from schools_manager.views import register_school_view
from schools_manager.admin import tenant_admin_site

urlpatterns = [
    # Public landing page
    path('', TemplateView.as_view(template_name='landing.html'), name='public_landing'),
    path('admin/', admin.site.urls),

    # 1. OVERRIDE ADMIN LOGOUT: Redirects directly to the home page ('/')
    # Must be placed BEFORE tenant_admin_site.urls
    path('admin_tenants/logout/', LogoutView.as_view(next_page='/'), name='public_admin_logout'),

    # 2. SECRET LANDLORD ADMIN
    path('admin_tenants/', tenant_admin_site.urls),

    path('lobby-auth/', include([
        path('login/', RedirectView.as_view(url='/', permanent=False), name='login'),
    ])),

    path('apply/', register_school_view, name='register_school'),
    path('schools/', include('schools_manager.urls')),
]

# Media file serving
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]