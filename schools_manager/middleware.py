from django.shortcuts import redirect
from django.utils import timezone
from django_tenants.utils import schema_context

class TenantSubscriptionMiddleware:
    """
    Middleware that intercepts requests to client tenant domains.
    If the tenant's subscription is expired or suspended, it redirects
    all traffic to the /subscription-expired/ page.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant = getattr(request, 'tenant', None)

        # Apply restrictions ONLY to tenant schemas (skip 'public')
        if tenant and tenant.schema_name != 'public':
            now = timezone.now()

            # Auto-suspend if current time has passed expiration
            if tenant.subscription_end_date and tenant.subscription_end_date < now and tenant.status == 'Active':
                with schema_context('public'):
                    tenant.status = 'Suspended'
                    tenant.save(update_fields=['status'])

            # If tenant is suspended, enforce URL lockout
            if tenant.status == 'Suspended':
                allowed_paths = [
                    '/subscription-expired/',
                    '/logout/',
                    '/admin/logout/',
                ]

                # Check if user is requesting an allowed page or static asset
                path = request.path
                is_allowed = (
                    any(path.startswith(p) for p in allowed_paths) or
                    path.startswith('/static/') or
                    path.startswith('/media/')
                )

                if not is_allowed:
                    return redirect('/subscription-expired/')

        return self.get_response(request)