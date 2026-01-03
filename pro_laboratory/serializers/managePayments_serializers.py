from pro_laboratory.models.patient_models import Patient, LabPatientInvoice, LabPatientTests
from rest_framework import serializers
from pro_laboratory.serializers.patient_serializers import LabPatientPackagesSerializer


class LabPatientTestsSerializer(serializers.ModelSerializer):
    status_id = serializers.SerializerMethodField()  # Use CharField for status name input

    def get_status_id(self, obj):
        return obj.status_id.name if obj.status_id else None

    class Meta:
        model = LabPatientTests
        fields = '__all__'


class LabPatientInvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabPatientInvoice
        fields = '__all__'


class PatientSerializer(serializers.ModelSerializer):
    lab_tests = serializers.SerializerMethodField()
    lab_packages = serializers.SerializerMethodField()
    patient_invoice = LabPatientInvoiceSerializer(source='labpatientinvoice')


    class Meta:
        model = Patient
        fields = ['id','name', 'title', 'age', 'gender','mobile_number', 'ULabPatientAge', 'lab_tests','mr_no','visit_id','visit_count','partner',
                  'referral_doctor','branch','referral_lab','created_by','added_on','lab_packages', 'patient_invoice']

    def get_lab_tests(self, obj):
        lab_tests = obj.labpatienttests_set.exclude(is_package_test=True)
        return [test.name for test in lab_tests]

    def get_lab_packages(self, obj):
        packages = obj.labpatientpackages_set.all()
        return  [package.name for package in packages]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['title'] = instance.title.name if instance.title else None
        representation['ULabPatientAge'] = instance.ULabPatientAge.name if instance.ULabPatientAge else None
        representation['gender'] = instance.gender.name if instance.gender else None
        representation['doctor_name'] = instance.referral_doctor.name if instance.referral_doctor else None
        representation['created_by'] = instance.created_by.name if instance.created_by else None
        representation['partner'] = f"{instance.partner.name}/ {instance.partner.company.name}" if instance.partner or instance.partner else None
        representation['referral_lab'] = instance.referral_lab.organization_name if instance.referral_lab else None
        return representation
