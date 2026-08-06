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