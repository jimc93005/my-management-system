from django.contrib import messages
from django.shortcuts import redirect
from functools import wraps


def role_required(allowed_roles=[]):
    """
    Checks if the user belongs to one of the allowed groups.
    If not, redirects back with an error message.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper_func(request, *args, **kwargs):
            # 1. Superusers bypass all restrictions
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # 2. Check group membership
            user_groups = request.user.groups.values_list('name', flat=True)
            if any(role in user_groups for role in allowed_roles):
                return view_func(request, *args, **kwargs)

            # 3. Access Denied: Add a temporary flash message
            messages.error(request, "You do not have permission to perform this action.")

            # 4. Redirect to previous page (or home if no previous page exists)
            referer = request.META.get('HTTP_REFERER')
            if referer:
                return redirect(referer)
            return redirect('/')

        return wrapper_func

    return decorator