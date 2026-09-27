
# schools_manager/views.py

import secrets
import string
from django.utils import timezone
from .models import PromoBlock
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth import get_user_model
from django_tenants.utils import tenant_context
from .models import SubscriptionPlan, PaymentMethod, NewsletterAsset
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from email.mime.image import MIMEImage
import mimetypes
from .models import SchoolRegistrationRequest, School, Domain
from .forms import SchoolRegistrationForm  # We will build this in step 3 or use ModelForm
from .emails import (
    send_pending_registration_email,
    send_approved_registration_email,
    send_rejected_registration_email
)
from .models import HeroBanner

from .emails import (

    send_renewal_submitted_admin_email,
    send_renewal_approved_email,
    send_renewal_rejected_email
)

User = get_user_model()



from datetime import timedelta

def get_subscription_end_date(start_from, billing_cycle):
    """
    Calculates the expiration timestamp based on the selected cycle.
    If the school is already active, start_from is their existing end date;
    otherwise, it starts from timezone.now().
    """
    if billing_cycle == 'monthly':
        return start_from + timedelta(days=30)
    elif billing_cycle == 'quarterly':
        return start_from + timedelta(days=90)
    elif billing_cycle == 'four_months':
        return start_from + timedelta(days=120)
    elif billing_cycle == 'annual':
        return start_from + timedelta(days=365)
    return start_from + timedelta(days=30)


# Make sure you have this import at the top of your views.py!
# from .models import SubscriptionPlan

def register_school_view(request):
    if request.method == 'POST':
        form = SchoolRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            registration = form.save(commit=False)
            registration.status = 'Pending'
            registration.save()

            # Trigger immediate receipt confirmation email
            send_pending_registration_email(registration)

            messages.success(request,
                             "Success! Your application and payment proof have been received. Our team will review this and send your login credentials to your email within 24 hours.")
            return redirect('schools_manager:registration_success')
    else:
        # NEW LOGIC: Check the URL for pricing plan selections
        initial_data = {}

        # 1. Get the 'plan' slug from the URL (e.g., ?plan=premium)
        plan_slug = request.GET.get('plan')
        if plan_slug:
            try:
                plan = SubscriptionPlan.objects.get(slug=plan_slug)
                initial_data['selected_plan'] = plan
            except SubscriptionPlan.DoesNotExist:
                pass  # If they manually type a fake plan in the URL, just ignore it

        # 2. Get the 'cycle' from the URL (e.g., ?cycle=annual)
        cycle = request.GET.get('cycle')
        if cycle in ['monthly', 'annual']:
            initial_data['billing_cycle'] = cycle

        # 3. Initialize the form with the caught data
        form = SchoolRegistrationForm(initial=initial_data)

    return render(request, 'schools_manager/register_school.html', {'form': form})




def registration_success(request):
    """
    Public confirmation page after submitting registration.
    """
    return render(request, 'schools_manager/registration_success.html')

from django.db import transaction


from django.db import transaction


@staff_member_required
def approve_registration(request, pk):
    """
    Admin-only view: Provisions schema, calculates initial subscription duration,
    creates tenant admin, creates domain, and emails credentials.
    """
    with transaction.atomic():
        registration = get_object_or_404(
            SchoolRegistrationRequest.objects.select_for_update(), pk=pk
        )

        if registration.status == 'Approved':
            messages.warning(request, "This application has already been approved.")
            return redirect('tenant_admin_site:schools_manager_schoolregistrationrequest_changelist')

        try:
            # Calculate initial subscription expiration
            now = timezone.now()
            initial_end_date = get_subscription_end_date(now, registration.billing_cycle)

            # 1. Create the Tenant Schema with Subscription Details
            tenant = School.objects.create(
                schema_name=registration.subdomain.lower(),
                name=registration.school_name,
                current_plan=registration.selected_plan,
                subscription_end_date=initial_end_date,
                status='Active'
            )

            # 2. Create the Tenant Domain
            main_domain = "threeangels.cloud"
            full_domain = f"{registration.subdomain.lower()}.{main_domain}"

            Domain.objects.create(
                domain=full_domain,
                tenant=tenant,
                is_primary=True
            )

            # 3. Generate a secure temporary password
            safe_symbols = "!@#$%^*_+-"
            alphabet = string.ascii_letters + string.digits + safe_symbols
            temp_password = ''.join(secrets.choice(alphabet) for _ in range(12))

            # 4. Create Initial Admin User INSIDE Tenant Schema Context
            with tenant_context(tenant):
                User.objects.create_superuser(
                    email=registration.email,
                    username=f"admin_{registration.subdomain.lower()}",
                    password=temp_password,
                    first_name="School",
                    last_name="Administrator"
                )

            # 5. Update Registration Record State
            registration.status = 'Approved'
            registration.reviewed_at = timezone.now()
            registration.save()

        except Exception as e:
            messages.error(request, f"Provisioning failed: {e}")
            return redirect('tenant_admin_site:schools_manager_schoolregistrationrequest_changelist')

    # 6. Send Approval Email
    domain_url = f"http://{full_domain}"
    send_approved_registration_email(registration, domain_url, temp_password)

    messages.success(
        request,
        f"Tenant {tenant.name} provisioned successfully until {tenant.subscription_end_date.strftime('%d %B %Y')}! Credentials emailed to {registration.email}."
    )

    return redirect('tenant_admin_site:schools_manager_schoolregistrationrequest_changelist')



