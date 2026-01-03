# from ckeditor.fields import RichTextField
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
from healtho_pro_user.models.universal_models import HealthcareRegistryType
from healtho_pro_user.models.users_models import Client, HealthOProUser


class ULabMenus(models.Model):
    label = models.CharField(max_length=100)
    ordering = models.PositiveIntegerField()
    icon = models.CharField(max_length=100, null=True, blank=True)
    link = models.CharField(max_length=200, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    health_care_registry_type = models.ForeignKey(HealthcareRegistryType, on_delete=models.PROTECT)

    def __str__(self):
        return self.label

    class Meta:
        ordering = ['ordering']


class UniversalLabDoctorsType(models.Model):  # Referral Doctor, Consultant Doctor
    name = models.CharField(max_length=200)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.name}'


class UniversalActionType(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name}'


@receiver(pre_save, sender=ULabMenus)
def update_custom_order(sender, instance, **kwargs):
    if not instance.ordering:
        # If custom_order is not set, set it to the maximum value + 1
        max_order = ULabMenus.objects.all().aggregate(models.Max('ordering'))['ordering__max']
        instance.custom_order = max_order + 1 if max_order is not None else 1


class ULabStaffGender(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name}"


class ULabPatientAction(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    action = models.CharField(max_length=100)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ULabPatientTitles(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ULabPatientAttenderTitles(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ULabPatientGender(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ULabReportsGender(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class SourcingLabType(models.Model):  # Fixed, Word
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name}"



class ULabReportType(models.Model):  # Fixed, Word
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name}"



## Pro Laboratory Models Start from here

class ULabTestStatus(models.Model):  # Pending, Processing, Completed
    name = models.CharField(max_length=50)
    added_on = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Universal Lab Test Status"
        verbose_name_plural = "Universal Lab Test Statuses"

    def __str__(self):
        return self.name


class ULabPaymentModeType(models.Model):  # Cash, UPI, Cheque, Net Banking
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Universal Lab Payment Mode Type"
        verbose_name_plural = "Universal Lab Payment Mode Types"

    def __str__(self):
        return self.name


class ULabMethodology(models.Model):
    name = models.CharField(max_length=100)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ULabFonts(models.Model):
    name = models.CharField(max_length=100)
    value = models.CharField(max_length=100, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ULabPatientAge(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=False)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}"


class PrivilegeCardBenefits(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True, unique=True)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}"


class AvailabilityPeriod(models.Model): #Specified period, Lifetime
    name = models.CharField(max_length=100, blank=True, null=True, unique=True)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}"


class PaymentFor(models.Model): #Tests, Dr. Consultation, Services, Rooms, Packages
    name = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


class PatientType(models.Model): # Lab, Out Patient, In Patient
    name = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)



class ULabRelations(models.Model):
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name}"


class TimeDurationTypes(models.Model):
    name = models.CharField(max_length=50)
    no_of_days = models.IntegerField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name}"


