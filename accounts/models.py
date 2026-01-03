from django.db import models
from django.utils import timezone
from healtho_pro_user.models.business_models import BusinessProfiles
from pro_laboratory.models.global_models import LabStaff
from pro_universal_data.models import ULabPaymentModeType


# Create your models here.


class LabExpenseType(models.Model):
    name = models.CharField(max_length=500)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}"


class LabPaidToType(models.Model):
    name = models.CharField(max_length=500)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}"


# class LabPayModeType(models.Model): # Admin Panel
#     name = models.CharField(max_length=500)
#     is_active = models.BooleanField(default=True)
#     added_on = models.DateTimeField(auto_now_add=True)
#     last_updated = models.DateTimeField(auto_now=True)
#
#     def __str__(self):
#         return f"{self.name}"


class LabIncomeFromAccount(models.Model):
    name = models.CharField(max_length=500)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}"


class LabExpenses(models.Model): # API
    expense_date = models.DateField()
    expense_type = models.ForeignKey(LabExpenseType, on_delete=models.PROTECT, null=True)
    paid_to = models.ForeignKey(LabPaidToType, on_delete=models.PROTECT)
    pay_mode = models.ForeignKey(ULabPaymentModeType, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10,decimal_places=2)
    description = models.CharField(max_length=500)
    voucher_id = models.CharField(max_length=100, null=True, blank=True)
    is_authorized = models.BooleanField(default=False)
    authorized_by = models.ForeignKey(LabStaff, on_delete=models.PROTECT, blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    invoice_no = models.CharField(max_length=100, blank=True, null=True)
    account_to = models.ForeignKey(LabStaff, on_delete=models.PROTECT, null=True, blank=True, related_name='staff_expenses')

    def save(self, *args, **kwargs):
        date = timezone.now().date()
        expenses = LabExpenses.objects.filter(added_on__date=date)
        expense_number = expenses.count() + 1
        date = date.strftime('%y%m%d')
        voucher_id = f"EXP{date}{expense_number:03d}"
        self.voucher_id = voucher_id
        super().save(*args, **kwargs)


# Income Account

class LabIncomeType(models.Model): # API 2
    name = models.CharField(max_length=500)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}"


class LabIncomes(models.Model): # API
    income_date = models.DateField()
    income_type = models.ForeignKey(LabIncomeType, on_delete=models.PROTECT)
    received_from = models.ForeignKey(LabIncomeFromAccount, on_delete=models.PROTECT, related_name='received_incomes', null=True, blank=True)
    pay_mode = models.ForeignKey(ULabPaymentModeType, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10,decimal_places=2)
    description = models.CharField(max_length=500)
    income_id = models.CharField(max_length=100, null=True, blank=True)
    is_authorized = models.BooleanField(default=False)
    authorized_by = models.ForeignKey(LabStaff, on_delete=models.PROTECT, blank=True, null=True, related_name='authorized_incomes')
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    account_to = models.ForeignKey(LabStaff, on_delete=models.PROTECT, null=True, blank=True, related_name='staff_incomes')

    def save(self, *args, **kwargs):
        date = timezone.now().date()
        incomes = LabIncomes.objects.filter(added_on__date=date)
        income_number = incomes.count() + 1
        date = date.strftime('%y%m%d')
        income_id = f"INC{date}{income_number:03d}"
        self.income_id = income_id
        super().save(*args, **kwargs)