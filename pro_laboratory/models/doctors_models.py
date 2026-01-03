from email.policy import default

from django.db import models
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from healtho_pro_user.models.universal_models import UProDoctorSpecializations, City, State, Country
from healtho_pro_user.models.users_models import HealthOProUser
from pro_laboratory.models.global_models import LabShift, LabBranch, LabBloodGroup, \
    LabMaritalStatus, LabWorkingDays, LabDoctorRole, LabDepartments, LabGlobalTests, LabStaff
from pro_universal_data.models import ULabStaffGender, UniversalBloodGroups, UniversalMaritalStatus, \
    DoctorSalaryPaymentTypes, DoctorTransactionTypes


class LabDoctorsType(models.Model):  # Referral Doctor, Consultant Doctor
    name = models.CharField(max_length=200)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.name}'


class LabDoctors(models.Model):
    doctor_type_id = models.ForeignKey(LabDoctorsType, on_delete=models.PROTECT, null=True)
    name = models.CharField(max_length=100)
    mobile_number = models.CharField(max_length=15)
    email = models.EmailField(blank=True, null=True)
    license_number = models.CharField(max_length=200, unique=True, null=True, blank=True)
    geo_area = models.CharField(max_length=100, blank=True, null=True)
    specialization = models.ForeignKey('DoctorSpecializations', on_delete=models.PROTECT, blank=True, null=True)
    qualification = models.CharField(max_length=100, null=True, blank=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    signature_for_consulting = models.TextField(blank=True, null=True)
    gender = models.ForeignKey(ULabStaffGender, null=True, blank=True, on_delete=models.PROTECT)
    role = models.ForeignKey(LabDoctorRole, null=True, blank=True, on_delete=models.PROTECT)
    department = models.ForeignKey(LabDepartments, null=True, blank=True, on_delete=models.PROTECT)
    shift = models.ForeignKey(LabShift, null=True, blank=True, on_delete=models.PROTECT)
    shift_start_time = models.TimeField(blank=True, null=True)
    shift_end_time = models.TimeField(blank=True, null=True)
    avg_consulting_time = models.IntegerField(blank=True, null=True)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True)
    branch = models.ForeignKey(LabBranch, null=True, blank=True, on_delete=models.PROTECT)
    lab_working_days = models.ManyToManyField(LabWorkingDays, blank=True)
    is_active = models.BooleanField(default=True)
    is_duplicate = models.BooleanField(default=False)
    free_visits_count = models.IntegerField(blank=True, null=True)
    free_visit_validation_in_days = models.IntegerField(blank=True, null=True)
    pro_user_id = models.ForeignKey(HealthOProUser, on_delete=models.PROTECT, blank=True, null=True)
    marketing_executive = models.ForeignKey(LabStaff, on_delete=models.PROTECT, blank=True, null=True)

    def __str__(self):
        return f'{self.name}'

    def save(self, *args, **kwargs):
        if not self.id:
            if self.mobile_number == "0000000000":
                if LabDoctors.objects.filter(doctor_type_id=self.doctor_type_id, name=self.name,
                                             mobile_number=self.mobile_number).exists():
                    raise ValidationError({"Error": "Doctor with the same name already exists!"})
                else:
                    super().save(*args, **kwargs)

            elif self.mobile_number != "0000000000":
                if LabDoctors.objects.filter(doctor_type_id=self.doctor_type_id, name=self.name,
                                             mobile_number=self.mobile_number).exists():
                    raise ValidationError({"Error": "Doctor with the same name and mobile number already exists!"})
                elif LabDoctors.objects.filter(doctor_type_id=self.doctor_type_id,
                                               mobile_number=self.mobile_number).exists():
                    raise ValidationError({"Error": "Doctor with the same mobile number already exists!"})
                else:
                    super().save(*args, **kwargs)
        else:
            if self.mobile_number == "0000000000":
                if LabDoctors.objects.filter(doctor_type_id=self.doctor_type_id, name=self.name,
                                             mobile_number=self.mobile_number).exclude(pk=self.pk).exists():
                    raise ValidationError({"Error": "Doctor with the same name already exists!"})
                else:
                    super().save(*args, **kwargs)

            elif self.mobile_number != "0000000000":
                if LabDoctors.objects.filter(doctor_type_id=self.doctor_type_id, name=self.name,
                                             mobile_number=self.mobile_number).exclude(pk=self.pk).exists():
                    raise ValidationError({"Error": "Doctor with the same name and mobile number already exists!"})
                elif LabDoctors.objects.filter(doctor_type_id=self.doctor_type_id,
                                               mobile_number=self.mobile_number).exclude(pk=self.pk).exists():
                    raise ValidationError({"Error": "Doctor with the same mobile number already exists!"})
                else:
                    super().save(*args, **kwargs)


