from django.contrib import admin
from healtho_pro_user.models.business_models import BusinessTimings, BusinessWorkingDays
from pro_laboratory.models.doctors_models import LabDoctorsPersonalDetails, LabDoctorsIdentificationDetails, \
    ReferralAmountForDoctor
from pro_laboratory.models.machine_integration_models import ProcessingMachine
from pro_laboratory.models.patient_appointment_models import AppointmentDetails
from pro_laboratory.models.phlebotomists_models import LabPhlebotomist
from pro_laboratory.models.global_models import LabStaff, Methodology, LabFixedParametersReportTemplate, \
    LabReportsTemplates, LabBloodGroup, LabMaritalStatus, \
    LabEmploymentType, ULabStaffGender, LabDoctorRole, LabBranch, LabShift, LabStaffIdentificationDetails, \
    LabStaffPersonalDetails, \
    LabWorkingDays, LabStaffRole, LabMenuAccess, LabGlobalTests, \
    LabWorkingDays, LabStaffRole, LabGlobalTests, LabDepartments
from pro_laboratory.models.patient_models import Patient, LabPatientInvoice, LabPatientTests, LabDoctors, \
    LabPatientReceipts
from pro_laboratory.models.universal_models import TpaUltrasound, TpaUltrasoundConfig, TpaUltrasoundImages, \
    ActivityLogs
from pro_universal_data.models import Tag
from pro_laboratory.models.labtechnicians_models import LabTechnicians, LabPatientFixedReportTemplate

admin.site.register(LabTechnicians)
admin.site.register(LabStaff)
admin.site.register(LabFixedParametersReportTemplate)
admin.site.register(LabPatientFixedReportTemplate)
admin.site.register(Patient)
admin.site.register(LabPatientInvoice)
admin.site.register(LabPatientReceipts)
admin.site.register(LabPatientTests)
admin.site.register(LabDoctors)
admin.site.register(AppointmentDetails)
admin.site.register(LabPhlebotomist)
admin.site.register(Methodology)
admin.site.register(LabReportsTemplates)
admin.site.register(LabBloodGroup)
admin.site.register(LabMaritalStatus)
admin.site.register(LabStaffPersonalDetails)
admin.site.register(LabStaffIdentificationDetails)
admin.site.register(LabDoctorsPersonalDetails)
admin.site.register(LabDoctorsIdentificationDetails)
admin.site.register(LabEmploymentType)
admin.site.register(LabWorkingDays)
admin.site.register(LabShift)
admin.site.register(LabBranch)
admin.site.register(LabDoctorRole)
admin.site.register(ULabStaffGender)
admin.site.register(LabStaffRole)
admin.site.register(LabMenuAccess)
admin.site.register(BusinessWorkingDays)
admin.site.register(BusinessTimings)
admin.site.register(LabGlobalTests)
admin.site.register(TpaUltrasoundConfig)
admin.site.register(TpaUltrasound)
admin.site.register(LabDepartments)
admin.site.register(ReferralAmountForDoctor)
admin.site.register(ProcessingMachine)

class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'client', 'operation', 'url', 'response_code', 'duration')
    list_filter = ('client', 'operation', 'response_code')


admin.site.register(ActivityLogs, ActivityLogAdmin)
