from rest_framework import serializers
from pro_universal_data.models import ULabMenus, ULabStaffGender, ULabReportType, ULabPatientTitles, ULabPatientAction, \
    ULabPatientAttenderTitles, ULabTestStatus, ULabPaymentModeType, \
    ULabPatientAge, ULabPatientGender, PrintTemplateType, DashBoardOptions, DoctorSharedReport, \
    DepartmentFlowType, UserPermissions, TimeDurationTypes, ULabRelations, ULabFonts, ULabReportsGender, \
    UniversalVehicleTypes, \
    UniversalFuelTypes, MarketingVisitTypes, UniversalBloodGroups, UniversalMaritalStatus, LabEmploymentType, \
    MarketingVisitStatus, MarketingTargetTypes, MarketingTargetDurations, LabStaffAttendanceStatus, \
    MarketingPaymentType, SalaryPaymentModes, LeaveTypes, LeaveStatus, UniversalActionType, PrivilegeCardBenefits, \
    AvailabilityPeriod, ConsultationType, TimeCategory, SourcingLabType, DoctorSalaryPaymentTypes, \
    DoctorTransactionTypes, TaxType, PharmaItemOperationType, SupplierType, UniversalFoodIntake, UniversalDayTimePeriod, \
    UniversalAilments, PatientType


class ULabMenusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ULabMenus
        fields = '__all__'


class ULabPatientGenderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ULabPatientGender
        fields = '__all__'


class ULabReportsGenderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ULabReportsGender
        fields = '__all__'


class ULabStaffGenderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ULabStaffGender
        fields = '__all__'


class ULabPatientActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ULabPatientAction
        fields = '__all__'


class UniversalActionTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = UniversalActionType
        fields = '__all__'


class ConsultationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultationType
        fields = "__all__"


class ULabPatientTitlesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ULabPatientTitles
        fields = ['id', 'name']


class ULabReportTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ULabReportType
        fields = '__all__'


class ULabPatientAttenderTitlesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ULabPatientAttenderTitles
        fields = '__all__'


class ULabTestStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ULabTestStatus
        fields = '__all__'


class ULabPaymentModeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ULabPaymentModeType
        fields = '__all__'


class ULabPatientAgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ULabPatientAge
        fields = '__all__'


class PrivilegeCardBenefitsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivilegeCardBenefits
        fields = '__all__'


class AvailabilityPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailabilityPeriod
        fields = '__all__'


class ULabRelationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ULabRelations
        fields = '__all__'


class TimeDurationTypesSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeDurationTypes
        fields = '__all__'


class ULabFontsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ULabFonts
        fields = '__all__'


class SourcingLabTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourcingLabType
        fields = '__all__'



#third party apis
from rest_framework import serializers
from pro_universal_data.models import (MessagingServiceTypes, MessagingVendors, MessagingSendType,
                                       MessagingCategory, MessagingTemplates, MessagingFor, Tag)


class MessagingServiceTypesSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessagingServiceTypes
        fields = '__all__'


class MessagingVendorsSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessagingVendors
        fields = '__all__'


class MessagingSendTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessagingSendType
        fields = '__all__'


# class MessagingLogsSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = MessagingLogs
#         fields = '__all__'


class MessagingCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MessagingCategory
        fields = '__all__'


class MessagingTemplatesSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessagingTemplates
        fields = '__all__'


class MessagingForSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessagingFor
        fields = '__all__'


# class SendSMSDataSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = SendSMSData
#         fields = ['search_id', 'numbers', 'sms_template', 'messaging_send_type', 'client', 'from_date', 'to_date']


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'


class TemplateTagsGetSerializer(serializers.ModelSerializer):
    templates = serializers.SerializerMethodField()

    class Meta:
        model = Tag
        fields = '__all__'

    def get_templates(self, obj):
        return [template.name for template in obj.templates.all()]


# class SendAndSaveWhatsAppSMSDataSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = SendAndSaveWhatsAppSMSData
#         fields = ['search_id', 'numbers', 'mwa_template', 'messaging_send_type', 'client']


class InitiatePaymentSerializer(serializers.Serializer):
    # user_id = serializers.CharField()
    amount = serializers.FloatField()

    # orderId = serializers.CharField()

    class Meta:
        # fields = ['user_id', 'amount','orderId']
        fields = ['amount']


class PrintTemplateTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrintTemplateType
        fields = '__all__'


class DashBoardOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashBoardOptions
        fields = '__all__'


class DoctorSharedReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorSharedReport
        fields = "__all__"


class DepartmentFlowTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepartmentFlowType
        fields = "__all__"


class UserPermissionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPermissions
        fields = "__all__"


class UniversalVehicleTypesSerializer(serializers.ModelSerializer):
    class Meta:
        model = UniversalVehicleTypes
        fields = "__all__"


class UniversalFuelTypesSerializer(serializers.ModelSerializer):
    class Meta:
        model = UniversalFuelTypes
        fields = "__all__"


class MarketingVisitTypesSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketingVisitTypes
        fields = "__all__"


class MarketingVisitStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketingVisitStatus
        fields = "__all__"


class UniversalBloodGroupsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UniversalBloodGroups
        fields = "__all__"


class UniversalMaritalStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = UniversalMaritalStatus
        fields = "__all__"


class LabEmploymentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabEmploymentType
        fields = '__all__'


class MarketingTargetTypesSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketingTargetTypes
        fields = '__all__'


class MarketingTargetDurationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketingTargetDurations
        fields = '__all__'


class LabStaffAttendanceStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabStaffAttendanceStatus
        fields = '__all__'


class MarketingPaymentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketingPaymentType
        fields = '__all__'


class SalaryPaymentModesSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalaryPaymentModes
        fields = '__all__'


class LeaveTypesSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveTypes
        fields = '__all__'


class LeaveStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveStatus
        fields = '__all__'

class TimeCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeCategory
        fields = "__all__"

class DoctorSalaryPaymentTypesSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorSalaryPaymentTypes
        fields = "__all__"

class DoctorTransactionTypesSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorTransactionTypes
        fields = "__all__"


class TaxTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxType
        fields = '__all__'



class PharmaItemOperationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PharmaItemOperationType
        fields = '__all__'


class SupplierTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierType
        fields = '__all__'



class UniversalFoodIntakeSerializer(serializers.ModelSerializer):
    class Meta:
        model = UniversalFoodIntake
        fields = '__all__'



class UniversalDayTimePeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = UniversalDayTimePeriod
        fields = '__all__'



class UniversalAilmentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UniversalAilments
        fields = '__all__'

class PatientTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientType
        fields = '__all__'

