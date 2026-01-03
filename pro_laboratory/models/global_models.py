from datetime import timedelta

from django.db import models
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from healtho_pro_user.models.business_models import BusinessProfiles, BusinessAddresses
from healtho_pro_user.models.universal_models import City, State, Country
from healtho_pro_user.models.users_models import HealthOProUser
from pro_universal_data.models import ULabStaffGender, ULabMenus, ULabReportType, DepartmentFlowType, ULabReportsGender, \
    ULabPatientAge, UniversalBloodGroups, UniversalMaritalStatus, LabEmploymentType, \
    LabStaffAttendanceStatus, MarketingPaymentType, SalaryPaymentModes, LeaveTypes, LeaveStatus


class Methodology(models.Model):
    name = models.CharField(max_length=100)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class LabDepartments(models.Model):  # Radiology, Hematology
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    department_flow_type = models.ForeignKey(DepartmentFlowType, on_delete=models.PROTECT, blank=True, null=True)

    # added_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Lab Department"
        verbose_name_plural = "Lab Departments"

    def __str__(self):
        return self.name


class BodyParts(models.Model):
    name = models.CharField(max_length=250, unique=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.name}'


class LabGlobalTests(models.Model):
    name = models.CharField(max_length=250)
    display_name = models.CharField(max_length=250, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    short_code = models.CharField(max_length=250, null=True, blank=True)
    department = models.ForeignKey(LabDepartments, on_delete=models.PROTECT)
    inventory_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_active = models.BooleanField(default=True, blank=True, null=True)
    is_accreditation = models.BooleanField(default=False, blank=True, null=True)
    target_tat = models.DurationField(blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    sample = models.CharField(max_length=200, null=True, blank=True)
    sample_volume = models.CharField(max_length=200, null=True, blank=True)
    methodology = models.ForeignKey(Methodology, on_delete=models.CASCADE, null=True, blank=True)
    clinical_information = models.TextField(null=True, blank=True)
    is_authorization = models.BooleanField(default=False, blank=True, null=True)
    body_parts = models.ManyToManyField(BodyParts, blank=True)
    test_image = models.ImageField(upload_to='lab_tests_images/', null=True, blank=True)
    is_outsourcing = models.BooleanField(default=False, null=True, blank=True)
    expense_for_outsourcing = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    outsourcing_global_test_id = models.IntegerField(blank=True, null=True)
    sourcing_lab = models.ForeignKey('pro_laboratory.SourcingLabRegistration', on_delete=models.PROTECT, blank=True,
                                     null=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.sourcing_lab:
            if LabGlobalTests.objects.filter(name=self.name, sourcing_lab=self.sourcing_lab).exclude(
                    pk=self.pk).exists():
                raise ValidationError({"Error": "Test with same name and sourcing lab already exists!"})
            else:
                super().save(*args, **kwargs)
        else:
            if LabGlobalTests.objects.filter(name=self.name, sourcing_lab__isnull=True).exclude(pk=self.pk).exists():
                raise ValidationError({"Error": "Test with same name already exists!"})
            else:
                super().save(*args, **kwargs)


class LabDiscountType(models.Model):  # like schemes, staff
    name = models.CharField(max_length=100)
    number = models.DecimalField(max_digits=10, decimal_places=2)
    is_percentage = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name}({self.number})"


class LabStaffRole(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class LabDoctorRole(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class LabWorkingDays(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name}"


class LabShift(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name}"


class LabBranch(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name}"


class LabBloodGroup(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name}"


class LabMaritalStatus(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name}"


class LabStaff(models.Model):
    is_active = models.BooleanField(default=True)
    is_superadmin = models.BooleanField(default=False)
    added_on = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=100, null=True)
    mobile_number = models.CharField(max_length=15, null=True, unique=True)
    email = models.EmailField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    employement_type = models.ForeignKey(LabEmploymentType, null=True, blank=True, on_delete=models.PROTECT)
    gender = models.ForeignKey(ULabStaffGender, null=True, blank=True, on_delete=models.PROTECT)
    role = models.ForeignKey(LabStaffRole, null=True, blank=True, on_delete=models.PROTECT)
    department = models.ForeignKey(LabDepartments, null=True, blank=True, on_delete=models.PROTECT)
    shift = models.ForeignKey(LabShift, null=True, blank=True, on_delete=models.PROTECT)
    branch = models.ForeignKey(LabBranch, null=True, blank=True, on_delete=models.PROTECT)
    lab_working_days = models.ManyToManyField(LabWorkingDays, blank=True)
    is_login_access = models.BooleanField(default=False, null=True)
    signature = models.TextField(blank=True, null=True)
    profile_pic = models.TextField(blank=True, null=True)
    pro_user_id = models.ForeignKey(HealthOProUser, on_delete=models.PROTECT, blank=True, null=True)
    branches = models.ManyToManyField(BusinessAddresses,blank=True)

    def __str__(self):
        return self.name



class LabStaffPersonalDetails(models.Model):
    labstaff = models.ForeignKey(LabStaff, null=True, blank=True, on_delete=models.PROTECT)
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


class LabStaffIdentificationDetails(models.Model):
    labstaff = models.ForeignKey(LabStaff, null=True, blank=True, on_delete=models.PROTECT)
    bank_name = models.CharField(max_length=50, null=True, blank=True)
    salary_payment_mode = models.ForeignKey(SalaryPaymentModes, on_delete=models.PROTECT, null=True, blank=True)
    ac_holder_name = models.CharField(max_length=200, null=True, blank=True)
    bank_account_no = models.PositiveBigIntegerField(null=True, blank=True)
    bank_ifsc_code = models.CharField(max_length=30, null=True, blank=True)
    pf_account_no = models.CharField(max_length=30, null=True, blank=True)
    passport_no = models.CharField(max_length=30, null=True, blank=True)
    pan_card_no = models.CharField(max_length=30, null=True, blank=True)
    esi_account_no = models.CharField(max_length=30, null=True, blank=True)


class LabStaffJobDetails(models.Model):
    labstaff = models.ForeignKey(LabStaff, null=True, blank=True, on_delete=models.PROTECT)
    date_of_joining = models.DateField(null=True, blank=True)
    payment_type = models.ForeignKey(MarketingPaymentType, on_delete=models.PROTECT, null=True, blank=True)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    incentive_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    salary_deduction = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    extra_hours_pay = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    shift_start_time = models.TimeField(null=True, blank=True)
    shift_end_time = models.TimeField(null=True, blank=True)


class LabStaffPayRoll(models.Model):
    lab_staff = models.ForeignKey(LabStaff, null=True, blank=True, on_delete=models.PROTECT)
    payment_structure = models.ForeignKey(MarketingPaymentType, null=True, blank=True, on_delete=models.PROTECT)
    ctc = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    commission = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    incentive = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    special_allowance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    conveyance_allowance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    hra = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    overtime_payment = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)


class LabStaffAttendanceDetails(models.Model):
    lab_staff = models.ForeignKey(LabStaff, null=True, blank=True, on_delete=models.PROTECT)
    date = models.DateField(null=True, blank=True)
    check_in_time = models.DateTimeField(blank=True, null=True)
    check_in_lat = models.CharField(max_length=50, blank=True, null=True)
    check_in_lon = models.CharField(max_length=50, blank=True, null=True)
    check_in_address = models.CharField(max_length=500, blank=True, null=True)
    check_out_lat = models.CharField(max_length=50, blank=True, null=True)
    check_out_lon = models.CharField(max_length=50, blank=True, null=True)
    check_out_address = models.CharField(max_length=500, blank=True, null=True)
    check_out_time = models.DateTimeField(blank=True, null=True)
    total_worked_hours = models.DurationField(null=True, blank=True)
    attendance_status = models.ForeignKey(LabStaffAttendanceStatus, on_delete=models.PROTECT, null=True, blank=True)
    shift_start_time = models.TimeField(null=True, blank=True)
    shift_end_time = models.TimeField(null=True, blank=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.check_in_time and self.check_out_time:
            self.total_worked_hours = self.check_out_time - self.check_in_time
        if not self.shift_start_time or not self.shift_end_time:
            job_details = LabStaffJobDetails.objects.filter(labstaff=self.lab_staff).first()
            if job_details:
                self.shift_start_time = job_details.shift_start_time
                self.shift_end_time = job_details.shift_end_time

        super().save(*args, **kwargs)


class LabStaffLeaveRequest(models.Model):
    lab_staff = models.ForeignKey(LabStaff, on_delete=models.PROTECT, null=True, blank=True)
    leave_type = models.ForeignKey(LeaveTypes, on_delete=models.PROTECT, null=True, blank=True)
    from_date = models.DateField(null=True, blank=True)
    to_date = models.DateField(null=True, blank=True)
    no_of_days = models.IntegerField(null=True, blank=True)
    reason = models.CharField(max_length=1000, null=True, blank=True)
    attachments = models.TextField(blank=True, null=True)
    status = models.ForeignKey(LeaveStatus, on_delete=models.PROTECT, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_cancel = models.BooleanField(default=False)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


class LeavePolicy(models.Model):
    is_monthly = models.BooleanField(default=False)
    no_of_paid_leaves = models.IntegerField(null=True, blank=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


class LabReportsTemplates(models.Model):
    LabGlobalTestID = models.ForeignKey(LabGlobalTests, on_delete=models.PROTECT)
    name = models.CharField(max_length=150, unique=True)
    report_type = models.ForeignKey(ULabReportType, on_delete=models.PROTECT)
    is_default = models.BooleanField(default=False)
    department = models.ForeignKey(LabDepartments, on_delete=models.PROTECT, blank=True, null=True)
    default_technician_remarks = models.TextField(blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.department:
            self.department = self.LabGlobalTestID.department

        if self.is_default:
            # Set is_default=False for other templates of the same TemplateTypeID
            LabReportsTemplates.objects.filter(
                LabGlobalTestID=self.LabGlobalTestID
            ).exclude(
                id=self.id
            ).update(
                is_default=False
            )
        super(LabReportsTemplates, self).save(*args, **kwargs)

#
# class LabWordReportTemplatePageWiseContent(models.Model):
#     page_content = models.TextField(blank=True, null=True)


class LabWordReportTemplate(models.Model):
    LabReportsTemplate = models.ForeignKey(LabReportsTemplates, on_delete=models.PROTECT, null=True)
    # header = models.TextField(blank=True, null=True)
    report = models.TextField(blank=True)
    rtf_content = models.TextField(blank=True, null=True)
    # pages = models.ManyToManyField(LabWordReportTemplatePageWiseContent, blank=True)
    department = models.ForeignKey(LabDepartments, on_delete=models.PROTECT, blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Universal Word Template"
        verbose_name_plural = "Universal Word Template"

    def save(self, *args, **kwargs):
        try:
            if not self.department :
                self.department = self.LabReportsTemplate.department

            super().save(*args, **kwargs)
        except Exception as error:
            raise ValidationError({"Error":f"{error}"})


class LabFixedParametersReportTemplate(models.Model):  # LabReportsTemplates
    LabReportsTemplate = models.ForeignKey(LabReportsTemplates, on_delete=models.PROTECT, null=True)
    ordering = models.SmallIntegerField(null=True, blank=True)
    group = models.CharField(max_length=300, blank=True, null=True)
    method = models.CharField(max_length=300, blank=True, null=True)
    parameter = models.CharField(max_length=500)
    value = models.CharField(max_length=1000, blank=True, null=True)
    units = models.CharField(max_length=200, blank=True, null=True)
    formula = models.TextField(blank=True, null=True)
    mcode = models.CharField(max_length=100, blank=True, null=True)
    to_display = models.BooleanField(default=True)
    round_to_decimals = models.IntegerField(default=None, blank=True, null=True)
    referral_range = models.TextField(null=True, blank=True)
    normal_ranges_display = models.TextField(blank=True, null=True)
    department = models.ForeignKey(LabDepartments, on_delete=models.PROTECT, blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    is_value_only = models.BooleanField(default=False)
    is_value_bold = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, blank=True, null=True)

    def save(self, *args, **kwargs):
        try:
            if not self.department:
                self.department = self.LabReportsTemplate.department

            super().save(*args, **kwargs)
        except Exception as error:
            raise ValidationError({"Error":f"{error}"})


class LabFixedReportNormalReferralRanges(models.Model):
    parameter_id = models.ForeignKey(LabFixedParametersReportTemplate, on_delete=models.PROTECT, blank=True, null=True)
    gender = models.ForeignKey(ULabReportsGender, on_delete=models.PROTECT)
    age_min = models.IntegerField(blank=True, null=True)
    age_min_units = models.ForeignKey(ULabPatientAge, on_delete=models.PROTECT, blank=True, null=True,
                                      related_name='min_age_units')
    age_min_in_days = models.IntegerField(blank=True, null=True)
    age_max = models.IntegerField(blank=True, null=True)
    age_max_units = models.ForeignKey(ULabPatientAge, on_delete=models.PROTECT, blank=True, null=True,
                                      related_name='max_age_units')
    age_max_in_days = models.IntegerField(blank=True, null=True)
    value_min = models.CharField(max_length=20)
    value_max = models.CharField(max_length=20)
    added_on = models.DateTimeField(auto_now_add=True)



# Lab Packages
class LabGlobalPackages(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.CharField(max_length=500, blank=True, null=True)
    offer_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_discount = models.DecimalField(max_digits=10, decimal_places=2)
    is_disc_percentage = models.BooleanField(default=False)
    package_image = models.ImageField(upload_to='package_images/', null=True, blank=True)
    lab_tests = models.ManyToManyField(LabGlobalTests, blank=True)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(LabStaff, on_delete=models.PROTECT, null=True)
    last_updated = models.DateTimeField(auto_now=True)


class LabMenuAccess(models.Model):
    lab_menu = models.ManyToManyField(ULabMenus, blank=True)
    lab_staff = models.OneToOneField(LabStaff, on_delete=models.PROTECT)
    is_access = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


class LabStaffRolePermissions(models.Model):
    lab_staff_role = models.ForeignKey(LabStaffRole, on_delete=models.PROTECT)
    lab_menu_access_list = models.ManyToManyField(ULabMenus, blank=True)


class LabStaffLoginAccess(models.Model):
    lab_staff_id = models.OneToOneField(LabStaff, on_delete=models.PROTECT)
    is_login = models.BooleanField(default=False)
    last_login = models.DateTimeField(null=True, blank=True)
    last_active = models.DateTimeField(null=True, blank=True)


class DoctorAccess(models.Model):
    doctor = models.OneToOneField(HealthOProUser, on_delete=models.PROTECT)
    is_active = models.BooleanField(default=False)
    added_on = models.DateTimeField(auto_now_add=True)


class DefaultTestParameters(models.Model):
    parameter = models.CharField(max_length=500)
    LabGlobalTestId = models.ForeignKey(LabGlobalTests, on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.parameter


class LabStaffDefaultBranch(models.Model):
    lab_staff = models.OneToOneField(LabStaff, on_delete=models.PROTECT)
    default_branch = models.ManyToManyField(BusinessAddresses, blank=True)






















