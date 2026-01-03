from django.db import models
from pro_laboratory.models.global_models import LabStaff
from pro_laboratory.models.patient_models import LabPatientTests
from datetime import datetime


class LabPhlebotomist(models.Model):
    LabPatientTestID = models.OneToOneField(LabPatientTests, on_delete=models.PROTECT, related_name='phlebotomist')
    is_received = models.BooleanField(default=False, blank=True)
    received_by = models.ForeignKey(
        LabStaff,
        on_delete=models.PROTECT,
        related_name='received_labphlebotomists' , blank=True # Unique related_name
    )
    received_at = models.DateTimeField(null=True, blank=True)
    is_collected = models.BooleanField(default=False, blank=True)
    assession_number = models.CharField(max_length=30, null=True, blank=True)
    collected_by = models.ForeignKey(
        LabStaff,
        on_delete=models.PROTECT,
        related_name='collected_labphlebotomists', blank=True  # Unique related_name
    )
    collected_at = models.DateTimeField(null=True, blank=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.LabPatientTestID}"

    def save(self, *args, **kwargs):
        if self.is_received and not self.received_at:
            self.received_at = datetime.now()
        if self.is_collected and not self.collected_at:
            self.collected_at = datetime.now()

        super().save(*args, **kwargs)

