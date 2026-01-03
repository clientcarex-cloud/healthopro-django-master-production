from django.db import models
from pro_laboratory.models.global_models import LabStaff
from pro_universal_data.models import UserPermissions


class UserPermissionsAccess(models.Model):
    permissions = models.ManyToManyField(UserPermissions, blank=True)
    lab_staff = models.OneToOneField(LabStaff, on_delete=models.PROTECT)
    is_access = models.BooleanField(default=True)
    number = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

