from django.db import models, transaction
from django.utils import timezone

from healtho_pro_user.models.business_models import BusinessAddresses
from healtho_pro_user.models.users_models import Client
from pro_hospital.models.universal_models import GlobalServices, DoctorConsultationDetails
from pro_laboratory.models.doctors_models import LabDoctors
from pro_laboratory.models.global_models import LabStaff, LabGlobalTests, LabGlobalPackages
from pro_laboratory.models.patient_models import Patient
from pro_universal_data.models import ULabPatientTitles, ULabPatientGender, ULabPatientAge


class LabAppointmentForPatient(models.Model):
    title = models.ForeignKey(ULabPatientTitles, on_delete=models.PROTECT, null=True)
    name = models.CharField(max_length=100)
    age = models.IntegerField()
    dob = models.DateField(null=True, blank=True)
    ULabPatientAge = models.ForeignKey(ULabPatientAge, on_delete=models.PROTECT, null=True)
    gender = models.ForeignKey(ULabPatientGender, on_delete=models.PROTECT, null=True)
    referral_doctor = models.ForeignKey(LabDoctors, on_delete=models.PROTECT, null=True, blank=True,
                                        related_name='lab_appointment_ref_patient')

    consulting_doctor = models.ForeignKey(LabDoctors, on_delete=models.PROTECT, null=True, blank=True,
                                        related_name='lab_appointment_cons_doctor')
    mobile_number = models.CharField(max_length=15)
    email = models.EmailField(null=True, blank=True)
    area = models.CharField(max_length=200, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    prescription_attach = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(LabStaff, on_delete=models.PROTECT,null=True)
    appointment_type_id = models.IntegerField(null=True, blank=True)
    appointment_no = models.CharField(max_length=50,blank=True, null=True)
    appointment_date = models.DateField(blank=True, null=True)
    appointment_time=models.TimeField(blank=True, null=True)

    last_updated_by = models.ForeignKey(LabStaff, related_name='lab_appointment_last_updated_by', on_delete=models.PROTECT,
                                        null=True, blank=True)
    added_on = models.DateTimeField(default=timezone.now)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, blank=True, null=True)
    tests=models.ManyToManyField(LabGlobalTests, blank=True)
    packages = models.ManyToManyField(LabGlobalPackages, blank=True)
    services = models.ManyToManyField(GlobalServices, blank=True)
    doctor_consultation = models.ManyToManyField(DoctorConsultationDetails, blank=True)
    branch = models.ForeignKey(BusinessAddresses, on_delete=models.PROTECT, blank=True, null=True)
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, blank=True, null=True, related_name='patient_appointment')
    is_cancelled=models.BooleanField(default=False)
    reason_of_cancellation = models.CharField(max_length=300, blank=True, null=True)

    def __str__(self):
        return f'{self.appointment_no} - {self.name}, {self.title}, {self.created_by}'


