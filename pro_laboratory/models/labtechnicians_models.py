from django.db import models
from healtho_pro_user.models.users_models import HealthOProUser
from pro_laboratory.models.doctors_models import LabDoctors
from pro_laboratory.models.global_models import LabGlobalTests, LabStaff, LabFixedParametersReportTemplate
from pro_laboratory.models.patient_models import LabPatientTests
from datetime import datetime
from pro_laboratory.models.universal_models import TpaUltrasound


class LabTechnicians(models.Model):
    LabPatientTestID = models.ForeignKey(LabPatientTests, on_delete=models.PROTECT, related_name='labtechnician')
    is_word_report = models.BooleanField(default=False)
    report_created_by = models.ForeignKey(
        LabStaff,
        on_delete=models.PROTECT,
        related_name='report_created_labtechnicians', blank=True, null=True  # Unique related_name
    )
    access = models.ManyToManyField(
        HealthOProUser,
        related_name='accessible_labtechnicians', blank=True
    )
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_passKey_used = models.BooleanField(default=False)
    added_on = models.DateTimeField(auto_now_add=True)
    has_machine_integration = models.BooleanField(default=False, blank=True, null=True)
    is_report_generated = models.BooleanField(default=False)
    is_report_finished = models.BooleanField(default=False)
    is_report_printed = models.BooleanField(default=False, blank=True, null=True)
    review_count = models.IntegerField(default=0, blank=True, null=True)
    last_updated = models.DateTimeField(auto_now=True)
    consulting_doctor = models.ForeignKey(LabDoctors, on_delete=models.PROTECT, null=True, blank=True)
    ultrasound_data = models.ForeignKey(TpaUltrasound, on_delete=models.PROTECT, null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.is_completed and not self.completed_at:
            self.completed_at = datetime.now()
        super().save(*args, **kwargs)


class LabTechnicianRemarks(models.Model):
    LabPatientTestID = models.ForeignKey(LabPatientTests, on_delete=models.PROTECT, null=True,
                                         related_name='lab_technician_remarks')
    remark = models.TextField(null=True, blank=True)
    added_by = models.ForeignKey(LabStaff, on_delete=models.PROTECT, null=True, blank=True)
    added_on = models.DateTimeField(auto_now_add=True)


# class LabPatientWordReportTemplatePageWiseContent(models.Model):
#     page_content = models.TextField(blank=True, null=True)


class LabPatientWordReportTemplate(models.Model):
    LabPatientTestID = models.ForeignKey(LabPatientTests, on_delete=models.PROTECT, null=True)
    # header = models.TextField(blank=True, null=True)
    # pages = models.ManyToManyField(LabPatientWordReportTemplatePageWiseContent, blank=True)
    report = models.TextField(blank=True)
    # rtf_content_header = models.TextField(blank=True, null=True)
    rtf_content_report = models.TextField(blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated_on = models.DateTimeField(auto_now=True,null=True, blank=True)
    created_by = models.ForeignKey(LabStaff, on_delete=models.PROTECT, null=True, blank=True)
    last_updated_by = models.ForeignKey(LabStaff, related_name='labpatientwordreporttemplate_lastupdatedby',
                                        on_delete=models.PROTECT, null=True, blank=True)


class LabPatientFixedReportTemplate(models.Model):
    LabGlobalTestID = models.ForeignKey(LabGlobalTests, on_delete=models.PROTECT)
    LabPatientTestID = models.ForeignKey(LabPatientTests, on_delete=models.PROTECT, null=True)
    template = models.ForeignKey(LabFixedParametersReportTemplate, on_delete=models.PROTECT, blank=True, null=True)
    ordering = models.SmallIntegerField(null=True, blank=True)
    group = models.CharField(max_length=300, blank=True, null=True)
    method = models.CharField(max_length=300, blank=True, null=True)
    parameter = models.CharField(max_length=500)
    value = models.CharField(max_length=1000, blank=True, null=True)
    units = models.CharField(max_length=200, blank=True, null=True)
    formula = models.TextField(blank=True, null=True)
    referral_range = models.TextField(null=True, blank=True)
    added_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(LabStaff, on_delete=models.PROTECT, null=True, blank=True)
    last_updated_by = models.ForeignKey(LabStaff, related_name='labpatientfixedreporttemplate_lastupdatedby',
                                        on_delete=models.PROTECT, null=True, blank=True)
    is_value_only = models.BooleanField(default=False)
    is_value_bold = models.BooleanField(default=False)


