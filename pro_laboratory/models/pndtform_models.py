from django.db import models

from healtho_pro_user.models.business_models import BusinessAddresses
from pro_laboratory.models.doctors_models import LabDoctors
from pro_laboratory.models.patient_models import Patient


class FamilyGeneticHistory(models.Model):
    patient = models.OneToOneField(Patient, on_delete=models.PROTECT)
    clinical_history = models.CharField(max_length=300, null=True, blank=True)
    biochemical_history = models.CharField(max_length=300, null=True, blank=True)
    cytogenetic_history = models.CharField(max_length=300, null=True, blank=True)
    other_history = models.CharField(max_length=300, null=True, blank=True)
    male_children_count = models.IntegerField(null=True, blank=True)
    female_children_count = models.IntegerField(null=True, blank=True)
    father_name = models.CharField(max_length=100, null=True, blank=True)
    husband_name = models.CharField(max_length=100, null=True, blank=True)


class PrenatalScreening(models.Model):
    patient = models.OneToOneField(Patient, on_delete=models.PROTECT)
    chromosomal_disorders = models.CharField(max_length=300, null=True, blank=True)
    metabolic_disorders = models.CharField(max_length=300, null=True, blank=True)
    congenital_anomalies = models.CharField(max_length=300, null=True, blank=True)
    intellectual_disabilities = models.CharField(max_length=300, null=True, blank=True)
    hemoglobinopathies = models.CharField(max_length=300, null=True, blank=True)
    sex_linked_disorders = models.CharField(max_length=300, null=True, blank=True)
    single_gene_disorders = models.CharField(max_length=300, null=True, blank=True)
    other_disorders = models.TextField(null=True, blank=True)
    maternal_age = models.CharField(max_length=300, null=True, blank=True)
    last_menstrual_period = models.CharField(max_length=50, null=True, blank=True)
    family_genetic_history = models.CharField(max_length=300, null=True, blank=True)
    other_information = models.CharField(max_length=300, null=True, blank=True)


class MTPInfo(models.Model):
    patient = models.OneToOneField(Patient, on_delete=models.PROTECT)
    mtp_performed_by = models.CharField(max_length=100, null=True, blank=True)
    date_mtp_performed = models.CharField(null=True, blank=True)
    mtp_advised_by = models.CharField(max_length=100, null=True, blank=True)
    mtp_advised_date = models.CharField(null=True, blank=True)
    registration_number = models.CharField(max_length=300, null=True, blank=True)
    pndt_number = models.CharField(max_length=100, null=True, blank=True)
    place_mtp = models.CharField(max_length=100, null=True, blank=True)


class RecommendedTests(models.Model):
    patient = models.OneToOneField(Patient, on_delete=models.PROTECT)
    chromosomal_studies = models.CharField(max_length=300, null=True, blank=True)
    biochemical_studies = models.CharField(max_length=300, null=True, blank=True)
    molecular_studies = models.CharField(max_length=300, null=True, blank=True)
    pre_implantation_genetic_diagnosis = models.CharField(max_length=300, null=True, blank=True)


class PNDTResults(models.Model):
    patient = models.OneToOneField(Patient, on_delete=models.PROTECT)
    prenatal_diagnostic_procedure = models.CharField(max_length=300, null=True, blank=True)
    ultrasonography_results = models.CharField(max_length=300, null=True, blank=True)
    date_consent_obtained = models.CharField(null=True, blank=True)
    date_procedures_carried_out = models.CharField(null=True, blank=True)
    results_conveyed_to = models.CharField(max_length=300, null=True, blank=True)
    results_conveyed_on = models.CharField(null=True, blank=True)


class ProceduresPerformed(models.Model):
    patient = models.OneToOneField(Patient, on_delete=models.PROTECT)
    doctors = models.ManyToManyField(LabDoctors, blank=True)
    registration_number = models.CharField(max_length=200, null=True, blank=True)
    pndt_number = models.CharField(max_length=100, null=True, blank=True)
    ultrasound_test_purpose = models.CharField(max_length=300, null=True, blank=True)
    complications = models.CharField(max_length=100, null=True, blank=True)
    clinic_details = models.ForeignKey(BusinessAddresses, on_delete=models.PROTECT, blank=True, null=True)