from django.db import models
from healtho_pro_user.models.business_models import BusinessProfiles
from pro_laboratory.models.global_models import LabGlobalTests, LabGlobalPackages, LabStaff
from pro_universal_data.models import ULabFonts, SourcingLabType


class SourcingLabRegistration(models.Model):
    min_paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True)
    min_print_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True)
    credit_payment = models.BooleanField(default=False)
    description = models.CharField(max_length=1000, null=True, blank=True)
    is_active = models.BooleanField(default=False)
    initiator = models.ForeignKey(BusinessProfiles, on_delete=models.PROTECT, blank=True, null=True,
                                  related_name='initiator')
    acceptor = models.ForeignKey(BusinessProfiles, on_delete=models.PROTECT, blank=True, null=True,
                                 related_name='acceptor')
    is_referral_lab=models.BooleanField(default=False)
    organization_name = models.CharField(max_length=500, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.CharField(max_length=200, blank=True, null=True)
    lab_code= models.CharField(max_length=20, blank=True, null=True)
    available_balance = models.DecimalField(max_digits=10, decimal_places=2,default=0, blank=True, null=True)
    type = models.ForeignKey(SourcingLabType, on_delete=models.PROTECT, blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


class SourcingLabPayments(models.Model):
    sourcing_lab = models.ForeignKey(SourcingLabRegistration, on_delete=models.PROTECT)
    previous_balance = models.DecimalField(max_digits=10, decimal_places=2,default=0, blank=True, null=True)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2,default=0, blank=True, null=True)
    available_balance = models.DecimalField(max_digits=10, decimal_places=2,default=0, blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    created_by=models.ForeignKey(LabStaff, on_delete=models.PROTECT)



class SourcingLabLetterHeadSettings(models.Model):
    sourcing_lab = models.ForeignKey(SourcingLabRegistration, on_delete=models.PROTECT)
    header_height = models.DecimalField(max_digits=6, decimal_places=1, blank=True, null=True)
    footer_height = models.DecimalField(max_digits=6, decimal_places=1, blank=True, null=True)
    display_letterhead = models.BooleanField(default=True)
    letterhead = models.TextField(blank=True, null=True)
    margin_left = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    margin_right = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    display_page_no = models.BooleanField(default=True)
    default_font=models.ForeignKey(ULabFonts, on_delete=models.PROTECT, blank=True, null=True)



class SourcingLabTestsTracker(models.Model):
    sourcing_lab = models.ForeignKey(SourcingLabRegistration, on_delete=models.PROTECT)
    patient_id=models.IntegerField(blank=True, null=True)
    lab_patient_test = models.IntegerField(blank=True, null=True)
    to_send=models.BooleanField(default=False)
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(blank=True, null=True)
    sent_remarks = models.CharField(max_length=500, blank=True, null=True)
    is_received = models.BooleanField(default=False)
    received_at = models.DateTimeField(blank=True, null=True)
    received_remarks = models.CharField(max_length=500, blank=True, null=True)
    is_cancelled = models.BooleanField(default=False)
    cancelled_at = models.DateTimeField(blank=True, null=True)
    cancellation_remarks= models.CharField(max_length=500, blank=True, null=True)
    patient_id_at_client = models.IntegerField(blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated_at = models.DateTimeField(auto_now=True)


class SourcingLabRevisedTestPrice(models.Model):
    sourcing_lab = models.ForeignKey(SourcingLabRegistration, on_delete=models.PROTECT)
    LabGlobalTestId = models.ForeignKey(LabGlobalTests, on_delete=models.PROTECT)
    revised_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)



class SourcingLabPatientReportUploads(models.Model):
    patient = models.ForeignKey('pro_laboratory.Patient', on_delete=models.PROTECT)
    tests = models.ManyToManyField('pro_laboratory.LabPatientTests', blank=True)
    pdf_file=models.TextField(blank=True, null=True)
    added_on=models.DateTimeField(auto_now_add=True)
