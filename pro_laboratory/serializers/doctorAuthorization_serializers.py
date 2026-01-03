from rest_framework import serializers
from pro_laboratory.models.doctorAuthorization_models import LabDrAuthorization, LabDrAuthorizationRemarks
from pro_laboratory.models.labtechnicians_models import LabTechnicians
from pro_laboratory.models.patient_models import Patient, LabPatientTests
from pro_laboratory.serializers.labtechnicians_serializers import LabTechnicianRemarksSerializer
from pro_universal_data.models import ULabTestStatus


class LabDrAuthorizationRemarksSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabDrAuthorizationRemarks
        fields = '__all__'


class LabDrAuthorizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabDrAuthorization
        fields = "__all__"

    def create(self, validated_data):
        lab_patient_test = validated_data.get('LabPatientTestID')
        is_authorized = validated_data.get('is_authorized')
        obj=LabDrAuthorization.objects.create(**validated_data)

        if is_authorized:
            completed_status = ULabTestStatus.objects.get(id=3)
            lab_patient_test.status_id = completed_status
            lab_patient_test.save()
        return obj


class LabTechnicianSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabTechnicians
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        report_created_by_id = representation.get('report_created_by')

        if report_created_by_id is not None:
            report_created_by_name = instance.report_created_by.name
            representation['report_created_by'] = report_created_by_name
        return representation


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        foreign_keys = ['gender', 'ULabPatientAge', 'title']
        for fk in foreign_keys:
            fk_id = representation.get(fk)
            if fk_id is not None:
                fk_name = getattr(instance, f'{fk}_name', None)
                if fk_name is None:
                    fk_name = getattr(instance, fk).name
                representation[fk] = fk_name

        created_by_id = representation.get('created_by')
        if created_by_id is not None:
            created_by_name = instance.created_by.name
            representation['created_by'] = created_by_name
        return representation


class LabPatientTestsSerializer(serializers.ModelSerializer):
    lab_dr_authorization = LabDrAuthorizationSerializer(many=True)
    lab_dr_authorization_remarks = LabDrAuthorizationRemarksSerializer(many=True)
    patient = PatientSerializer()
    labtechnician = serializers.SerializerMethodField()
    lab_technician_remarks = serializers.SerializerMethodField()

    class Meta:
        model = LabPatientTests
        fields = '__all__'

    def get_labtechnician(self, instance):
        technicians = instance.labtechnician.all()
        if technicians:
            technician = technicians[0]
            technician_serializer = LabTechnicianSerializer(technician)
            return technician_serializer.data
        else:
            return None
    def get_lab_technician_remarks(self, instance):
        remarks = instance.lab_technician_remarks.all()
        if remarks:
            remark = remarks[0]
            technician_remark_serializer = LabTechnicianRemarksSerializer(remark)
            return technician_remark_serializer.data
        else:
            return None

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        foreign_keys = ['department', 'status_id']
        for fk in foreign_keys:
            fk_id = representation.get(fk)
            if fk_id is not None:
                fk_name = getattr(instance, f'{fk}_name', None)
                if fk_name is None:
                    fk_name = getattr(instance, fk).name
                representation[fk] = fk_name
        return representation


class AuthorizationAnalyticsSerializer(serializers.Serializer):
    added_by = serializers.CharField()
    total_authorization_pending = serializers.IntegerField()
    total_authorized_completed = serializers.IntegerField()
