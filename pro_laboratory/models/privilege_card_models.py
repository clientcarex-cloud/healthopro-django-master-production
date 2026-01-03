from django.db import models
from pro_laboratory.models.global_models import LabDepartments, LabStaff, LabGlobalTests
from pro_laboratory.models.patient_models import Patient
from pro_universal_data.models import ULabPatientGender, ULabRelations, TimeDurationTypes, PrivilegeCardBenefits, \
    AvailabilityPeriod


class PrivilegeCardFor(models.Model):  #Individual , Family
    name = models.CharField(max_length=200)
    added_on = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name}"


class PrivilegeCards(models.Model):
    name = models.CharField(max_length=200, unique=True)
    card_cost = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    no_of_members = models.IntegerField(blank=True, null=True)
    plan_period_type = models.ForeignKey(AvailabilityPeriod, on_delete=models.PROTECT, blank=True, null=True)
    card_for = models.ForeignKey(PrivilegeCardFor, on_delete=models.PROTECT, null=True, blank=True)
    duration = models.IntegerField(null=True, blank=True)
    duration_type = models.ForeignKey(TimeDurationTypes, on_delete=models.PROTECT, null=True, blank=True)
    card_prefix = models.CharField(max_length=5, blank=True, null=True)
    pc_no_length = models.IntegerField(blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, blank=True, null=True)
    created_by = models.ForeignKey(LabStaff, on_delete=models.PROTECT, related_name='created_by')
    last_updated_by = models.ForeignKey(LabStaff, on_delete=models.PROTECT, related_name='last_updated_by')


class PrivilegeCardsApplicableBenefits(models.Model):
    card = models.ForeignKey(PrivilegeCards, on_delete=models.PROTECT, blank=True, null=True)
    benefit = models.ForeignKey(PrivilegeCardBenefits, on_delete=models.PROTECT, blank=True, null=True)
    free_usages = models.IntegerField(null=True, blank=True)
    discount_usages = models.IntegerField(null=True, blank=True)
    discount = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    is_discount_percentage = models.BooleanField(default=True, null=True, blank=True)


class PrivilegeCardsLabTestBenefits(models.Model):
    card = models.ForeignKey(PrivilegeCards, on_delete=models.PROTECT, blank=True, null=True)
    test = models.ForeignKey(LabGlobalTests, on_delete=models.PROTECT, blank=True, null=True)
    discount = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    is_discount_percentage = models.BooleanField(default=True, null=True, blank=True)


class PrivilegeCardsLabDepartmentsBenefits(models.Model):
    card = models.ForeignKey(PrivilegeCards, on_delete=models.PROTECT, blank=True, null=True)
    department = models.ForeignKey(LabDepartments, on_delete=models.PROTECT, blank=True, null=True)
    discount = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    is_discount_percentage = models.BooleanField(default=True, null=True, blank=True)


class PrivilegeCardsMembershipApplicableBenefits(models.Model):
    membership = models.ForeignKey('PrivilegeCardMemberships', on_delete=models.PROTECT)
    benefit = models.ForeignKey(PrivilegeCardBenefits, on_delete=models.PROTECT, blank=True, null=True)
    free_usages = models.IntegerField(null=True, blank=True)
    availed_free_usages = models.IntegerField(null=True, blank=True)
    discount_usages = models.IntegerField(null=True, blank=True)
    availed_discount_usages = models.IntegerField(null=True, blank=True)
    discount = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    is_discount_percentage = models.BooleanField(default=True, null=True, blank=True)


# PrivilegeCardHolders
class PrivilegeCardMemberships(models.Model):
    card = models.ForeignKey(PrivilegeCards, on_delete=models.PROTECT)
    card_name = models.CharField(max_length=200, blank=True, null=True)
    pc_no = models.CharField(max_length=20, blank=True, null=True)
    card_holder = models.ForeignKey('PrivilegeCardMembers', on_delete=models.PROTECT, blank=True, null=True)
    card_cost = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    card_for = models.ForeignKey(PrivilegeCardFor, on_delete=models.PROTECT, null=True)
    plan_period_type = models.ForeignKey(AvailabilityPeriod, on_delete=models.PROTECT, blank=True, null=True)
    duration = models.IntegerField(null=True, blank=True)
    duration_type = models.ForeignKey(TimeDurationTypes, on_delete=models.PROTECT, null=True, blank=True)
    validity_starts_on = models.DateField(blank=True, null=True)
    validity_ends_on = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True, blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(LabStaff, on_delete=models.PROTECT, related_name='card_holder_created_by')
    last_updated_by = models.ForeignKey(LabStaff, on_delete=models.PROTECT, related_name='card_holder_last_updated_by')


class PrivilegeCardMembers(models.Model):
    profile_image = models.TextField(blank=True, null=True)
    name = models.CharField(max_length=100)
    dob = models.DateField(null=True, blank=True)
    email = models.CharField(max_length=50, blank=True, null=True)
    gender = models.ForeignKey(ULabPatientGender, on_delete=models.PROTECT, null=True)
    mobile_number = models.CharField(max_length=15, blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)
