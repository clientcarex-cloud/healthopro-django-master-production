from datetime import datetime

from rest_framework import serializers

from pro_laboratory.models.doctors_models import LabDoctors
from pro_laboratory.models.global_models import LabFixedReportNormalReferralRanges
from pro_laboratory.models.labtechnicians_models import LabTechnicians, LabTechnicianRemarks, \
    LabPatientWordReportTemplate, LabPatientFixedReportTemplate
from pro_laboratory.models.patient_models import LabPatientTests, Patient
from pro_laboratory.models.phlebotomists_models import LabPhlebotomist
from pro_laboratory.serializers.global_serializers import LabFixedReportNormalReferralRangesSerializer
from pro_laboratory.serializers.phlebotomists_serializers import LabPhlebotomistSerializer


class PatientSerializer(serializers.ModelSerializer):
    total_due = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = "__all__"

    def get_total_due(self, obj):
        return obj.labpatientinvoice.total_due
    def get_total_price(self, obj):
        return obj.labpatientinvoice.total_price
        
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['gender'] = instance.gender.name if instance.gender else None
        representation['ULabPatientAge'] = instance.ULabPatientAge.name if instance.ULabPatientAge else None
        representation['title'] = instance.title.name if instance.title else None
        representation['created_by'] = instance.created_by.name if instance.created_by else None

        referral_doctor_id = representation.get('referral_doctor')
        representation['referral_doctor_id'] = referral_doctor_id
        if referral_doctor_id is not None:
            referral_doctor_name = instance.referral_doctor.name
            representation['referral_doctor'] = referral_doctor_name
        return representation


class LabPatientTestsSerializer(serializers.ModelSerializer):
    patient = PatientSerializer()

    class Meta:
        model = LabPatientTests
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['department'] = instance.department.name if instance.department else None
        representation['status_id'] = instance.status_id.name if instance.status_id else None
        return representation


class LabTechnicianRemarksSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabTechnicianRemarks
        fields = '__all__'


class LabTechnicianSerializer(serializers.ModelSerializer):
    lab_technician_remarks = LabTechnicianRemarksSerializer(required=False)

    class Meta:
        model = LabTechnicians
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        lab_technician_remark = LabTechnicianRemarks.objects.filter(LabPatientTestID=instance.LabPatientTestID).first()
        representation['consulting_doctor'] = {"id": instance.consulting_doctor.id,
                                               "name": instance.consulting_doctor.name
                                               } if instance.consulting_doctor else None
        if lab_technician_remark:
            representation['lab_technician_remarks'] = LabTechnicianRemarksSerializer(lab_technician_remark).data
        return representation


class LabTechnicianListSerializer(serializers.ModelSerializer):
    LabPatientTestID = LabPatientTestsSerializer()
    phlebotomist = serializers.SerializerMethodField()
    lab_technician_remarks = serializers.SerializerMethodField()

    class Meta:
        model = LabTechnicians
        fields = '__all__'

    def get_lab_technician_remarks(self, instance):
        try:
            lab_technician_remarks_instance = LabTechnicianRemarks.objects.filter(
                LabPatientTestID=instance.LabPatientTestID).first()
            serializer = LabTechnicianRemarksSerializer(instance=lab_technician_remarks_instance)
            return serializer.data
        except LabTechnicianRemarks.DoesNotExist:
            return None

    def get_phlebotomist(self, instance):
        try:
            lab_phlebotomist_instance = LabPhlebotomist.objects.get(LabPatientTestID=instance.LabPatientTestID)
            serializer = LabPhlebotomistSerializer(instance=lab_phlebotomist_instance)
            return serializer.data
        except LabPhlebotomist.DoesNotExist:
            return None


# class LabPatientWordReportTemplatePageWiseContentSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = LabPatientWordReportTemplatePageWiseContent
#         fields = "__all__"


