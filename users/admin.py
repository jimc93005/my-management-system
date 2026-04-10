from django.contrib import admin
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


class CustomUserAdmin(UserAdmin):
    model = CustomUser

    # This tells Django to take the default user fields and add our custom ones at the bottom
    fieldsets = UserAdmin.fieldsets + (
        ('School Roles', {
            'fields': ('is_teacher', 'is_hod', 'is_headteacher', 'is_deputy')
        }),
    )


# Register our custom user model with our custom admin class
admin.site.register(CustomUser, CustomUserAdmin)


