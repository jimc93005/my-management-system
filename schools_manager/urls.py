# schools_manager/urls.py

from django.urls import path
from . import views

app_name = 'schools_manager'

urlpatterns = [
    # Public Registration URLs
    path('register/', views.register_school_view, name='register'),

    path('register/success/', views.registration_success, name='registration_success'),
    path('preview-email/', views.preview_approved_email, name='preview_email'),

    # Admin Action URLs (These will be triggered from your admin dashboard)
    path('admin/approve/<int:pk>/', views.approve_registration, name='approve_registration'),
    path('admin/reject/<int:pk>/', views.reject_registration, name='reject_registration'),
    path('pricing/', views.pricing_view, name='pricing')
]