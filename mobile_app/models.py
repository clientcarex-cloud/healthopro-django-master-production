from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from healtho_pro_user.models.universal_models import HealthcareRegistryType
from pro_laboratory.models.patient_models import Patient


class QuickServices(models.Model):
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Quick Service"
        verbose_name_plural = "Quick Services"

    def __str__(self):
        return self.name


class MobileAppLabMenus(models.Model):
    label = models.CharField(max_length=100)
    ordering = models.PositiveIntegerField()
    icon = models.CharField(max_length=100, null=True, blank=True)
    link = models.CharField(max_length=200, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    health_care_registry_type = models.ForeignKey(HealthcareRegistryType, on_delete=models.PROTECT,
                                                  related_name='mobileapp_health_care_registry_type')

    def __str__(self):
        return self.label

    class Meta:
        ordering = ['ordering']


@receiver(pre_save, sender=MobileAppLabMenus)
def update_custom_order(sender, instance, **kwargs):
    if not instance.ordering:
        # If custom_order is not set, set it to the maximum value + 1
        max_order = MobileAppLabMenus.objects.all().aggregate(models.Max('ordering'))['ordering__max']
        instance.custom_order = max_order + 1 if max_order is not None else 1


# class HealthoAppPatientReg(models.Model):
#     patient = models.ForeignKey('pro_laboratory.Patient', on_delete=models.PROTECT)
#     user_id = models.IntegerField()
#

class Category(models.Model):
    name = models.CharField(max_length=100)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
