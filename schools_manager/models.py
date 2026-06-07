
from django.db import models
from django_tenants.models import TenantMixin, DomainMixin

# 1. THE TENANT MODEL
class School(TenantMixin):
    name = models.CharField(max_length=100)
    created_on = models.DateField(auto_now_add=True)

    # default true, schema will be automatically created and synced when it is saved
    auto_create_schema = True
    auto_drop_schema = True # Be careful with this in production!

    def __str__(self):
        return self.name


# 2. THE DOMAIN MODEL
class Domain(DomainMixin):
    # This comes built-in from DomainMixin.
    # It automatically links the URL (like schoola.com) to the School model above!
    pass