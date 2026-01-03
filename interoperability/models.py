from django.db import models

from healtho_pro_user.models.users_models import Client


# Create your models here.
class LabTpaType(models.Model):
    name = models.CharField(max_length=30)
    # type = models.CharField(max_length=30)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}"


class LabTpaSecretKeys(models.Model):
    client = models.ForeignKey(Client, on_delete=models.PROTECT)
    lab_tpa_type = models.ForeignKey(LabTpaType, on_delete=models.PROTECT)
    secret_key = models.CharField(max_length=100, unique=True, blank=True, null=True)
    mac_uid = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=False)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.client}- {self.lab_tpa_type}"