class LabPatientWordReportTemplateSerializer(serializers.ModelSerializer):
    # pages = LabPatientWordReportTemplatePageWiseContentSerializer(many=True)
    header = serializers.CharField(read_only=True)
    rtf_content_header = serializers.CharField(read_only=True)
    signature_content = serializers.CharField(read_only=True)

    class Meta:
        model = LabPatientWordReportTemplate
        fields = '__all__'


class LabPatientFixedReportTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabPatientFixedReportTemplate
        fields = '__all__'


    def get_age_in_days_for_patient(self, patient=None):
        patient_age_in_days = 0
        patient_age = patient.age
        patient_age_units = patient.ULabPatientAge.name

        if patient_age_units == "Days":
            patient_age_in_days = patient_age
        elif patient_age_units == "Months":
            patient_age_in_days = patient_age * 30
        elif patient_age_units == "Years":
            patient_age_in_days = patient_age * 365
        elif patient_age_units == "DOB":
            today = datetime.now().date()
            patient_age_in_days = (today-patient.dob).days

        return patient_age_in_days

    def get_normal_range_for_patient(self, patient_gender=None, patient_age_in_days=None, parameter=None):
        genders_to_check = ["Both", f"{patient_gender}"]
        normal_ranges = LabFixedReportNormalReferralRanges.objects.filter(parameter_id=parameter,
                                                                          gender__name__in=genders_to_check,
                                                                          age_min_in_days__lte=patient_age_in_days,
                                                                          age_max_in_days__gte=patient_age_in_days
                                                                          )

        normal_range = normal_ranges.first() if normal_ranges else None

        return normal_range

    def to_representation(self, instance):
        fixed_parameter = instance.template
        representation = super().to_representation(instance)
        representation['normal_ranges'] = None
        patient =instance.LabPatientTestID.patient
        patient_gender = patient.gender.name
        patient_age_in_days = self.get_age_in_days_for_patient(patient=patient)
        normal_range = self.get_normal_range_for_patient(patient_gender=patient_gender, patient_age_in_days=patient_age_in_days, parameter=instance.template)

        representation['normal_ranges'] = LabFixedReportNormalReferralRangesSerializer(normal_range).data if normal_range else None
        representation['to_display'] = fixed_parameter.to_display
        representation['round_to_decimals'] = fixed_parameter.round_to_decimals

        return representation


class LabPatientTestFixedReportGenerationSerializer(serializers.Serializer):
    lab_patient_test_id = serializers.IntegerField()

    class Meta:
        fields = ['lab_patient_test_id']


class LabPatientTestReportGenerationSerializer(serializers.Serializer):
    lab_patient_test_id = serializers.IntegerField()
    created_by = serializers.IntegerField(required=False)
    template_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        fields = ['lab_patient_test_id', 'created_by','template_id']


class LabPatientTestWordReportGenerationSerializer(serializers.Serializer):
    lab_patient_test_id = serializers.IntegerField()

    class Meta:
        fields = ['lab_patient_test_id']


class LabPatientTestFixedReportDeletionSerializer(serializers.Serializer):
    lab_patient_test_id = serializers.IntegerField()

    class Meta:
        fields = ['lab_patient_test_id']


class LabTechniciansAnalyticsSerializer(serializers.ModelSerializer):
    total_received = serializers.IntegerField()
    total_draft_reports = serializers.IntegerField()
    total_authorization_pending = serializers.IntegerField()
    total_completed = serializers.IntegerField()
    report_created_by_name = serializers.CharField()

    class Meta:
        model = LabTechnicians
        fields = ['total_received', 'report_created_by_name', 'total_draft_reports', 'total_authorization_pending',
                  'total_completed']



class ReferralDoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabDoctors
        fields = ['id', 'name', 'mobile_number']


class LabPatientTestWordReportDeletionSerializer(serializers.Serializer):
    lab_patient_test_id = serializers.IntegerField()

    class Meta:
        fields = ['lab_patient_test_id']