@staff_member_required
def reject_registration(request, pk):
    registration = get_object_or_404(SchoolRegistrationRequest, pk=pk)

    if request.method == 'POST':
        admin_notes = request.POST.get('admin_notes', '')
        registration.status = 'Rejected'
        registration.admin_notes = admin_notes
        registration.reviewed_at = timezone.now()
        registration.save()

        # Delete the uploaded file from disk now that it's no longer needed
        if registration.proof_of_payment:
            registration.proof_of_payment.delete(save=False)

        send_rejected_registration_email(registration)

        messages.info(request, f"Application for {registration.school_name} was rejected.")
        return redirect('tenant_admin_site:schools_manager_schoolregistrationrequest_changelist')

    return render(request, 'emails/reject_confirm.html', {'registration': registration})


# PRICING VIEW
def pricing_view(request):
    # Fetch only active plans and prefetch features to speed up database queries
    plans = SubscriptionPlan.objects.filter(is_active=True).prefetch_related('features')

    return render(request, 'schools_manager/pricing.html', {'plans': plans})

# schools_manager/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .models import (
    LandingPageConfig, Feature, FAQ, CompanyProfile,
    TeamMember, MediaShowcase, NewsletterSubscriber,
    FooterConfig, FooterLink  # <-- Added new imports
)
from schools_manager.models import School


def public_landing_page(request):
    # 1. Handle Newsletter Submissions
    if request.method == 'POST' and 'newsletter_email' in request.POST:
        email = request.POST.get('newsletter_email', '').strip()
        if email:
            try:
                validate_email(email)
                NewsletterSubscriber.objects.get_or_create(email=email)
                messages.success(request, "Thank you for subscribing to our updates!")
            except ValidationError:
                messages.error(request, "Please enter a valid email address.")
        return redirect('public_landing')

    # 2. Fetch CMS Singletons
    config = LandingPageConfig.objects.first()
    company = CompanyProfile.objects.first()

    # 3. Fetch Active List Data
    features = Feature.objects.filter(is_active=True).order_by('display_order')
    # faqs = FAQ.objects.filter(is_active=True).order_by('display_order')
    # team = TeamMember.objects.filter(is_active=True).order_by('display_order')
    media = MediaShowcase.objects.filter(is_active=True).order_by('display_order')
    hero_banners = HeroBanner.objects.filter(is_active=True)

    # <-- Fetch and split footer links by their category
    # legal_links = FooterLink.objects.filter(is_active=True, link_type='legal').order_by('display_order')
    # social_links = FooterLink.objects.filter(is_active=True, link_type='social').order_by('display_order')

    # 4. Fetch Active Client Tenants (excluding the public schema)
    schools = School.objects.exclude(schema_name='public').prefetch_related('domains')
    now = timezone.now()

    # Fetch the latest active promotion within the valid date window
    active_promo = PromoBlock.objects.filter(
        is_active=True,
        start_time__lte=now,
        end_time__gte=now
    ).first()

    # 5. Build Context
    context = {
        'config': config,
        'company': company,
        'features': features,
        'hero_banners': hero_banners,


        'media': media,
        # 'legal_links': legal_links,  # <-- Added to context
        # 'social_links': social_links,  # <-- Added to context
        'schools': schools,
        'active_promo': active_promo,
    }

    return render(request, 'schools_manager/landing.html', context)


