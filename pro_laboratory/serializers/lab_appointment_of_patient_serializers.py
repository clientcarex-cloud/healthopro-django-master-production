from datetime import datetime
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.response import Response
from healtho_pro_user.models.users_models import Client
from pro_hospital.models.universal_models import GlobalServices, DoctorConsultationDetails
from pro_hospital.serializers.universal_serializers import GlobalServicesSerializer, DoctorConsultationDetailsSerializer
from pro_laboratory.models.client_based_settings_models import BusinessControls
from pro_laboratory.models.doctors_models import LabDoctors
from pro_laboratory.models.global_models import LabStaffDefaultBranch
from pro_laboratory.models.lab_appointment_of_patient_models import LabAppointmentForPatient
from pro_laboratory.models.patient_models import HomeService, LabPatientPackages
from pro_laboratory.serializers.doctors_serializers import LabDoctorsSerializer, ReferralDoctorCountSerializer
from pro_laboratory.serializers.global_serializers import LabGlobalTestsSerializer, LabGlobalPackagesSerializer
from pro_laboratory.serializers.patient_serializers import HomeServiceSerializer, LabTestSerializer, \
    LabPatientPaymentsSerializer, LabPatientPackagesSerializer, logger
from pro_universal_data.models import ULabTestStatus




class LabAppointmentForPatientSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all(), required=False)
    home_service = HomeServiceSerializer(required=False)
    lab_tests = serializers.ListField(child=serializers.IntegerField(), required=False)
    lab_packages = serializers.ListField(child=serializers.IntegerField(), required=False)
    services = serializers.PrimaryKeyRelatedField(queryset=GlobalServices.objects.all(), many=True, required=False)


    tests = LabGlobalTestsSerializer(many=True, read_only=True)
    packages = LabGlobalPackagesSerializer(many=True, read_only=True)


    referral_doctor = serializers.PrimaryKeyRelatedField(
        queryset=LabDoctors.objects.all(),
        required=False
    )
    consulting_doctor = serializers.PrimaryKeyRelatedField(
        queryset=LabDoctors.objects.all(),
        required=False
    )
    case_type = serializers.PrimaryKeyRelatedField(queryset=DoctorConsultationDetails.objects.all(), many=True, required=False)


    class Meta:
        model = LabAppointmentForPatient
        fields = '__all__'

    def create(self, validated_data):
        with transaction.atomic():
            try:
                home_service_data = validated_data.pop('home_service', None)
                lab_tests_data = validated_data.pop('lab_tests', [])
                client = validated_data.pop('client', None)
                lab_packages_data = validated_data.pop('lab_packages', [])
                consultation_details = validated_data.pop('case_type', [])
                services_data = validated_data.pop('services', [])
                name = validated_data.get('name')
                mobile_number = validated_data.get('mobile_number')
                appointment_date=validated_data.get('appointment_date')
                appointment_time=validated_data.get('appointment_time')
                today = timezone.now().date()

                controls = BusinessControls.objects.first()
                if controls and controls.multiple_branches:
                    created_by = validated_data['created_by']
                    default_branch_obj = LabStaffDefaultBranch.objects.get(lab_staff=created_by)
                    default_branch = default_branch_obj.default_branch.all()

                    if default_branch.count() == 1:
                        validated_data['branch'] = default_branch.first()
                    elif default_branch.count() > 1:
                        error_message = f"Please select only One branch, to continue to Patient Registration!"
                        raise serializers.ValidationError({"Error": error_message})
                    else:
                        error_message = f"Please select a branch, to continue to Patient Registration!"
                        raise serializers.ValidationError({"Error": error_message})

                appointments = LabAppointmentForPatient.objects.filter(added_on__date__gte=today,
                                                  added_on__date__lt=today + timezone.timedelta(days=1))
                appointments_count = appointments.count() + 1
                current_date = datetime.now().strftime('%y%m%d')

                appointment_no = f'{current_date}-{appointments_count}'

                validated_data['appointment_no'] = appointment_no
                validated_data['client'] = client
                validated_data['last_updated_by'] = validated_data['created_by']

                booked_appointment = LabAppointmentForPatient.objects.create(**validated_data)

                if home_service_data:
                    pass
                    # HomeService.objects.create(patient=patient, **home_service_data)

                if lab_packages_data:
                    booked_appointment.packages.set(lab_packages_data)

                if lab_tests_data:
                    booked_appointment.tests.set(lab_tests_data)
                if consultation_details:
                    booked_appointment.doctor_consultation.set(consultation_details)
                if services_data:
                    booked_appointment.services.set(services_data)

                return booked_appointment

            except Exception as error:
                logger.error(f"Unexpected error creating patient: {error}", exc_info=True)
                raise serializers.ValidationError(error)

    def update(self, instance, validated_data):
        with transaction.atomic():
            try:
                lab_tests_data = validated_data.pop('lab_tests', [])
                lab_packages_data = validated_data.pop('lab_packages', [])
                consultation_details = validated_data.pop('case_type', [])
                services_data = validated_data.pop('services', [])
                instance = super().update(instance, validated_data)

                if lab_tests_data:
                    for lab_test_data in lab_tests_data:
                        instance.tests.add(lab_test_data)
                if lab_packages_data:
                    for lab_package_data in lab_packages_data:
                        instance.packages.add(lab_package_data)

                if consultation_details:
                    for consultation in consultation_details:
                        instance.doctor_consultation.add(consultation)
                if services_data:
                    for service in services_data:
                        instance.services.add(service)

                return instance
            except Exception as e:
                logger.error(f"Unexpected error updating patient: {e}", exc_info=True)
                return Response({"Error": f"An unexpected error occurred: {e}"})

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        title_id = representation.get('title')
        if title_id is not None:
            title_name = instance.title.name
            representation['title'] = title_name

        created_by_id = representation.get('created_by')
        if created_by_id is not None:
            created_by_name = instance.created_by.name
            representation['created_by'] = created_by_name

        referral_doctor = representation.get('referral_doctor')
        if referral_doctor is not None:
            representation['referral_doctor'] = ReferralDoctorCountSerializer(instance.referral_doctor).data


        consulting_doctor = representation.get('consulting_doctor')
        if consulting_doctor is not None:
            consultations = DoctorConsultationDetails.objects.filter(labdoctors=consulting_doctor)
            representation['consulting_doctor'] = {"id": instance.consulting_doctor.id, "name": instance.consulting_doctor.name,
                                                   "lab_doctors_consultation_details":DoctorConsultationDetailsSerializer(consultations, many=True).data if consultations else []}

        services = instance.services.all()
        if services:
            representation['services'] = GlobalServicesSerializer(services, many=True).data
        consultations = instance.doctor_consultation.all()
        if consultations:
            representation['consultation_details'] = DoctorConsultationDetailsSerializer(consultations, many=True).data

        return representation

