from django.db import transaction
from rest_framework import serializers
from pro_laboratory.models.labtechnicians_models import LabTechnicians
from pro_laboratory.models.patient_models import Patient, LabPatientTests
from pro_laboratory.models.phlebotomists_models import LabPhlebotomist
from pro_laboratory.models.sourcing_lab_models import SourcingLabRegistration
from pro_laboratory.serializers.sourcing_lab_serializers import SourcingLabRegistrationSerializer
from pro_universal_data.models import ULabTestStatus


class LabPhlebotomistSerializer(serializers.ModelSerializer):
    added_on = serializers.SerializerMethodField()

    class Meta:
        model = LabPhlebotomist
        fields = "__all__"

    def get_added_on(self, obj):
        return obj.added_on.strftime('%d-%m-%Y, %I:%M %p')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        received_by_id = representation.get('received_by')
        if received_by_id is not None:
            received_by_name = instance.received_by.name
            representation['received_by'] = received_by_name

        collected_by_id = representation.get('collected_by')
        if collected_by_id is not None:
            collected_by_name = instance.collected_by.name
            representation['collected_by'] = collected_by_name

        return representation


class PatientSerializer(serializers.ModelSerializer):
    sourcing_lab = SourcingLabRegistrationSerializer(read_only=True)

    class Meta:
        model = Patient
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        foreign_keys = ['gender', 'ULabPatientAge', 'title', 'created_by']
        for fk in foreign_keys:
            fk_id = representation.get(fk)
            if fk_id is not None:
                fk_name = getattr(instance, f'{fk}_name', None)
                if fk_name is None:
                    fk_name = getattr(instance, fk).name
                representation[fk] = fk_name
        return representation


class LabPatientTestsSerializer(serializers.ModelSerializer):
    patient = PatientSerializer()
    phlebotomist = LabPhlebotomistSerializer()
    sourcing_lab = SourcingLabRegistrationSerializer(read_only=True)

    class Meta:
        model = LabPatientTests
        fields = '__all__'

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


class LabPhlebotomistAnalyticsSerializer(serializers.Serializer):
    collected_by = serializers.CharField()
    total_collected = serializers.IntegerField()
    total_pending = serializers.IntegerField()


class LabTestsSerializer(serializers.ModelSerializer):
    sample_type = serializers.SerializerMethodField()
    phlebotomist = LabPhlebotomistSerializer()
    class Meta:
        model = LabPatientTests
        fields = ['id', 'name', 'short_code', 'price', 'discount',
            'price_after_discount', 'is_authorization',
            'is_package_test', 'added_on', 'is_outsourcing',
            'LabGlobalTestId', 'status_id', 'department', 'sample_type', 'phlebotomist'
        ]

    def get_sample_type(self,obj):
        return obj.LabGlobalTestId.sample if obj.LabGlobalTestId.sample else None

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        related_fields = ['status_id', 'department']
        representation.update({
            field: getattr(getattr(instance, field, None), 'name', None) for field in related_fields
        })
        return representation


class PatientTestSerializer(serializers.ModelSerializer):
    sourcing_lab = serializers.SerializerMethodField()
    tests = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = [
            'id', 'name', 'age', 'dob', 'attender_name',
            'mobile_number', 'email', 'area', 'address',
            'prescription_attach', 'mr_no', 'visit_id',
            'added_on', 'visit_count', 'is_sourcing_lab',
            'title', 'ULabPatientAge', 'gender', 'referral_doctor',
            'attender_relationship_title', 'department',
            'created_by', 'last_updated_by', 'client', 'tests',
            'privilege_membership', 'sourcing_lab'
        ]

    def get_tests(self, obj):
        departments_details = self.context['request'].query_params.get('departments', [])
        departments = [department.strip() for department in departments_details.split(',') if department.strip()]

        lab_tests = LabPatientTests.objects.filter(patient=obj)

        if departments:
            lab_tests = lab_tests.filter(department__id__in=departments)
        tests = LabTestsSerializer(lab_tests, many=True).data
        return tests


    def get_sourcing_lab(self, obj):
        lab_tests = LabPatientTests.objects.filter(patient=obj)
        sourcing_labs = lab_tests.filter(is_outsourcing=True).values_list('sourcing_lab', flat=True)
        if sourcing_labs.exists():
            sourcing_lab_objects = SourcingLabRegistration.objects.filter(id__in=sourcing_labs)
            return SourcingLabRegistrationSerializer(sourcing_lab_objects, many=True).data
        return None

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        related_fields = ['gender', 'ULabPatientAge', 'title', 'created_by']
        representation.update({
            field: getattr(getattr(instance, field, None), 'name', None) for field in related_fields
        })
        return representation




class LabPatientTestsGetSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabPatientTests
        fields = ['id', 'name', 'short_code', 'status_id', 'department', 'price', 'discount', 'price_after_discount']

class PatientGetSerializer(serializers.ModelSerializer):
    tests = serializers.SerializerMethodField()
    phlebotomist = serializers.SerializerMethodField()
    sourcing_lab = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = '__all__'

    def get_tests(self, patient):
        tests = LabPatientTests.objects.filter(patient=patient)
        grouped_tests = {}
        for test in tests:
            sample_type = test.LabGlobalTestId.sample
            if sample_type not in grouped_tests:
                grouped_tests[sample_type] = []
            grouped_tests[sample_type].append(LabPatientTestsGetSerializer(test).data)
        return grouped_tests

    def get_phlebotomist(self, obj):
        lab_tests = LabPatientTests.objects.filter(patient=obj)
        phlebotomist_data = LabPhlebotomist.objects.filter(LabPatientTestID__in=lab_tests)
        if phlebotomist_data.exists():
            return LabPhlebotomistSerializer(phlebotomist_data, many=True).data
        return None

    def get_sourcing_lab(self, obj):
        lab_tests = LabPatientTests.objects.filter(patient=obj)
        sourcing_labs = lab_tests.filter(is_outsourcing=True).values_list('sourcing_lab', flat=True)
        if sourcing_labs.exists():
            sourcing_lab_objects = SourcingLabRegistration.objects.filter(id__in=sourcing_labs)
            return SourcingLabRegistrationSerializer(sourcing_lab_objects, many=True).data
        return None

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        related_fields = ['gender', 'ULabPatientAge', 'title', 'created_by']
        representation.update({
            field: getattr(getattr(instance, field, None), 'name', None) for field in related_fields
        })
        return representation


class PatientListSerializer(serializers.ModelSerializer):

    class Meta:
        model = Patient
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        foreign_keys = ['gender', 'ULabPatientAge', 'title', 'created_by']
        for fk in foreign_keys:
            fk_id = representation.get(fk)
            if fk_id is not None:
                fk_name = getattr(instance, f'{fk}_name', None)
                if fk_name is None:
                    fk_name = getattr(instance, fk).name
                representation[fk] = fk_name
        return representation