# schools_manager/views.py

def faq_page(request):
    faqs = FAQ.objects.filter(is_active=True)  # Meta.ordering on the model already sorts by display_order
    return render(request, 'schools_manager/faq.html', {'faqs': faqs})

# schools_manager/views.py

def about_page(request):
    company = CompanyProfile.objects.first()
    return render(request, 'schools_manager/about.html', {'company': company})

# schools_manager/views.py

def team_page(request):
    team_members = TeamMember.objects.filter(is_active=True)  # Meta.ordering already sorts by display_order
    return render(request, 'schools_manager/team.html', {'team_members': team_members})




# NEWS LETTER SUBSCRIPTION


from .models import NewsletterSubscriber



import logging
import mimetypes
from email.mime.image import MIMEImage
from django.core.mail import get_connection, EmailMessage
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required

logger = logging.getLogger(__name__)


# Ensure only authorized staff can send mass emails
@staff_member_required
def send_newsletter_announcement(request):
    # 1. Get the selected subscribers
    recipient_ids = request.session.get('newsletter_recipient_ids', [])

    recipients = NewsletterSubscriber.objects.filter(
        pk__in=recipient_ids,
        is_active=True
    )

    # 2. Redirect URL back to the subscriber list
    redirect_url = '/admin_tenants/schools_manager/newslettersubscriber/'

    if not recipients.exists():
        messages.error(request, "No valid recipients found. Please select subscribers again.")
        return redirect(redirect_url)

    # Variables for the template (Do not overwrite these in the POST block)
    assets = NewsletterAsset.objects.filter(is_active=True)
    logos = assets.filter(asset_type='logo')
    all_pictures = assets.filter(asset_type='image')
    all_documents = assets.filter(asset_type='document')

    # 3. Handle sending the emails
    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        body = request.POST.get('body', '').strip()

        logo_id = request.POST.get('logo_id')
        picture_ids = request.POST.getlist('picture_ids')
        document_ids = request.POST.getlist('document_ids')

        include_unsubscribe = (request.POST.get('include_unsubscribe') == 'yes')

        if not subject or not body:
            messages.error(request, "Both a subject and message are required.")
        else:
            # Rename variables to avoid shadowing the template context
            selected_logo = NewsletterAsset.objects.filter(pk=logo_id, asset_type='logo', is_active=True).first() if logo_id else None
            selected_pictures = NewsletterAsset.objects.filter(pk__in=picture_ids, asset_type='image', is_active=True)
            selected_documents = NewsletterAsset.objects.filter(pk__in=document_ids, asset_type='document', is_active=True)

            logo_cid = f"newsletter-logo-{selected_logo.pk}" if selected_logo else None
            picture_cids = [
                {'cid': f"newsletter-picture-{pic.pk}", 'title': pic.title, 'asset': pic}
                for pic in selected_pictures
            ]

            sent_count = 0
            failed_emails = []

            # Open email connection once, with error handling so a connection
            # failure shows a friendly message instead of crashing the whole view
            try:
                connection = get_connection()
                connection.open()
            except Exception:
                logger.exception("Failed to open SMTP connection for newsletter send")
                messages.error(request, "Couldn't connect to the mail server. Please try again shortly.")
                return redirect(redirect_url)

            for subscriber in recipients:
                try:
                    unsubscribe_url = request.build_absolute_uri(
                        reverse('schools_manager:unsubscribe_newsletter', kwargs={'token': subscriber.unsubscribe_token})
                    )

                    html_message = render_to_string(
                        'emails/newsletter.html',
                        {
                            'subject': subject,
                            'body': body,
                            'logo_cid': logo_cid,
                            'picture_cids': picture_cids,
                            'unsubscribe_url': unsubscribe_url if include_unsubscribe else None,
                        }
                    )

                    email = EmailMessage(
                        subject=subject,
                        body=html_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        to=[subscriber.email],
                        connection=connection,
                    )
                    email.content_subtype = "html"

                    # Embed Logo
                    if selected_logo:
                        with selected_logo.file.open('rb') as f:
                            image = MIMEImage(f.read())
                        image.add_header('Content-ID', f'<{logo_cid}>')
                        image.add_header('Content-Disposition', 'inline', filename=selected_logo.file.name.split('/')[-1])
                        email.attach(image)

                    # Embed Pictures
                    for picture in picture_cids:
                        asset = picture['asset']
                        with asset.file.open('rb') as f:
                            image = MIMEImage(f.read())
                        image.add_header('Content-ID', f"<{picture['cid']}>")
                        image.add_header('Content-Disposition', 'inline', filename=asset.file.name.split('/')[-1])
                        email.attach(image)

                    # Attach Documents
                    for document in selected_documents:
                        filename = document.file.name.split('/')[-1]
                        with document.file.open('rb') as f:
                            file_data = f.read()

                        content_type, _ = mimetypes.guess_type(filename)
                        email.attach(filename, file_data, content_type or 'application/octet-stream')

                    email.send(fail_silently=False)
                    sent_count += 1

                except Exception:
                    logger.exception(f"Failed to send newsletter to {subscriber.email}")
                    failed_emails.append(subscriber.email)

            connection.close()

            if 'newsletter_recipient_ids' in request.session:
                del request.session['newsletter_recipient_ids']

            if failed_emails:
                messages.warning(request, f"Sent to {sent_count}. Failed for: {', '.join(failed_emails)}")
            else:
                messages.success(request, f"Successfully sent announcement to all {sent_count} subscriber(s).")

            return redirect(redirect_url)

    # 4. Render the page to type the email
    return render(
        request,
        'schools_manager/send_announcement.html',
        {
            'recipients': recipients,
            'recipient_count': recipients.count(),
            'assets': assets,
            'logos': logos,
            'pictures': all_pictures,
            'documents': all_documents,
        }
    )

