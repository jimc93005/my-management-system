from django.db import connection
from .models import Footer  # Using 'Footer' based on your error log!


def school_footer_context(request):
    """
    Injects footer settings into the template context,
    but safely ignores the public schema to prevent database crashes.
    """
    # 1. Check if we are on the main public website
    if connection.schema_name == 'public':
        return {'footer_data': None}

    # 2. If we are on a tenant schema, it is safe to query the database!
    try:
        # Note: Add .prefetch_related('documents') if you added the Legal Documents model
        profile = Footer.objects.first()
        return {'school_profile_data': profile}
    except Exception:
        # Fallback just in case the table is completely missing
        return {'footer_data': None}