from django.db import connection
from rest_framework import serializers

from healtho_pro_user.models.users_models import Client
from interoperability.models import LabTpaSecretKeys
from pro_laboratory.models.doctors_models import LabDoctors
from pro_laboratory.models.global_models import LabStaff, LabGlobalTests, LabGlobalPackages
from pro_laboratory.models.patient_models import LabPatientReceipts
from pro_laboratory.models.phlebotomists_models import LabPhlebotomist
from pro_laboratory.models.universal_models import TpaUltrasoundConfig, TpaUltrasound, TpaUltrasoundImages, \
    PrintTemplate, PrintDataTemplate, ActivityLogs, ChangesInModels, DashBoardSettings
from pro_laboratory.serializers.patient_serializers import LabPatientPaymentsSerializer
from pro_laboratory.serializers.sourcing_lab_serializers import SourcingLabRegistrationSerializer


class GenerateBarcodePDFSerializer(serializers.Serializer):
    sample_id = serializers.CharField(required=False)
    mr_no = serializers.CharField(required=False)
    phlebotomist_id = serializers.CharField(required=False)
    date_time = serializers.CharField(required=False)

    class Meta:
        fields = '__all__'


# class GenerateBarcodePDFTrailSerializer(serializers.Serializer):
#     phlebotomist = serializers.ListField(child=serializers.PrimaryKeyRelatedField(queryset=LabPhlebotomist.objects.all()))
#
#
#     class Meta:
#         fields = '__all__'
class GenerateBarcodePDFTrailSerializer(serializers.Serializer):
    phlebotomist = serializers.PrimaryKeyRelatedField(queryset=LabPhlebotomist.objects.all())


    class Meta:
        fields = '__all__'


class GeneratePatientInvoiceSerializer(serializers.Serializer):
    patient_id = serializers.CharField()
    client_id = serializers.CharField()
    printed_by = serializers.CharField()

    class Meta:
        fields = '__all__'


class GetPrivilegeCardSerializer(serializers.Serializer):
    client_id = serializers.CharField()
    membership_id = serializers.CharField()

    class Meta:
        fields = '__all__'


class GeneratePatientReceiptSerializer(serializers.Serializer):
    patient_id = serializers.CharField()
    client_id = serializers.CharField()
    receipt_id = serializers.CharField(required=False)
    template_type = serializers.CharField(required=False)
    printed_by = serializers.CharField()

    class Meta:
        fields = '__all__'




class GeneratePatientTestReportSerializer(serializers.Serializer):
    patient_id = serializers.CharField()
    client_id = serializers.CharField()
    test_ids = serializers.ListField(child=serializers.IntegerField(), required=False)

    class Meta:
        fields = '__all__'


class GenerateTestReportSerializer(serializers.Serializer):
    test_id = serializers.CharField()
    client_id = serializers.CharField()
    printed_by = serializers.CharField()
    pdf = serializers.BooleanField(default=False)
    lh = serializers.BooleanField(default=False)


    class Meta:
        fields = '__all__'


class GenerateReceiptSerializer(serializers.ModelSerializer):
    client_id = serializers.CharField()
    payments = LabPatientPaymentsSerializer(many=True)


    class Meta:
        model = LabPatientReceipts
        fields = ['patient', 'remarks', 'discount_type', 'discount_amt', 'created_by', 'payments','payment_for',
                  'client_id']


class TpaUltrasoundConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = TpaUltrasoundConfig
        fields = '__all__'


class TpaUltrasoundImagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = TpaUltrasoundImages
        fields = '__all__'


class TpaUltrasoundSerializer(serializers.ModelSerializer):
    images = TpaUltrasoundImagesSerializer(many=True, required=False)  # have to check whether this is necessary or not

    class Meta:
        model = TpaUltrasound
        fields = '__all__'


# class MachineIntegrationSerializer(serializers.ModelSerializer):
#     secret_key=serializers.CharField(required=False, write_only=True)
#     class Meta:
#         model = MachineIntegrationModel
#         fields = '__all__'


