from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView, TemplateView
from schools_manager.views import register_school_view

# Import the custom admin site we just built
from schools_manager.admin import tenant_admin_site
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView, RedirectView
from django.views.static import serve

# Import your custom views here if needed
# from schools_manager.views import register_school_view, tenant_admin_site

urlpatterns = [
    # The normal admin (You can keep this or remove it for the public schema)
    path('', TemplateView.as_view(template_name='landing.html'), name='public_landing'),
    path('admin/', admin.site.urls),

    # THE SECRET LANDLORD ADMIN
    path('admin_tenants/', tenant_admin_site.urls),
    path('lobby-auth/', include([
        path('login/', RedirectView.as_view(url='/', permanent=False), name='login'),
    ])),

    path('apply/', register_school_view, name='register_school'),
    path('schools/', include('schools_manager.urls')),

    # You can also include your public landing page here later!
    # path('', include('public_app.urls')),
]

# Serve media files in development (DEBUG=True) and production (DEBUG=False)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]