# schools_manager/urls.py

from django.urls import path
from . import views

app_name = 'schools_manager'

urlpatterns = [
    # Public Registration URLs
    path('register/', views.register_school_view, name='register'),

    path('register/success/', views.registration_success, name='registration_success'),


    # Admin Action URLs (These will be triggered from your admin dashboard)
    path('admin/approve/<int:pk>/', views.approve_registration, name='approve_registration'),
    path('admin/reject/<int:pk>/', views.reject_registration, name='reject_registration'),
    path('pricing/', views.pricing_view, name='pricing'),
    path('landing_view', views.public_landing_page, name='public_landing')
]