class TpaUltrasoundIntegrationSerializer(serializers.ModelSerializer):
    images = TpaUltrasoundImagesSerializer(many=True, required=False)
    images_data = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False, allow_null=True, allow_empty=True
    )
    secret_key = serializers.CharField(max_length=200, allow_blank=True, allow_null=True)
    client = serializers.CharField(max_length=200, allow_blank=True, allow_null=True)

    class Meta:
        model = TpaUltrasound
        fields = ['secret_key', 'client', 'date', 'main_folder', 'sub_folder', 'xml_data', 'meta_info',
                  'images',
                  'images_data']

    def create(self, validated_data):
        try:
            lab_tpa_secret_key = None
            client_name = validated_data.pop('client', None)
            secret_key = validated_data.pop('secret_key', None)

            # Check if the secret key exists in LabTpaSecretKeys
            try:
                lab_tpa_secret_key = LabTpaSecretKeys.objects.get(secret_key=secret_key, is_active=True)

            except LabTpaSecretKeys.DoesNotExist:
                error = f"Matching Secret Key not found"
                raise serializers.ValidationError(error)

            if lab_tpa_secret_key:
                images = validated_data.pop('images_data', [])

                client = Client.objects.get(name=client_name)
                connection.set_schema(client.schema_name)
                tpa_ultrasound_instance = TpaUltrasound.objects.create(**validated_data)

                if images:
                    for image in images:
                        image_instance = TpaUltrasoundImages.objects.create(image=image)
                        tpa_ultrasound_instance.images.add(image_instance)

                return tpa_ultrasound_instance

        except Exception as error:
            raise serializers.ValidationError(error)


class TpaUltrasoundMetaInfoListViewSerializer(serializers.ModelSerializer):
    images = TpaUltrasoundImagesSerializer(many=True, required=False)

    class Meta:
        model = TpaUltrasound
        fields = ['id', 'date', 'images', 'meta_info', 'added_on']


class PrintReceptionistReportSerializer(serializers.Serializer):
    lab_staff = serializers.PrimaryKeyRelatedField(queryset=LabStaff.objects.all(), required=False, allow_null=True)
    start_date = serializers.DateField(required=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all(), required=True)

    class Meta:
        fields = '__all__'


class ReferralDoctorReportSerializer(serializers.Serializer):
    doctor_id = serializers.PrimaryKeyRelatedField(queryset=LabDoctors.objects.all(), required=True)
    start_date = serializers.DateField(required=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all(), required=True)

    class Meta:
        fields = '__all__'


class PrintTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrintTemplate
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        if 'print_template_type' in representation:
            representation['print_template_type'] = {
                'id': representation['print_template_type'],
                'name': instance.print_template_type.name if instance.print_template_type else None
            }
        return representation


class PrintDataTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrintDataTemplate
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        if 'print_template' in representation:
            representation['print_template'] = {
                'id': representation['print_template'],
                'name': instance.print_template.name if instance.print_template else None
            }
        return representation


class ChangesInModelsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChangesInModels
        fields = '__all__'


class ActivityLogsSerializer(serializers.ModelSerializer):
    changes = ChangesInModelsSerializer(many=True)

    class Meta:
        model = ActivityLogs
        fields = '__all__'


class GeneratePatientRefundSerializer(serializers.Serializer):
    patient_id = serializers.CharField()
    client_id = serializers.CharField()
    printed_by = serializers.CharField()
    refund_id = serializers.CharField()

    class Meta:
        fields = '__all__'

#
class DashBoardSettingsSerializer(serializers.ModelSerializer):
    graph_size=serializers.CharField(required=False)
    class Meta:
        model = DashBoardSettings
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        dash_board_id = representation.get('dash_board')
        if dash_board_id is not None:
            dash_board = instance.dash_board
            representation['dash_board'] = dash_board.name
            representation['icon'] = dash_board.icon
        return representation


class DoctorSharedTestReportSerializer(serializers.Serializer):
    test_id = serializers.CharField()
    client_id = serializers.CharField()
    doctor = serializers.CharField()

    class Meta:
        fields = '__all__'


class GeneratePatientMedicalCertificateSerializer(serializers.Serializer):
    patient_id = serializers.IntegerField()
    client_id = serializers.IntegerField()

    class Meta:
        fields = '__all__'



class ConvertStringToHTMLSerializer(serializers.Serializer):
    html_string = serializers.CharField()

    class Meta:
        fields = '__all__'


