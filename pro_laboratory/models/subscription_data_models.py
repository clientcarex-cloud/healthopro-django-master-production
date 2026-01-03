from datetime import timedelta
from django.db import models
from django.utils import timezone
from healtho_pro_user.models.business_models import BusinessProfiles
from healtho_pro_user.models.subscription_models import BusinessBillCalculationType, BusinessSubscriptionPlans
from healtho_pro_user.models.users_models import HealthOProUser


class BusinessSubscriptionPlansPurchased(models.Model):
    b_id = models.ForeignKey(BusinessProfiles, on_delete=models.PROTECT)
    plan_name = models.CharField(max_length=200, blank=True, null=True)
    plan_start_date = models.DateTimeField(blank=True, null=True)
    plan_end_date = models.DateTimeField(blank=True, null=True)
    no_of_days = models.IntegerField(blank=True, null=True)
    amount_per_patient = models.DecimalField(max_digits=10, decimal_places=2,default=0)
    is_amount_percentage = models.BooleanField(default=False)
    is_prepaid = models.BooleanField(default=True)
    invoice_bill_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_plan_completed = models.BooleanField(default=False)
    is_bill_paid = models.BooleanField(default=False)
    payment_status=models.CharField(max_length=50, blank=True, null=True)
    invoice_id = models.CharField(max_length=50, blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    created_by=models.ForeignKey(HealthOProUser, on_delete=models.PROTECT,blank=True, null=True, related_name='plan_created_by')
    last_updated_by = models.ForeignKey(HealthOProUser, on_delete=models.PROTECT,blank=True, null=True, related_name='plan_last_updated_by')



