from rest_framework import serializers

from healtho_pro_user.models.business_models import BusinessAddresses

from healtho_pro_user.models.business_models import BusinessProfiles
from pro_laboratory.models.client_based_settings_models import LetterHeadSettings, BusinessDataStatus, \
    CopiedLabDepartmentsData, BusinessDiscountSettings, BusinessPaidAmountSettings, BusinessPNDTDetails, \
    PrintDueReports, PrintReportSettings, PNDTRegistrationNumber, BusinessMessageSettings, \
    BusinessReferralDoctorSettings, PrintTestReportSettings, LabStaffPrintSettings, \
    ClientWiseMessagingTemplates, OtherBusinessSettings, BusinessEmailDetails, BusinessControls, ReportFontSizes, \
    PharmacyPricingConfig
from pro_laboratory.models.doctors_models import LabDoctors
from pro_laboratory.serializers.global_serializers import LabDepartmentsSerializer
from pro_universal_data.serializers import ULabFontsSerializer


class LetterHeadSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LetterHeadSettings
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        b_id = BusinessProfiles.objects.get(organization_name=instance.client.name)

        representation['letterhead'] = b_id.b_letterhead

        default_font = representation.get('default_font')

        if default_font:
            representation['default_font'] = ULabFontsSerializer(instance.default_font).data

        return representation


class PrintTestReportSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrintTestReportSettings
        fields = '__all__'


class PrintReportSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrintReportSettings
        fields = '__all__'


class CopyBasicBusinessDataSerializer(serializers.Serializer):
    client_id = serializers.CharField()
    departments = serializers.ListField(
        child=serializers.CharField()
    )

    class Meta:
        fields = '__all__'


class BusinessDataStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessDataStatus
        fields = '__all__'


class CopiedLabDepartmentsDataSerializer(serializers.ModelSerializer):
    departments_list = serializers.ListField(
        child=serializers.CharField(), write_only=True
    )
    departments = LabDepartmentsSerializer(many=True, required=False)

    class Meta:
        model = CopiedLabDepartmentsData
        fields = '__all__'


class BusinessDiscountSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessDiscountSettings
        fields = "__all__"


class BusinessPaidAmountSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessPaidAmountSettings
        fields = "__all__"


class OtherBusinessSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OtherBusinessSettings
        fields = "__all__"


class LabDoctorsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabDoctors
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        foreign_keys = ['gender', 'department', 'specialization', 'branch']
        for fk in foreign_keys:
            fk_id = representation.get(fk)
            if fk_id is not None:
                fk_name = getattr(instance, f'{fk}_name', None)
                if fk_name is None:
                    fk_name = getattr(instance, fk).name
                representation[fk] = fk_name
        return representation


class PNDTRegistrationNumberSerializer(serializers.ModelSerializer):
    class Meta:
        model = PNDTRegistrationNumber
        fields = '__all__'


class BusinessAddressesAtPNDTSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessAddresses
        fields = '__all__'


class BusinessPNDTDetailsSerializer(serializers.ModelSerializer):
    default_pndt_doctors = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=LabDoctors.objects.all()
    )

    class Meta:
        model = BusinessPNDTDetails
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        default_pndt_doctors_ids = instance.default_pndt_doctors.values_list('id', flat=True)
        doctor_details = LabDoctors.objects.filter(id__in=default_pndt_doctors_ids)
        representation['default_pndt_doctors'] = LabDoctorsSerializer(doctor_details, many=True).data
        org = instance.b_id
        addresses = BusinessAddresses.objects.filter(b_id=instance.b_id)
        representation['addresses'] = BusinessAddressesAtPNDTSerializer(addresses, many=True).data if addresses else []
        representation['organization_name'] = org.organization_name
        return representation


class PrintDueReportsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrintDueReports
        fields = "__all__"


class BusinessMessageSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessMessageSettings
        fields = "__all__"


class BusinessReferralDoctorSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessReferralDoctorSettings
        fields = '__all__'


class LabStaffPrintSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabStaffPrintSettings
        fields = "__all__"



class ClientWiseMessagingTemplatesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientWiseMessagingTemplates
        fields = "__all__"


class BusinessEmailDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessEmailDetails
        fields = '__all__'


class BusinessControlsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessControls
        fields = '__all__'

class PharmacyPricingConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = PharmacyPricingConfig
        fields = '__all__'


class ReportFontSizesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportFontSizes
        fields = "__all__"

class GenerateQuotationSerializer(serializers.Serializer):
    test_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=True
    )
    package_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=True
    )
    printed_by = serializers.CharField()
    class Meta:
        fields = '__all__'