# UNSUBSCRIBE EMAIL VIEW


from django.shortcuts import render, get_object_or_404


def unsubscribe_newsletter(request, token):
    subscriber = get_object_or_404(
        NewsletterSubscriber,
        unsubscribe_token=token
    )

    was_active = subscriber.is_active

    # 1. Handle the actual unsubscription via POST
    if request.method == 'POST':
        if was_active:
            subscriber.is_active = False
            subscriber.save(update_fields=['is_active'])

        return render(
            request,
            'emails/unsubscribe_success.html',
            {
                'subscriber': subscriber,
                'was_active': was_active,
            }
        )

    # 2. Handle GET requests
    if not was_active:
        # If they are already unsubscribed, just show them the success page
        return render(
            request,
            'emails/unsubscribe_success.html',
            {
                'subscriber': subscriber,
                'was_active': False,
            }
        )

    # If they are active, show a confirmation page to prevent bot-clicks
    return render(
        request,
        'emails/unsubscribe_confirm.html',
        {
            'subscriber': subscriber,
        }
    )
# MAYMENT DETAILS VIEWS

def payment_methods_page(request):
    payment_methods = PaymentMethod.objects.filter(is_active=True)
    return render(request, 'schools_manager/payment_methods.html', {'payment_methods': payment_methods})






# RENEWING THE TENNANT
from .models import SubscriptionRenewal


@staff_member_required
def approve_renewal(request, pk):
    """
    Approves an existing tenant's renewal payment proof and extends their subscription.
    """
    with transaction.atomic():
        renewal = get_object_or_404(
            SubscriptionRenewal.objects.select_for_update(),
            pk=pk
        )

        if renewal.status == 'Approved':
            messages.warning(
                request,
                "This renewal has already been approved."
            )
            return redirect(
                'tenant_admin_site:schools_manager_subscriptionrenewal_changelist'
            )

        school = renewal.school
        now = timezone.now()

        # If subscription is still active in the future, extend from that end date;
        # if expired/suspended, restart from today.
        if school.subscription_end_date and school.subscription_end_date > now:
            start_point = school.subscription_end_date
        else:
            start_point = now

        new_end_date = get_subscription_end_date(
            start_point,
            renewal.billing_cycle
        )

        # Update school status and expiration
        school.subscription_end_date = new_end_date
        school.status = 'Active'
        school.save()

        # Update renewal record status
        renewal.status = 'Approved'
        renewal.reviewed_at = now
        renewal.save()

    # --- TRIGGER EMAIL TO TENANT ADMIN ---
    send_renewal_approved_email(renewal)

    messages.success(
        request,
        f"Renewal approved! {school.name} is now active until "
        f"{new_end_date.strftime('%d %B %Y')}."
    )

    return redirect(
        'tenant_admin_site:schools_manager_subscriptionrenewal_changelist'
    )





