from django.db import models

from healtho_pro_user.models.business_models import BusinessProfiles
from healtho_pro_user.models.users_models import Client, HealthOProUser
from pro_laboratory.models.bulk_messaging_models import BulkMessagingTemplates
from pro_laboratory.models.doctors_models import LabDoctors
from pro_laboratory.models.global_models import LabDepartments, LabStaff
from pro_universal_data.models import ULabFonts, DepartmentFlowType, MessagingTemplates, MessagingVendors, \
    UniversalActionType


class LetterHeadSettings(models.Model):
    client = models.OneToOneField(Client, on_delete=models.PROTECT, blank=True, null=True)
    header_height = models.DecimalField(max_digits=6, decimal_places=1, blank=True, null=True)
    footer_height = models.DecimalField(max_digits=6, decimal_places=1, blank=True, null=True)
    display_letterhead = models.BooleanField(default=True)
    margin_left = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    margin_right = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    invoice_space = models.BooleanField(default=True)
    receipt_space = models.BooleanField(default=True)
    display_page_no = models.BooleanField(default=True)
    default_font=models.ForeignKey(ULabFonts, on_delete=models.PROTECT, blank=True, null=True)


class PrintTestReportSettings(models.Model):
    client = models.OneToOneField(Client, on_delete=models.PROTECT)
    merge_test_reports = models.BooleanField(default=False)
    print_matched_ref_ranges=models.BooleanField(default=False)


class PrintReportSettings(models.Model):
    barcode_height = models.DecimalField(max_digits=6, decimal_places=1, blank=True, null=True)
    barcode_width = models.DecimalField(max_digits=6, decimal_places=1, blank=True, null=True)
    qr_code_size = models.DecimalField(max_digits=6, decimal_places=1, blank=True, null=True)
    test_barcode_height = models.DecimalField(max_digits=6, decimal_places=1)
    test_barcode_width = models.DecimalField(max_digits=6, decimal_places=1)


class BusinessDataStatus(models.Model):
    client = models.OneToOneField(Client, on_delete=models.PROTECT, blank=True, null=True)
    b_id = models.OneToOneField(BusinessProfiles, on_delete=models.PROTECT, blank=True, null=True)
    is_data_imported = models.BooleanField(default=False)


class CopiedLabDepartmentsData(models.Model):
    client = models.OneToOneField(Client, on_delete=models.PROTECT, blank=True, null=True)
    b_id = models.OneToOneField(BusinessProfiles, on_delete=models.PROTECT, blank=True, null=True)
    departments = models.ManyToManyField(LabDepartments, blank=True)


class BusinessDiscountSettings(models.Model):
    number = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_percentage = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


class BusinessPaidAmountSettings(models.Model):
    number = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_percentage = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


class OtherBusinessSettings(models.Model):
    manual_date=models.BooleanField(default=False)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


class BusinessPNDTDetails(models.Model):
    b_id = models.OneToOneField(BusinessProfiles, on_delete=models.PROTECT, null=True)
    default_pndt_doctors = models.ManyToManyField(LabDoctors, blank=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)


class PrintDueReports(models.Model):
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


class PNDTRegistrationNumber(models.Model):
    pndt_number = models.CharField(max_length=300, blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


class BusinessMessageSettings(models.Model):
    is_sms_active = models.BooleanField(default=True)
    is_whatsapp_active = models.BooleanField(default=True)
    whatsapp_vendor=models.ForeignKey(MessagingVendors, on_delete=models.PROTECT,blank=True, null=True, related_name='vendor')
    send_reports_by=models.ForeignKey(UniversalActionType, on_delete=models.PROTECT,blank=True, null=True,related_name='send_reports_by')
    client = models.OneToOneField(Client, on_delete=models.PROTECT)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


class BusinessReferralDoctorSettings(models.Model):
    client = models.OneToOneField(Client, on_delete=models.PROTECT, null=True)
    is_calculation_by_total = models.BooleanField(default=True)
    is_calculation_by_net_total = models.BooleanField(default=False)
    due_clear_patients = models.BooleanField(default=False)
    discount_by_doctor = models.BooleanField(default=False)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


class LabStaffPrintSettings(models.Model):
    lab_staff=models.ForeignKey(LabStaff, on_delete=models.PROTECT)
    auto_invoice_print = models.BooleanField(default=True)
    auto_receipt_print = models.BooleanField(default=True)
    show_remarks_at_patient = models.BooleanField(default=True)
    phlebotomist_print = models.BooleanField(default=True)
    patient_data_in_barcode = models.BooleanField(default=False)
    technician_print = models.BooleanField(default=False)
    radiology_print = models.BooleanField(default=False)
    show_print_preview=models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated_at = models.DateTimeField(auto_now=True)



class ClientWiseMessagingTemplates(models.Model):
    client = models.OneToOneField(Client, on_delete=models.PROTECT)
    templates=models.ManyToManyField(MessagingTemplates, blank=True)
    bulk_templates = models.ManyToManyField(BulkMessagingTemplates, blank=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


class BusinessEmailDetails(models.Model):
    email = models.CharField(max_length=100, null=True, blank=True)
    password = models.CharField(max_length=100, null=True, blank=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


class BusinessControls(models.Model):
    multiple_branches = models.BooleanField(default=False)
    added_on = models.DateTimeField(auto_now_add=True)
    # created_by=models.ForeignKey(HealthOProUser, on_delete=models.PROTECT, blank=True, null=True)
    last_updated = models.DateTimeField(auto_now=True)
    last_updated_by=models.ForeignKey(HealthOProUser, on_delete=models.PROTECT, blank=True, null=True)




class ReportFontSizes(models.Model):
    dept_name_size = models.IntegerField(default=16)
    dept_name_weight = models.IntegerField(default=600)
    dept_name_alignment = models.CharField(max_length=20, default="center", null=True, blank=True)
    test_name_size = models.IntegerField(default=14)
    test_name_weight = models.IntegerField(default=400)
    test_name_alignment = models.CharField(max_length=20, default="left", null=True, blank=True)
    report_head_size = models.IntegerField(default=14)
    report_head_weight = models.IntegerField(default=600)
    parameter_size = models.IntegerField(default=12)
    parameter_weight = models.IntegerField(default=400)
    result_size = models.IntegerField(default=12)
    unit_size = models.IntegerField(default=12)
    unit_weight = models.IntegerField(default=400)
    ref_range_size = models.IntegerField(default=12)
    ref_range_weight = models.IntegerField(default=400)
    method_size = models.IntegerField(default=10)
    method_weight = models.IntegerField(default=300)
    group_name_size = models.IntegerField(default=14)
    group_name_weight = models.IntegerField(default=600)
    test_display_name = models.CharField(max_length=20, default="Test Name", null=True, blank=True)
    result_display_name = models.CharField(max_length=20, default="Result", null=True, blank=True)
    unit_display_name = models.CharField(max_length=20, default="Unit", null=True, blank=True)
    ref_ranges_display_name = models.CharField(max_length=20, default="Bio.Ref.Range", null=True, blank=True)
    method_display_name = models.CharField(max_length=20, default="METHOD:", null=True, blank=True)
    method_is_italic = models.BooleanField(default=True)


class PharmacyPricingConfig(models.Model):
    tax_percentage = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_percentage = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

