from rest_framework import serializers

from pro_hospital.models.patient_wise_models import PatientDoctorConsultationDetails
from pro_hospital.models.prescription_models import PatientPrescription, VitalsInPrescription, \
    InvestigationsInPrescription, MedicinesInPrescription
from pro_laboratory.models.lab_appointment_of_patient_models import LabAppointmentForPatient
from pro_laboratory.serializers.global_serializers import LabGlobalTestsSerializer
from pro_laboratory.serializers.managePayments_serializers import PatientSerializer
from pro_laboratory.serializers.patient_serializers import LabAppointmentsSerializer
from pro_pharmacy.models import PharmaItems
from pro_universal_data.models import ULabTestStatus
from pro_universal_data.serializers import UniversalAilmentsSerializer, UniversalDayTimePeriodSerializer, \
    UniversalFoodIntakeSerializer


class VitalsInPrescriptionSerializer(serializers.ModelSerializer):
    prescription = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = VitalsInPrescription
        fields = "__all__"

class InvestigationsInGetPrescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvestigationsInPrescription
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        if instance.tests:
            representation['tests'] = LabGlobalTestsSerializer(instance.tests, many=True).data
        if instance.packages:
            representation['packages'] = LabGlobalTestsSerializer(instance.packages, many=True).data

        return representation


class InvestigationsInPrescriptionSerializer(serializers.ModelSerializer):
    prescription = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = InvestigationsInPrescription
        fields = "__all__"

class MedicinesInPrescriptionSerializer(serializers.ModelSerializer):
    prescription = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = MedicinesInPrescription
        fields = "__all__"

class PatientPrescriptionSerializer(serializers.ModelSerializer):
    vitals = VitalsInPrescriptionSerializer(write_only=True)
    investigations = InvestigationsInPrescriptionSerializer(write_only=True)
    medicines = MedicinesInPrescriptionSerializer(write_only=True, many=True)
    class Meta:
        model = PatientPrescription
        fields = "__all__"


    def create(self, validated_data):
        vitals_data = validated_data.pop('vitals', None)
        investigations_data = validated_data.pop('investigations', [])
        medicines_data = validated_data.pop('medicines', [])

        ailments = validated_data.pop('ailments', None)

        # Create the package
        prescription = PatientPrescription.objects.create(**validated_data)
        if prescription.doctor_consultation:
            prescription.doctor_consultation.status_id = ULabTestStatus.objects.get(id=3)
            prescription.doctor_consultation.save()
        if ailments:
            prescription.ailments.set(ailments)

        if vitals_data:
            VitalsInPrescription.objects.create(prescription=prescription, **vitals_data)

        # Handle investigations
        if investigations_data:
            investigation = InvestigationsInPrescription.objects.create(prescription=prescription)
            if 'tests' in investigations_data:
                investigation.tests.set(investigations_data['tests'])
            if 'packages' in investigations_data:
                investigation.packages.set(investigations_data['packages'])

        # Handle medicines
        if medicines_data:
            for medicine_data in medicines_data:
                intake_time = medicine_data.pop('in_take_time', [])
                medicine_in_prescription = MedicinesInPrescription.objects.create(prescription=prescription, **medicine_data)
                medicine_in_prescription.in_take_time.set(intake_time)

        return prescription

    def update(self, instance, validated_data):
        vitals_data = validated_data.pop('vitals', None)
        investigations_data = validated_data.pop('investigations', [])
        medicines_data = validated_data.pop('medicines', [])
        ailments = validated_data.pop('ailments', [])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if ailments:
            instance.ailments.set(ailments)

        if vitals_data:
            vitals = VitalsInPrescription.objects.filter(prescription=instance).first()

            if vitals:
                for attr, value in vitals_data.items():
                    setattr(vitals, attr, value)
                vitals.save()
            else:
                VitalsInPrescription.objects.create(prescription=instance,
                                                    **vitals_data)

        if investigations_data:
            investigations = InvestigationsInPrescription.objects.filter(prescription=instance).first()

            if investigations:
                investigations.tests.set(investigations_data['tests'])
                investigations.packages.set(investigations_data['packages'])

            else:
                investigations = InvestigationsInPrescription.objects.create(prescription=instance)
                investigations.tests.set(investigations_data['tests'])
                investigations.packages.set(investigations_data['packages'])

        if medicines_data:
            medicines = MedicinesInPrescription.objects.filter(prescription=instance)
            medicines.delete()

            for medicine_data in medicines_data:
                in_take_time = medicine_data.pop('in_take_time')
                medicine_in_prescription = MedicinesInPrescription.objects.create(prescription=instance, **medicine_data)
                medicine_in_prescription.in_take_time.set(in_take_time)

        return instance


    def to_representation(self, instance):
        representation = super().to_representation(instance)

        if instance.ailments:
            representation['ailments'] = UniversalAilmentsSerializer(instance.ailments, many=True).data

        vitals = VitalsInPrescription.objects.filter(prescription=instance).first()

        investigations = InvestigationsInPrescription.objects.filter(prescription=instance).first()

        medicines = MedicinesInPrescription.objects.filter(prescription=instance)

        representation['vitals'] = VitalsInPrescriptionSerializer(vitals).data if vitals else None

        representation['investigations'] = InvestigationsInGetPrescriptionSerializer(investigations).data if investigations else None

        representation['medicines'] = MedicinesInPrescriptionGetSerializer(medicines, many=True).data if medicines else []

        return representation


class MedicinesInPrescriptionGetSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicinesInPrescription
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        if instance.medicine:
            representation['medicine'] = PharmaItemsForPrescriptionSerializer(instance.medicine).data

        if instance.in_take_time.all():
            representation['in_take_time'] = UniversalDayTimePeriodSerializer(instance.in_take_time.all(), many=True).data

        if instance.when_to_take:
            representation['when_to_take'] = UniversalFoodIntakeSerializer(instance.when_to_take).data

        return representation



class PharmaItemsForPrescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PharmaItems
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        foreign_key_fields = ['category']
        for field in foreign_key_fields:
            field_instance = getattr(instance, field)
            if field_instance:
                representation[field] = str(field_instance)

        return representation


class GeneratePatientPrescriptionSerializer(serializers.Serializer):
    patient_id = serializers.CharField()
    doctor_consultation = serializers.CharField()

    class Meta:
        fields = '__all__'

class GetPatientPrescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientPrescription
        fields = '__all__'

class GetPatientDoctorConsultationsSerializer(serializers.ModelSerializer):
    patient = PatientSerializer()
    class Meta:
        model = PatientDoctorConsultationDetails
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        appointments = LabAppointmentForPatient.objects.filter(patient=instance.patient)
        patient_prescription = PatientPrescription.objects.filter(doctor_consultation=instance, patient=instance.patient)

        representation['patient_prescription'] = True if patient_prescription else False
        representation['consultation'] = {
            "id": getattr(instance.consultation.labdoctors, 'id', None),
            "name": getattr(instance.consultation.labdoctors, 'name', None),
            "department": getattr(instance.consultation.labdoctors.department, 'name', None)
        }
        representation['case_type'] = instance.case_type.name if instance.case_type else None
        representation['appointment'] = LabAppointmentsSerializer(appointments, many=True).data if appointments else None
        representation['status_id'] = instance.status_id.name if instance.status_id else None
        return representation
