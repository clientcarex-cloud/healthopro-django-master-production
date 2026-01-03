from attr.validators import max_len
from django.db import models

from pro_laboratory.models.doctors_models import LabDoctors
from pro_laboratory.models.global_models import LabDepartments, LabStaff
from pro_laboratory.models.patient_models import Patient
from pro_universal_data.models import TimeCategory


class VehicleType(models.Model):
    name = models.CharField(max_length=200)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


class Vehicle(models.Model):
    name = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.PositiveIntegerField()
    license_plate_number = models.CharField(max_length=20)
    vehicle_type = models.ForeignKey(VehicleType, on_delete=models.CASCADE)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} {self.model} ({self.year})"


class Driver(models.Model):
    name = models.CharField(max_length=200)
    contact = models.CharField(max_length=20)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class VehicleBasicInfo(models.Model):
    ambulance_number = models.CharField(max_length=50, unique=True)
    is_status = models.BooleanField(default=False)
    location = models.CharField(max_length=600, blank=True, null=True)
    gps_tracking_enabled = models.BooleanField(default=False)
    emergency_contact = models.CharField(max_length=100)
    driver = models.OneToOneField(Driver, on_delete=models.CASCADE, related_name='ambulance_driver', blank=True,
                                  null=True)
    vehicle = models.OneToOneField(Vehicle, on_delete=models.CASCADE, related_name='ambulance_vehicle', blank=True,
                                   null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.ambulance_number


class AmbulanceDetails(models.Model):
    vehicle_basic_info = models.OneToOneField(VehicleBasicInfo, on_delete=models.CASCADE,
                                              related_name='vehicle_basic_details')
    maintenance_history = models.TextField(blank=True, null=True)
    insurance_details = models.TextField(blank=True, null=True)
    registration_details = models.TextField(blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.vehicle_basic_info.ambulance_number} Details"


class CaseType(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.name}'


class DoctorConsultationDetails(models.Model):
    labdoctors = models.ForeignKey(LabDoctors, on_delete=models.PROTECT, null=True, blank=True)
    case_type = models.ForeignKey(CaseType, on_delete=models.PROTECT, null=True, blank=True)
    is_online = models.BooleanField(default=False)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True)
    created_by = models.ForeignKey(LabStaff, on_delete=models.PROTECT, null=True, blank=True)
    last_updated_by = models.ForeignKey(LabStaff, on_delete=models.PROTECT, null=True, blank=True, related_name='doctor_consultation_fee_last_updated_by')
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        existing_instance = DoctorConsultationDetails.objects.filter(
            labdoctors=self.labdoctors,
            case_type=self.case_type,
            is_online=self.is_online,
        ).exclude(pk=self.pk)

        if existing_instance.exists():
            raise ValueError(
                "An instance with the same labdoctors, case_type, and is_online already exists."
            )

        super().save(*args, **kwargs)


class GlobalServices(models.Model):
    name = models.CharField(max_length=500)
    department = models.ForeignKey(LabDepartments, on_delete=models.PROTECT, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True)
    short_code = models.CharField(max_length=15, null=True, blank=True)
    description = models.CharField(max_length=1000, null=True, blank=True)
    created_by = models.ForeignKey(LabStaff, on_delete=models.PROTECT, null=True, blank=True)
    last_updated_by = models.ForeignKey(LabStaff, on_delete=models.PROTECT, null=True, blank=True, related_name='global_service_last_updated_by')
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)



class RoomType(models.Model): # AC, NON-AC, Casual, Deluxe
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.name}'


class Floor(models.Model):
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.name}'


class GlobalRoom(models.Model):
    name = models.CharField(max_length=200)
    room_type = models.ForeignKey(RoomType, on_delete=models.PROTECT, null=True, blank=True)
    room_number = models.CharField(max_length=100, null=True, blank=True)
    floor = models.ForeignKey(Floor, on_delete=models.PROTECT, null=True, blank=True)
    total_beds = models.IntegerField(null=True, blank=True)
    charges_per_bed = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True)
    time_category = models.ForeignKey(TimeCategory, on_delete=models.PROTECT, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.name}'


class GlobalRoomBeds(models.Model):
    global_room = models.ForeignKey(GlobalRoom, on_delete=models.PROTECT, null=True, blank=True)
    bed_number = models.IntegerField(null=True, blank=True)
    is_booked = models.BooleanField(default=False)
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, null=True, blank=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


class GlobalPackages(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.CharField(max_length=500, blank=True, null=True)
    offer_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_discount = models.DecimalField(max_digits=10, decimal_places=2)
    is_disc_percentage = models.BooleanField(default=False)
    package_image = models.ImageField(upload_to='package_images/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('pro_laboratory.LabStaff', on_delete=models.PROTECT, null=True)
    last_updated = models.DateTimeField(auto_now=True)


class GlobalPackageLabTest(models.Model):
    package = models.ForeignKey(GlobalPackages, on_delete=models.PROTECT, related_name='package_lab_tests')
    lab_test = models.ForeignKey('pro_laboratory.LabGlobalTests', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)

class GlobalPackageConsultation(models.Model):
    package = models.ForeignKey(GlobalPackages, on_delete=models.PROTECT, related_name='package_consultations')
    consultation = models.ForeignKey('pro_hospital.DoctorConsultationDetails', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)

class GlobalPackageService(models.Model):
    package = models.ForeignKey(GlobalPackages, on_delete=models.PROTECT, related_name='package_services')
    service = models.ForeignKey('pro_hospital.GlobalServices', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)

class GlobalPackageRoom(models.Model):
    package = models.ForeignKey(GlobalPackages, on_delete=models.PROTECT, related_name='package_rooms')
    room = models.ForeignKey('pro_hospital.GlobalRoom', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)


