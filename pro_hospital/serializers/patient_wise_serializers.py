from datetime import datetime
from decimal import Decimal

from rest_framework import serializers
from pro_hospital.models.patient_wise_models import PatientDoctorConsultationDetails, \
    PatientServices, IPRoomBooking, PatientVitals
from pro_hospital.models.prescription_models import PatientPrescription
from pro_hospital.serializers.universal_serializers import DoctorConsultationDetailsForPatientsSerializer


class PatientDoctorConsultationDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientDoctorConsultationDetails
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        case_type = instance.case_type
        created_by = instance.created_by

        representation['consultation'] = DoctorConsultationDetailsForPatientsSerializer(instance.consultation).data if instance.consultation else None

        representation['case_type']={"id": case_type.id, "name":case_type.name} if case_type else None

        representation['status_id'] = {"id":instance.status_id.id, "name":instance.status_id.name} if instance.status_id else ""

        representation['created_by'] = {"id": created_by.id, "name": created_by.name} if created_by else None

        representation['prescription'] = PatientPrescription.objects.filter(doctor_consultation=instance).exists()

        return representation


class PatientServicesSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientServices
        fields = "__all__"


class IPRoomBookingGetSerializer(serializers.ModelSerializer):
    class Meta:
        model = IPRoomBooking
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        representation['time_category'] = {"id": instance.time_category.id,
                                        "name": instance.time_category.name} if instance.time_category else None
        representation['floor'] = {"id": instance.floor.id,
                                           "name": instance.floor.name} if instance.floor else None

        representation['room_type'] = {"id": instance.room_type.id, "name": instance.room_type.name} if instance.room_type else None
        representation['created_by'] = {"id": instance.created_by.id,
                                       "name": instance.created_by.name} if instance.created_by else None
        total_price = calculate_room_charges(instance.admitted_date, instance.vacated_date, instance.time_category, instance.charges_per_bed)
        representation['total_price'] = f"{Decimal(total_price):.2f}"

        if instance.admitted_date:
            vacated_date = instance.vacated_date or datetime.now()
            delta = vacated_date - instance.admitted_date
            if delta.days > 0:
                turnaround_time = f"{delta.days} days, {delta.seconds // 3600} hours, {(delta.seconds % 3600) // 60} minutes"
            elif delta.seconds >= 3600:
                turnaround_time = f"{delta.seconds // 3600} hours, {(delta.seconds % 3600) // 60} minutes"
            else:
                turnaround_time = f"{delta.seconds // 60} minutes"

            representation['turn_around_time'] = turnaround_time
        else:
            representation['turn_around_time'] = None

        return representation


class PatientVitalsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientVitals
        fields = '__all__'


def calculate_room_charges(admitted_date, vacated_date, time_category, charges_per_bed):
    if not (admitted_date and time_category and charges_per_bed):
        return Decimal(0)

    vacated_date = vacated_date or datetime.now()
    delta = vacated_date - admitted_date
    if time_category.name.lower() == "day":
        total_days = delta.days + (1 if delta.seconds > 0 else 0)  # Add 1 day if there are leftover seconds
        return total_days * charges_per_bed
    elif time_category.name.lower() == "hour":
        total_hours = delta.days * 24 + delta.seconds // 3600
        print(delta.seconds, 'seconds')
        print(total_hours, 'total hours')
        if delta.seconds % 3600 > 0:  # Add 1 hour if there are leftover seconds or minutes
            total_hours += 1
            print(total_hours, 'hours')
        return total_hours * charges_per_bed
    return Decimal(0)