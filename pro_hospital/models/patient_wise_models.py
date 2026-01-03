from datetime import datetime

from django.db import models
from pro_hospital.models.universal_models import CaseType, GlobalServices, RoomType, Floor, GlobalRoom, \
    DoctorConsultationDetails, GlobalPackages, GlobalRoomBeds
from pro_laboratory.models.doctors_models import LabDoctors
from pro_laboratory.models.global_models import LabStaff
from pro_laboratory.models.patient_models import Patient
from pro_universal_data.models import ULabTestStatus, TimeCategory

from math import ceil

from pro_universal_data.models import ConsultationType, ULabTestStatus, TimeCategory


class PatientPackages(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, null=True)
    GlobalPackageId = models.ForeignKey(GlobalPackages, on_delete=models.PROTECT, null=True)
    name = models.CharField(max_length=200, unique=True)
    description = models.CharField(max_length=500, blank=True, null=True)
    offer_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_discount = models.DecimalField(max_digits=10, decimal_places=2)
    is_disc_percentage = models.BooleanField(default=False)
    package_image = models.ImageField(upload_to='package_images/', null=True, blank=True)
    is_package_cancelled = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('pro_laboratory.LabStaff', on_delete=models.PROTECT, null=True)
    last_updated = models.DateTimeField(auto_now=True)


class PatientDoctorConsultationDetails(models.Model):
    consultation = models.ForeignKey(DoctorConsultationDetails, on_delete=models.PROTECT, null=True, blank=True)
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, null=True, blank=True)
    case_type = models.ForeignKey(CaseType, on_delete=models.PROTECT, null=True, blank=True)
    status_id = models.ForeignKey(ULabTestStatus, on_delete=models.PROTECT, null=True, blank=True)
    is_online = models.BooleanField(default=False) #True if online and false if Walk-in
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    is_package = models.BooleanField(default=False)
    package = models.ForeignKey(PatientPackages, on_delete=models.PROTECT, null=True, blank=True)
    created_by = models.ForeignKey(LabStaff, on_delete=models.PROTECT, null=True, blank=True)
    last_updated_by = models.ForeignKey(LabStaff, on_delete=models.PROTECT, null=True, blank=True, related_name='doctor_appointment_consultation_details_last_updated_by')
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


class PatientServices(models.Model):
    name = models.CharField(max_length=500)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    short_code = models.CharField(max_length=15, null=True, blank=True)
    status_id = models.ForeignKey(ULabTestStatus, on_delete=models.PROTECT, null=True, blank=True)
    service = models.ForeignKey(GlobalServices, on_delete=models.PROTECT, null=True, blank=True)
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, null=True, blank=True)
    is_package = models.BooleanField(default=False)
    package = models.ForeignKey(PatientPackages, on_delete=models.PROTECT, null=True, blank=True)
    created_by = models.ForeignKey(LabStaff, on_delete=models.PROTECT, null=True, blank=True)
    last_updated_by = models.ForeignKey(LabStaff, on_delete=models.PROTECT, null=True, blank=True,related_name='patient_service_last_updated_by')
    added_on = models.DateTimeField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)


class IPRoomBooking(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, null=True, blank=True)
    no_of_days = models.IntegerField(null=True, blank=True)
    GlobalRoomId = models.ForeignKey(GlobalRoom, on_delete=models.PROTECT, null=True, blank=True)
    name = models.CharField(max_length=200)
    room_type = models.ForeignKey(RoomType, on_delete=models.PROTECT, null=True, blank=True)
    room_number = models.CharField(max_length=100, null=True, blank=True)
    floor = models.ForeignKey(Floor, on_delete=models.PROTECT, null=True, blank=True)
    booked_bed_number = models.ForeignKey(GlobalRoomBeds, on_delete=models.PROTECT, null=True, blank=True)
    is_package = models.BooleanField(default=False)
    package = models.ForeignKey(PatientPackages, on_delete=models.PROTECT, null=True, blank=True)
    charges_per_bed = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True)
    time_category = models.ForeignKey(TimeCategory, on_delete=models.PROTECT, null=True, blank=True)
    created_by = models.ForeignKey(LabStaff, on_delete=models.PROTECT, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    admitted_date = models.DateTimeField(null=True, blank=True)
    vacated_date = models.DateTimeField(null=True, blank=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.admitted_date and (self.vacated_date or datetime.now()):
            vacated_date = self.vacated_date or datetime.now()
            delta = vacated_date - self.admitted_date
            if self.time_category:
                if self.time_category.name.lower() == "day":
                    self.no_of_days = delta.days + (1 if delta.seconds > 0 else 0)
                    if self.no_of_days == 0:
                        self.no_of_days = 1
                elif self.time_category.name.lower() == "hour":
                    total_hours = delta.days * 24 + delta.seconds // 3600
                    if delta.seconds % 3600 > 0:  # Add 1 hour for leftover seconds
                        total_hours += 1
                    self.no_of_days = max(total_hours, 1)
                else:
                    self.no_of_days = None
            else:
                self.no_of_days = None
        else:
            self.no_of_days = None

        super().save(*args, **kwargs)



class PatientVitals(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, null=True, blank=True)
    bp1 = models.CharField(blank=True, null=True)
    bp2 = models.CharField(blank=True, null=True)
    pulse = models.CharField(blank=True, null=True)
    height = models.CharField(blank=True, null=True)
    weight = models.CharField(blank=True, null=True)
    spo2 = models.CharField(blank=True, null=True)
    temperature = models.CharField(blank=True, null=True)
    grbs = models.CharField(max_length=100, null=True, blank=True)
    added_on = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(LabStaff, on_delete=models.PROTECT, null=True, blank=True)
