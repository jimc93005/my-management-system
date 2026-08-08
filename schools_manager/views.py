
# schools_manager/views.py

import secrets
import string
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth import get_user_model
from django_tenants.utils import tenant_context
from .models import SubscriptionPlan

from .models import SchoolRegistrationRequest, School, Domain
from .forms import SchoolRegistrationForm  # We will build this in step 3 or use ModelForm
from .emails import (
    send_pending_registration_email,
    send_approved_registration_email,
    send_rejected_registration_email
)

User = get_user_model()


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
    Admin-only view: Provisions schema, creates tenant admin, creates domain, and emails credentials.
    """
    with transaction.atomic():
        registration = get_object_or_404(
            SchoolRegistrationRequest.objects.select_for_update(), pk=pk
        )

        if registration.status == 'Approved':
            messages.warning(request, "This application has already been approved.")
            # Updated to tenant_admin_site to prevent NoReverseMatch
            return redirect('tenant_admin_site:schools_manager_schoolregistrationrequest_changelist')

        try:
            # 1. Create the Tenant Schema
            tenant = School.objects.create(
                schema_name=registration.subdomain.lower(),
                name=registration.school_name,
            )

            # 2. Create the Tenant Domain
            main_domain = "localhost"
            full_domain = f"{registration.subdomain.lower()}.{main_domain}"

            Domain.objects.create(
                domain=full_domain,
                tenant=tenant,
                is_primary=True
            )

            # 3. Generate a secure temporary password
            # Safe symbols to avoid HTML entity escaping issues in text/email views
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

    # 6. Send Approval Email (Outside try/except block as requested)
    domain_url = f"http://{full_domain}:8000"

    # If this fails, Django will throw a direct Exception traceback on your screen
    send_approved_registration_email(registration, domain_url, temp_password)

    messages.success(
        request,
        f"Tenant {tenant.name} provisioned successfully! Credentials emailed to {registration.email}."
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

def preview_approved_email(request):
    """
    Temporary view to preview the email template in the browser.
    """
    context = {
        'school_name': 'Sample Academy',
        'domain_url': 'https://sample.threeangels.com',
        'email': 'admin@sample.com',
        'temp_password': 'PassWord123!',
    }
    return render(request, 'emails/registration_approved.html', context)