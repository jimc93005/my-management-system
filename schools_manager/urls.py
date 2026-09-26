# schools_manager/urls.py

from django.urls import path
from . import views

app_name = 'schools_manager'

urlpatterns = [
    # Public Registration URLs
    path('register/', views.register_school_view, name='register'),

    path('register/success/', views.registration_success, name='registration_success'),
    path('landing_view', views.public_landing_page, name='public_landing'),

    # Admin Action URLs (These will be triggered from your admin dashboard)
    path('admin/approve/<int:pk>/', views.approve_registration, name='approve_registration'),
    path('admin/reject/<int:pk>/', views.reject_registration, name='reject_registration'),
    path('apply/', views.register_school_view, name='register_school'),
    path('pricing/', views.pricing_view, name='pricing'),
    path('faq/', views.faq_page, name='faq'),
    path('about/', views.about_page, name='about'),
    path('team/', views.team_page, name='team'),
    path('payment-methods/', views.payment_methods_page, name='payment_methods'),
    path('schools_manager/newslettersubscriber/send-announcement/', views.send_newsletter_announcement, name='send_newsletter_announcement'),
    path('unsubscribe/<uuid:token>/', views.unsubscribe_newsletter, name='unsubscribe_newsletter',),

    # RENEWAL OF SUBSCRIPTIONS URLS
    path('renewals/<int:pk>/approve/', views.approve_renewal, name='approve_renewal'),
    path('renewals/<int:pk>/reject/', views.reject_renewal, name='reject_renewal'),
    path('subscription-expired/', views.subscription_expired_view, name='subscription_expired'),

]