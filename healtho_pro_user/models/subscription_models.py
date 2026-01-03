from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from healtho_pro_user.models.business_models import BusinessProfiles
from healtho_pro_user.models.users_models import HealthOProUser
from pro_universal_data.models import ULabMenus


class BusinessSubscriptionType(models.Model):  #Trail, Paid
    name = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class BusinessBillCalculationType(models.Model):  #Amount/Patient or Prepaid-Plan
    name = models.CharField(max_length=200, unique=True)
    subscription_type = models.ForeignKey(BusinessSubscriptionType, on_delete=models.PROTECT)
    amount_per_patient = models.DecimalField(max_digits=10, decimal_places=2)
    is_amount_percentage = models.BooleanField(default=False)
    is_default = models.BooleanField(default=True)
    is_prepaid = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name}-{self.amount_per_patient}{" - default" if self.is_default else ""}"

    def save(self, *args, **kwargs):
        if self.is_default and self.is_active:
            BusinessBillCalculationType.objects.filter(is_active=True,
                                                       subscription_type=self.subscription_type).exclude(
                pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class BusinessSubscriptionPlans(models.Model):
    name = models.CharField(max_length=200, unique=True)
    plan_description = models.CharField(max_length=2000, blank=True, null=True)
    plan_validity_in_days = models.IntegerField()
    subscription_type = models.ForeignKey(BusinessSubscriptionType, on_delete=models.PROTECT)
    calculation_type = models.ForeignKey(BusinessBillCalculationType, on_delete=models.PROTECT)
    is_default_plan = models.BooleanField(default=False)
    plan_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    grace_period = models.IntegerField(default=15)
    is_active = models.BooleanField(default=True)
    modules=models.ManyToManyField(ULabMenus, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    added_on = models.DateTimeField(auto_now_add=True)
    created_by=models.ForeignKey(HealthOProUser, on_delete=models.PROTECT, related_name='created_by')
    last_updated_by = models.ForeignKey(HealthOProUser, on_delete=models.PROTECT, related_name='last_updated_by')

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.is_default_plan and self.is_active:
            BusinessSubscriptionPlans.objects.filter(is_active=True, subscription_type=self.subscription_type).exclude(
                pk=self.pk).update(is_default_plan=False)
        super().save(*args, **kwargs)


class OverallBusinessSubscriptionStatus(models.Model):
    b_id = models.OneToOneField(BusinessProfiles, on_delete=models.PROTECT, blank=True, null=True)
    validity = models.DateTimeField(blank=True, null=True)
    account_locks_on = models.DateTimeField(blank=True, null=True)
    is_subscription_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)


class OverallBusinessSubscriptionPlansPurchased(models.Model):
    b_id = models.ForeignKey(BusinessProfiles, on_delete=models.PROTECT, blank=True, null=True)
    plan_id_at_client = models.IntegerField(blank=True, null=True)
    plan_name = models.CharField(max_length=200, blank=True, null=True)
    plan_start_date = models.DateTimeField(blank=True, null=True)
    plan_end_date = models.DateTimeField(blank=True, null=True)
    no_of_days = models.IntegerField(blank=True, null=True)
    amount_per_patient = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_amount_percentage = models.BooleanField(default=False)
    is_prepaid = models.BooleanField(default=True)
    invoice_bill_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_plan_completed = models.BooleanField(default=False)
    is_bill_paid = models.BooleanField(default=False)
    payment_status = models.CharField(max_length=50, blank=True, null=True)
    invoice_id = models.CharField(max_length=50, blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)
