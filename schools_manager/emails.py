# schools_manager/emails.py

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

def send_pending_registration_email(registration):
    """
    Sent immediately when a school submits their application form.
    """
    subject = f"Registration Received - {registration.school_name}"
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@threeangels.com')
    to_email = [registration.email]

    context = {
        'school_name': registration.school_name,
        'subdomain': registration.subdomain,
        'applied_at': registration.applied_at,
    }

    # Render HTML and plain text alternatives
    html_content = render_to_string('emails/registration_pending.html', context)
    text_content = strip_tags(html_content)

    email = EmailMultiAlternatives(subject, text_content, from_email, to_email)
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)


def send_approved_registration_email(registration, full_domain_url, temp_password):
    """
    Sent when the super-admin approves the registration request.
    Includes the tenant link and temporary admin login credentials.
    """
    subject = f"Congratulations! Your Edusphere Account is Ready - {registration.school_name}"
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@threeangels.com')
    to_email = [registration.email]

    context = {
        'school_name': registration.school_name,
        'domain_url': full_domain_url,
        'email': registration.email,
        'temp_password': temp_password,
        'registration': registration
    }

    html_content = render_to_string('emails/registration_approved.html', context)
    text_content = strip_tags(html_content)

    email = EmailMultiAlternatives(subject, text_content, from_email, to_email)
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)


def send_rejected_registration_email(registration):
    """
    Sent if an admin rejects the registration.
    """
    subject = f"Update on your Edusphere Application - {registration.school_name}"
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@threeangels.com')
    to_email = [registration.email]

    context = {
        'school_name': registration.school_name,
        'admin_notes': registration.admin_notes,
    }

    html_content = render_to_string('emails/registration_rejected.html', context)
    text_content = strip_tags(html_content)

    email = EmailMultiAlternatives(subject, text_content, from_email, to_email)
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)






from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django_tenants.utils import tenant_context


def get_tenant_admin_emails(school):
    """Helper function to fetch the email of the admin user inside the tenant schema."""
    User = get_user_model()
    with tenant_context(school):
        admins = User.objects.filter(is_superuser=True).values_list('email', flat=True)
        return list(admins)


def send_html_email(subject, template_name, context, recipient_list):
    """Helper function to render HTML templates and send dual-format emails."""
    html_message = render_to_string(template_name, context)
    plain_message = strip_tags(html_message)

    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipient_list,
        html_message=html_message,
        fail_silently=True,
    )


def send_billing_warning_email(school, days_left):
    admin_emails = get_tenant_admin_emails(school)
    if admin_emails:
        send_html_email(
            subject=f"Action Required: Your School Portal Subscription Expires in {days_left} Days",
            template_name='emails/billing_warning.html',
            context={'school': school, 'days_left': days_left},
            recipient_list=admin_emails
        )


def send_suspension_email(school):
    admin_emails = get_tenant_admin_emails(school)
    if admin_emails:
        send_html_email(
            subject=f"Account Suspended: {school.name} Portal Subscription Expired",
            template_name='emails/account_suspended.html',
            context={'school': school},
            recipient_list=admin_emails
        )


def send_renewal_submitted_admin_email(renewal):
    send_html_email(
        subject=f"New Renewal Payment Uploaded: {renewal.school.name}",
        template_name='emails/renewal_submitted_admin.html',
        context={'renewal': renewal},
        recipient_list=[settings.DEFAULT_FROM_EMAIL]
    )


def send_renewal_approved_email(renewal):
    admin_emails = get_tenant_admin_emails(renewal.school)
    if admin_emails:
        send_html_email(
            subject=f"Subscription Restored: {renewal.school.name} Portal",
            template_name='emails/renewal_approved.html',
            context={'renewal': renewal},
            recipient_list=admin_emails
        )


def send_renewal_rejected_email(renewal):
    admin_emails = get_tenant_admin_emails(renewal.school)
    if admin_emails:
        send_html_email(
            subject=f"Action Required: Subscription Renewal Payment Issue - {renewal.school.name}",
            template_name='emails/renewal_rejected.html',
            context={'renewal': renewal},
            recipient_list=admin_emails
        )