class LabDoctorsPersonalDetails(models.Model):
    labdoctors = models.ForeignKey(LabDoctors, null=True, blank=True, on_delete=models.PROTECT)
    blood_group = models.ForeignKey(UniversalBloodGroups, null=True, blank=True, on_delete=models.PROTECT)
    resume_upload = models.FileField(upload_to='lab_resume_uploads', null=True, blank=True)
    father_name = models.CharField(max_length=50, null=True, blank=True)
    marital_status = models.ForeignKey(UniversalMaritalStatus, null=True, blank=True, on_delete=models.PROTECT)
    date_of_joining = models.DateField(null=True, blank=True)
    address = models.CharField(max_length=300, null=True, blank=True)
    pin_code = models.IntegerField(null=True, blank=True)
    city = models.ForeignKey(City, null=True, blank=True, on_delete=models.PROTECT)
    state = models.ForeignKey(State, null=True, blank=True, on_delete=models.PROTECT)
    country = models.ForeignKey(Country, null=True, blank=True, on_delete=models.PROTECT)


class LabDoctorsIdentificationDetails(models.Model):
    labdoctors = models.ForeignKey(LabDoctors, null=True, blank=True, on_delete=models.PROTECT)
    bank_name = models.CharField(max_length=50, null=True, blank=True)
    bank_account_no = models.PositiveBigIntegerField(null=True, blank=True)
    bank_ifsc_code = models.CharField(max_length=30, null=True, blank=True)
    pf_account_no = models.CharField(max_length=30, null=True, blank=True)
    passport_no = models.CharField(max_length=30, null=True, blank=True)
    esi_account_no = models.CharField(max_length=30, null=True, blank=True)
    driving_license = models.CharField(max_length=30, null=True, blank=True)


class ReferralAmountForDoctor(models.Model):
    referral_doctor = models.ForeignKey(LabDoctors, on_delete=models.PROTECT)
    referral_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True)
    is_percentage = models.BooleanField(default=False)
    added_on = models.DateTimeField(auto_now_add=True, null=True)
    last_updated = models.DateTimeField(auto_now=True, null=True)
    lab_test = models.ForeignKey(LabGlobalTests, on_delete=models.PROTECT, null=True)

    def __str__(self):
        return f"{self.referral_doctor}-Rs.{self.referral_amount}"



class DefaultsForDepartments(models.Model):
    department=models.ForeignKey(LabDepartments, on_delete=models.PROTECT)
    doctor = models.ForeignKey(LabDoctors, on_delete=models.PROTECT,blank=True, null=True)
    lab_technician = models.ForeignKey(LabStaff, on_delete=models.PROTECT,blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


class DoctorSpecializations(models.Model):
    name = models.CharField(max_length=200)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Doctor Specialization"
        verbose_name_plural = "Doctor Specializations"

    def __str__(self):
        return self.name


class LabDoctorSalaryPayments(models.Model):
    doctor = models.ForeignKey(LabDoctors, on_delete=models.PROTECT, null=True, blank=True)
    payment_policy = models.ForeignKey(DoctorSalaryPaymentTypes, on_delete=models.PROTECT, null=True, blank=True)
    transaction_type = models.ForeignKey(DoctorTransactionTypes, on_delete=models.PROTECT, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_percentage = models.BooleanField(default=False)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