@staff_member_required
def reject_renewal(request, pk):
    """
    Rejects a renewal payment proof submission.
    """
    renewal = get_object_or_404(SubscriptionRenewal, pk=pk)

    if request.method == 'POST':
        admin_notes = request.POST.get('admin_notes', '')

        renewal.status = 'Rejected'
        renewal.admin_notes = admin_notes
        renewal.reviewed_at = timezone.now()
        renewal.save()

        if renewal.proof_of_payment:
            renewal.proof_of_payment.delete(save=False)

        # --- TRIGGER EMAIL TO TENANT ADMIN ---
        send_renewal_rejected_email(renewal)

        messages.info(
            request,
            f"Renewal request for {renewal.school.name} was rejected."
        )

        return redirect(
            'tenant_admin_site:schools_manager_subscriptionrenewal_changelist'
        )

    return render(
        request,
        'emails/reject_renewal_confirm.html',
        {'renewal': renewal}
    )

from django_tenants.utils import schema_context
from .models import SubscriptionRenewal, PaymentMethod

def subscription_expired_view(request):
    """
    Renders the 'Account Suspended / Expired' page for tenants and handles
    proof of payment uploads for renewals.
    """
    tenant = request.tenant

    # Fetch active payment details (bank, mobile money) from the public schema
    with schema_context('public'):
        payment_methods = list(
            PaymentMethod.objects.filter(is_active=True)
        )

    if request.method == 'POST':
        billing_cycle = request.POST.get('billing_cycle')
        proof_file = request.FILES.get('proof_of_payment')

        if not billing_cycle or not proof_file:
            messages.error(
                request,
                "Please select a billing cycle and attach proof of payment."
            )
        else:
            with schema_context('public'):
                renewal = SubscriptionRenewal.objects.create(
                    school=tenant,
                    billing_cycle=billing_cycle,
                    proof_of_payment=proof_file,
                    status='Pending'
                )

                # --- TRIGGER EMAIL TO MASTER ADMIN ---
                send_renewal_submitted_admin_email(renewal)

            messages.success(
                request,
                "Renewal proof submitted successfully! "
                "Our administration team will review your payment "
                "and restore account access within 24 hours."
            )

            return redirect('/subscription-expired/')

    return render(
        request,
        'schools_manager/subscription_expired.html',
        {
            'tenant': tenant,
            'payment_methods': payment_methods,
        }
    )



# VIDEOS VIEW
from django.shortcuts import render
from django.db.models import Q
from .models import DemoVideo


def demo_hub(request):
    """Public view for landing page visitors to search and watch demo videos."""
    query = request.GET.get('q', '').strip()
    selected_category = request.GET.get('category', '').strip()

    # Fetch published videos in the order defined by the model
    videos = DemoVideo.objects.filter(is_published=True)

    # Text search across title, description, and category
    if query:
        videos = videos.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(category__icontains=query)
        )

    # Exact filter when clicking a specific category button
    if selected_category:
        videos = videos.filter(category=selected_category)

    return render(request, 'videos/demo_hub.html', {
        'videos': videos,
        'query': query,
        'selected_category': selected_category,
        'categories': DemoVideo.CATEGORY_CHOICES,  # Passes category list to template for buttons
    })

#
# from django.shortcuts import render
# from django.utils import timezone
# from .models import PromoBlock  # Adjust import path if needed
#
#
# def public_landing(request):
#     now = timezone.now()
#
#     # Fetch the latest active promotion within the valid date window
#     active_promo = PromoBlock.objects.filter(
#         is_active=True,
#         start_time__lte=now,
#         end_time__gte=now
#     ).first()
#
#     context = {
#         'active_promo': active_promo,
#         # ... your existing context variables (config, hero_banners, features, etc.) ...
#     }
#     return render(request, 'schools_manager/landing.html', context)