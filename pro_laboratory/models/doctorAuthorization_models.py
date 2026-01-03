from django.db import models
from pro_laboratory.models.global_models import LabStaff
from pro_laboratory.models.patient_models import LabPatientTests


class LabDrAuthorizationRemarks(models.Model):
    LabPatientTestID = models.ForeignKey(LabPatientTests, on_delete=models.PROTECT, null=True, related_name = 'lab_dr_authorization_remarks')
    remark = models.CharField(max_length=500)
    is_retest = models.BooleanField(default=True)
    added_by = models.ForeignKey(LabStaff, on_delete=models.PROTECT)
    added_on = models.DateTimeField(auto_now_add=True)


class LabDrAuthorization(models.Model):
    LabPatientTestID = models.ForeignKey(LabPatientTests, on_delete=models.PROTECT, null=True, related_name= 'lab_dr_authorization')
    is_authorized = models.BooleanField(default=False)
    is_passKey_used = models.BooleanField(default=False)
    added_on = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(LabStaff, on_delete=models.PROTECT,null=True)