class MessagingServiceTypes(models.Model):  # SMS, WA, Notify, Email
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class MessagingVendors(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    tag = models.CharField(max_length=50)
    messaging_type = models.ForeignKey(MessagingServiceTypes, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class MessagingSendType(models.Model):  # staff, patients, doctors
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class MessagingCategory(models.Model):
    name = models.CharField(max_length=100)  # Assuming each category has a name

    def __str__(self):
        return self.name


class MessagingTemplates(models.Model):
    templateName = models.CharField(max_length=100)
    messaging_service_types = models.ForeignKey(MessagingServiceTypes, on_delete=models.CASCADE)
    templateContent = models.TextField()
    templateId = models.CharField(max_length=100)
    messaging_category = models.ForeignKey(MessagingCategory, on_delete=models.CASCADE)
    sender_id = models.CharField(max_length=10, default=None, blank=True, null=True)
    route = models.CharField(max_length=10, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.templateName

    class Meta:
        verbose_name_plural = "MessagingTemplates"


class MessagingFor(models.Model):  # OTP_login, Welcome
    name = models.CharField(max_length=100)
    messagingTemplate = models.ForeignKey(MessagingTemplates, on_delete=models.PROTECT)
    messaging_types = models.ForeignKey(MessagingServiceTypes, on_delete=models.PROTECT, default=None)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


# # Model used to Check/send the SMS  data and save it db
# class SendSMSData(models.Model):
#     sms_template = models.ForeignKey(MessagingTemplates, on_delete=models.PROTECT, blank=True, null=True)
#     search_id = models.CharField(max_length=100, blank=True, null=True)
#     numbers = models.CharField(max_length=100, blank=True, null=True)
#     messaging_send_type = models.ForeignKey(MessagingSendType, blank=True, null=True, on_delete=models.CASCADE)
#     message = models.TextField(blank=True, null=True)
#     sent_on = models.DateTimeField(auto_now_add=True, blank=True, null=True)
#     client = models.ForeignKey(Client, on_delete=models.PROTECT, null=True)
#     from_date = models.DateField(blank=True, null=True)
#     to_date = models.DateField(blank=True, null=True)
#
#     class Meta:
#         verbose_name_plural = "SendSMSData"
#
#
# class MessagingLogs(models.Model):
#     sms = models.ForeignKey(SendSMSData, on_delete=models.PROTECT, blank=True, null=True)
#     messaging_vendor = models.ForeignKey(MessagingVendors, on_delete=models.CASCADE)
#     response_code = models.IntegerField(blank=True, null=True)
#     status = models.CharField(max_length=255)
#     message = models.TextField()
#     businessid = models.CharField(max_length=100)
#     messaging_send_type = models.ForeignKey(MessagingSendType, on_delete=models.CASCADE)
#     numbers = models.CharField(max_length=255)
#     client = models.ForeignKey(Client, on_delete=models.PROTECT, null=True)
#     sent_on = models.DateTimeField(auto_now_add=True, blank=True, null=True)
#
#     class Meta:
#         verbose_name_plural = "MessagingLogs"


class PrintTemplateType(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Tag(models.Model):
    messaging_send_type = models.ForeignKey(MessagingSendType, on_delete=models.CASCADE)
    tag_name = models.CharField(max_length=50, blank=True, null=True, unique=True)
    tag_display_name = models.CharField(max_length=50, blank=True, null=True, unique=True)
    tag_formula = models.CharField(max_length=200, blank=True, null=True)
    is_collection = models.BooleanField(default=False)
    templates = models.ManyToManyField(PrintTemplateType, blank=True)

    def __str__(self):
        return f"{self.tag_name}"


# # Model used to Check/send the SMS  data and save it db
# class SendAndSaveWhatsAppSMSData(models.Model):
#     mwa_template = models.ForeignKey(MessagingTemplates, on_delete=models.PROTECT, blank=True, null=True)
#     search_id = models.CharField(max_length=100, blank=True, null=True)
#     numbers = models.CharField(max_length=100, blank=True, null=True)
#     messaging_send_type = models.ForeignKey(MessagingSendType, blank=True, null=True, on_delete=models.CASCADE)
#     message = models.TextField(blank=True, null=True)
#     client = models.ForeignKey(Client, on_delete=models.PROTECT, null=True)
#     sent_on = models.DateTimeField(auto_now_add=True, blank=True, null=True)
#
#     class Meta:
#         verbose_name_plural = "SendAndSaveWhatsAppSMSData"
#
#
# class WhatsAppMessagingLogs(models.Model):
#     sms = models.ForeignKey(SendAndSaveWhatsAppSMSData, on_delete=models.PROTECT, blank=True, null=True)
#     messaging_vendor = models.ForeignKey(MessagingVendors, on_delete=models.PROTECT)
#     response_code = models.IntegerField(blank=True, null=True)
#     status = models.CharField(max_length=300)
#     message = models.TextField()
#     businessid = models.CharField(max_length=100)
#     messaging_send_type = models.ForeignKey(MessagingSendType, on_delete=models.CASCADE)
#     numbers = models.CharField(max_length=255)
#     client = models.ForeignKey(Client, on_delete=models.PROTECT, null=True)
#     sent_on = models.DateTimeField(auto_now_add=True, blank=True, null=True)
#
#     class Meta:
#         verbose_name_plural = "WhatsAppMessagingLogs"
#

class DashBoardOptions(models.Model):
    name = models.CharField(max_length=500)
    is_active = models.BooleanField(default=True)
    graph_size = models.CharField(max_length=50)
    icon = models.CharField(max_length=100, null=True, blank=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.name}'


class DoctorSharedReport(models.Model):
    doctor = models.ForeignKey(HealthOProUser, on_delete=models.PROTECT)
    test = models.IntegerField()
    client = models.ForeignKey(Client, on_delete=models.PROTECT)
    added_on = models.DateTimeField(auto_now_add=True)


class DepartmentFlowType(models.Model):
    name = models.CharField(max_length=300)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.name}'


class UserPermissions(models.Model):
    name = models.CharField(max_length=100)
    ordering = models.PositiveIntegerField()
    description = models.CharField(max_length=1000, null=True)
    label = models.CharField(max_length=300, null=True)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.name}'

    class Meta:
        ordering = ['ordering']


class UniversalVehicleTypes(models.Model):  # Two wheeler, #Car
    name = models.CharField(max_length=100, null=True, blank=True)
    is_active = models.BooleanField(default=True, blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


class UniversalFuelTypes(models.Model):  # Petrol, Diesel
    name = models.CharField(max_length=100, null=True, blank=True)
    is_active = models.BooleanField(default=True, blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


class MarketingVisitTypes(models.Model):  # Doctor, Lab, Hospital
    name = models.CharField(max_length=100, null=True, blank=True)
    is_active = models.BooleanField(default=True, blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


class MarketingVisitStatus(models.Model):  # Pending, follow up, accepted, declined
    name = models.CharField(max_length=100, null=True, blank=True)
    is_active = models.BooleanField(default=True, blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


class UniversalBloodGroups(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name}"


class UniversalMaritalStatus(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name}"


class LabEmploymentType(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name}"


class MarketingPaymentType(models.Model):  # CTC/Commission
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name}'


class MarketingTargetTypes(models.Model):  # Revenue/No.of Referrals
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name}'


class MarketingTargetDurations(models.Model):  # Daily/Weekly/Monthly
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name}'


class LabStaffAttendanceStatus(models.Model):  # Present/Absent/On-Leave/Half-Day
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name}'


class SalaryPaymentModes(models.Model):  # Cash/UPI/Net Banking/Check
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name}'


class LeaveTypes(models.Model):  # Paid/Sick/Unpaid
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name}'


class LeaveStatus(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name}'

#
# class Dummy(models.Model):
#     name=models.CharField(max_length=200)

class ConsultationType(models.Model):
    name = models.CharField(max_length=100)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.name}'

class TimeCategory(models.Model): # Days, Hours
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.name}'

class DoctorSalaryPaymentTypes(models.Model): # PerPatient/ Salary
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

class DoctorTransactionTypes(models.Model): #consultation/tests/services
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


class PharmaItemOperationType(models.Model): # Sale/Consume
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

class TaxType(models.Model): # GST/IGST
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


class SupplierType(models.Model): #manufacturer/ Vendor
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


class UniversalAilments(models.Model): #Fever/Cold etc
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


class UniversalDayTimePeriod(models.Model):  # morning, afternoon etc
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)



class UniversalFoodIntake(models.Model):  # before lunch, after lunch etc
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)