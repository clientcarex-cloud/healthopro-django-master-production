from django.db import models

from pro_hospital.models.patient_wise_models import PatientDoctorConsultationDetails
from pro_hospital.models.universal_models import DoctorConsultationDetails
from pro_laboratory.models.doctors_models import LabDoctors
from pro_laboratory.models.global_models import LabGlobalTests, LabGlobalPackages
from pro_laboratory.models.patient_models import Patient
from pro_pharmacy.models import PharmaItems
from pro_universal_data.models import UniversalAilments, UniversalFoodIntake, UniversalDayTimePeriod


class PatientPrescription(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT)
    doctor_consultation = models.ForeignKey(PatientDoctorConsultationDetails, on_delete=models.PROTECT, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    follow_up_days = models.IntegerField(blank=True, null=True)
    follow_up_date = models.DateField(blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    ailments = models.ManyToManyField(UniversalAilments, blank=True)
    last_updated_by = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(LabDoctors, on_delete=models.PROTECT, null=True, blank=True)


class VitalsInPrescription(models.Model):
    prescription = models.ForeignKey(PatientPrescription, on_delete=models.PROTECT)
    bp1 = models.CharField(blank=True, null=True)
    bp2 = models.CharField(blank=True, null=True)
    pulse = models.CharField(blank=True, null=True)
    height = models.CharField(blank=True, null=True)
    weight = models.CharField(blank=True, null=True)
    spo2 = models.CharField(blank=True, null=True)
    temperature = models.CharField(blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)


class InvestigationsInPrescription(models.Model):
    prescription = models.ForeignKey(PatientPrescription, on_delete=models.PROTECT)
    tests = models.ManyToManyField(LabGlobalTests, blank=True)
    packages = models.ManyToManyField(LabGlobalPackages, blank=True)
    added_on = models.DateTimeField(auto_now_add=True)


class MedicinesInPrescription(models.Model):
    prescription = models.ForeignKey(PatientPrescription, on_delete=models.PROTECT)
    medicine = models.ForeignKey(PharmaItems, on_delete=models.PROTECT)
    in_take_time = models.ManyToManyField(UniversalDayTimePeriod, blank=True)
    when_to_take = models.ForeignKey(UniversalFoodIntake, on_delete=models.PROTECT)
    quantity = models.CharField(blank=True, null=True)
    duration = models.IntegerField(blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)


