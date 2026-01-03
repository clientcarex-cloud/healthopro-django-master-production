from django.db import models

from healtho_pro_user.models.users_models import HealthOProUser


# Create your models here.

class HealthOProSuperAdmin(models.Model):
    user = models.OneToOneField(HealthOProUser, on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)
    is_owner = models.BooleanField(default=False)
    permissions = models.ManyToManyField('HealthOProSuperAdminPermissions', blank=True)
    added_on = models.DateTimeField(auto_now_add=True)


class HealthOProSuperAdminPermissions(models.Model):
    name = models.CharField(max_length=300)
    display_name = models.CharField(max_length=300)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.display_name

