from datetime import datetime, timedelta

from django.db.models import Sum
from rest_framework.response import Response

from healtho_pro_user.models.universal_models import ProDoctor
from healtho_pro_user.models.users_models import HealthOProUser
from healtho_pro_user.serializers.users_serializers import UserSerializer, ProDoctorSerializer
from pro_hospital.models.universal_models import DoctorConsultationDetails
from pro_hospital.serializers.universal_serializers import DoctorConsultationDetailsSerializer
from pro_laboratory.models.doctors_models import LabDoctors, LabDoctorsType, LabDoctorsPersonalDetails, \
    LabDoctorsIdentificationDetails, ReferralAmountForDoctor, DefaultsForDepartments, DoctorSpecializations, \
    LabDoctorSalaryPayments
from rest_framework import serializers

from pro_laboratory.models.global_models import LabWorkingDays, LabGlobalTests
from pro_laboratory.models.lab_appointment_of_patient_models import LabAppointmentForPatient
from pro_laboratory.models.patient_models import Patient, LabPatientInvoice
from django.contrib.auth import get_user_model

User = get_user_model()


class LabDoctorsTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabDoctorsType
        fields = '__all__'


class LabDoctorsPersonalDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabDoctorsPersonalDetails
        fields = '__all__'


class LabDoctorsIdentificationDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabDoctorsIdentificationDetails
        fields = '__all__'

class LabDoctorSalaryPaymentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabDoctorSalaryPayments
        fields = '__all__'

class LabDoctorsSerializer(serializers.ModelSerializer):
    lab_working_days = serializers.PrimaryKeyRelatedField(queryset=LabWorkingDays.objects.all(), many=True,
                                                          required=False)
    lab_doctors_personal_details = LabDoctorsPersonalDetailsSerializer(required=False)
    lab_doctors_identification_details = LabDoctorsIdentificationDetailsSerializer(required=False)
    lab_doctors_consultation_details = DoctorConsultationDetailsSerializer(required=False, many=True)
    salary_details = LabDoctorSalaryPaymentsSerializer(required=False, many=True)

    class Meta:
        model = LabDoctors
        fields = '__all__'

    def create(self, validated_data):
        lab_working_days_data = validated_data.pop('lab_working_days', [])
        lab_doctors_personal_details_data = validated_data.pop('lab_doctors_personal_details', None)
        lab_doctors_identification_details_data = validated_data.pop('lab_doctors_identification_details', None)
        lab_doctors_consultation_details_data = validated_data.pop('lab_doctors_consultation_details', [])
        salary_details_data = validated_data.pop('salary_details',[])

        labdoctors = LabDoctors.objects.create(**validated_data)

        for day in lab_working_days_data:
            labdoctors.lab_working_days.add(day)

        if lab_doctors_personal_details_data:
            LabDoctorsPersonalDetails.objects.create(labdoctors=labdoctors, **lab_doctors_personal_details_data)

        if lab_doctors_identification_details_data:
            LabDoctorsIdentificationDetails.objects.create(labdoctors=labdoctors,
                                                           **lab_doctors_identification_details_data)
        if lab_doctors_consultation_details_data:
            for fee_data in lab_doctors_consultation_details_data:
                DoctorConsultationDetails.objects.create(labdoctors=labdoctors, **fee_data)

        if salary_details_data:
            for data in salary_details_data:
                LabDoctorSalaryPayments.objects.create(doctor=labdoctors, **data)

        return labdoctors

    def update(self, instance, validated_data):
        salary_details_data = validated_data.pop('salary_details', [])
        lab_working_days_data = validated_data.pop('lab_working_days', [])
        lab_doctors_consultation_details_data = validated_data.pop('lab_doctors_consultation_details', [])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        for day in lab_working_days_data:
            instance.lab_working_days.add(day)

        if lab_doctors_consultation_details_data:
            for fee_data in lab_doctors_consultation_details_data:
                if fee_data.get('id'):
                    obj = DoctorConsultationDetails.objects.get(id=fee_data.get('id'))
                    obj.case_type=fee_data['case_type']
                    obj.is_online=fee_data['is_online']
                    obj.consultation_fee = fee_data['consultation_fee']
                    obj.is_active = fee_data['is_active']
                    obj.last_updated_by = fee_data['last_updated_by']
                    obj.save()
                else:
                    obj, created = DoctorConsultationDetails.objects.get_or_create(labdoctors=instance,
                                                                                   case_type=fee_data['case_type'],
                                                                                   is_online=fee_data['is_online'])
                    obj.consultation_fee = fee_data['consultation_fee']
                    obj.save()
        if salary_details_data:
            for data in salary_details_data:
                LabDoctorSalaryPayments.objects.create(doctor=instance, **data)

        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['gender'] = instance.gender.name if instance.gender else None
        representation['department'] = instance.department.name if instance.department else None
        representation['specialization'] = instance.specialization.name if instance.specialization else None

        marketing_executive = instance.marketing_executive

        if marketing_executive:
            representation['marketing_executive'] = {"id":marketing_executive.id,"name":marketing_executive.name}

        personal_details_data = instance.labdoctorspersonaldetails_set.first()
        identification_details_data = instance.labdoctorsidentificationdetails_set.first()
        consultation_fee_data = DoctorConsultationDetails.objects.filter(labdoctors=instance)

        if personal_details_data:
            representation['lab_doctors_personal_details'] = LabDoctorsPersonalDetailsSerializer(
                personal_details_data).data
        if identification_details_data:
            representation['lab_doctors_identification_details'] = LabDoctorsIdentificationDetailsSerializer(
                identification_details_data).data

        if consultation_fee_data:
            representation['lab_doctors_consultation_details'] = DoctorConsultationDetailsSerializer(consultation_fee_data, many=True).data
        else:
            representation['lab_doctors_consultation_details'] = None

        return representation


class SearchLabDoctorsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabDoctors
        fields = ['id', 'name']


class ConsultingDoctorCountSerializer(serializers.ModelSerializer):
    reports_signed_count = serializers.SerializerMethodField()
    appointments_count = serializers.SerializerMethodField()

    class Meta:
        model = LabDoctors
        fields = "__all__"

    def get_reports_signed_count(self, obj):
        request = self.context.get('request')
        date = request.query_params.get('date')
        start_date = request.query_params.get('date_range_after')
        end_date = request.query_params.get('date_range_before')

        if date:
            date = datetime.strptime(date, "%Y-%m-%d")

            return Patient.objects.filter(
                labpatienttests__labtechnician__consulting_doctor=obj,
                labpatienttests__labtechnician__last_updated__date=date
            ).count()

        if start_date and end_date:
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
            end_date = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
            return Patient.objects.filter(
                labpatienttests__labtechnician__consulting_doctor=obj,
                labpatienttests__labtechnician__last_updated__range=[start_date, end_date]
            ).count()
        else:
            return Patient.objects.filter(labpatienttests__labtechnician__consulting_doctor=obj).count()

    def get_appointments_count(self, obj):
        request = self.context.get('request')
        date = request.query_params.get('date')
        start_date = request.query_params.get('date_range_after')
        end_date = request.query_params.get('date_range_before')
        appointments = LabAppointmentForPatient.objects.filter(consulting_doctor=obj,is_cancelled=False)

        if date:
            appointments=appointments.filter(appointment_date=date)
        if start_date and end_date:
            appointments=appointments.filter(appointment_date__range=[start_date, end_date])
        elif start_date:
            appointments=appointments.filter(appointment_date__gte=start_date)
        return appointments.count()


    def to_representation(self, instance):
        representation = super().to_representation(instance)
        consultation_fee_data = DoctorConsultationDetails.objects.filter(labdoctors=instance)
        representation['gender'] = instance.gender.name if instance.gender else None
        representation['department'] = instance.department.name if instance.department else None
        representation['specialization'] = instance.specialization.name if instance.specialization else None
        representation['branch'] = instance.branch.name if instance.branch else None
        representation['lab_doctors_consultation_details'] = DoctorConsultationDetailsSerializer(consultation_fee_data,
                                                                                                 many=True).data if consultation_fee_data else None
        return representation


class ReferralDoctorCountSerializer(serializers.ModelSerializer):
    total_patients = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()
    last_patient_date = serializers.DateTimeField(read_only=True)

    class Meta:
        model = LabDoctors
        fields = "__all__"

    def get_total_patients(self, obj):
        date = self.context.get('date')
        date_range_after = self.context.get('date_range_after')
        date_range_before = self.context.get('date_range_before')
        patients =  Patient.objects.filter(referral_doctor=obj)
        if date:
            patients = patients.filter(added_on_date=date)
        if date_range_after and date_range_before:
            try:
                start_date = datetime.strptime(date_range_after, "%Y-%m-%d")
                end_date = datetime.strptime(date_range_before, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
                patients = patients.filter(added_on__range=[start_date, end_date])
            except ValueError:
                pass
        return patients.count()

    def get_total_paid(self, obj):
        total_paid = LabPatientInvoice.objects.filter(patient__referral_doctor=obj).aggregate(
            total_paid=Sum('total_paid')).get('total_paid', 0)
        return total_paid if total_paid is not None else 0

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['gender'] = instance.gender.name if instance.gender else None
        representation['department'] = instance.department.name if instance.department else None
        representation['specialization'] = instance.specialization.name if instance.specialization else None
        representation['branch'] = instance.branch.name if instance.branch else None
        marketing_executive = instance.marketing_executive
        if marketing_executive:
            representation['marketing_executive'] = {"id": marketing_executive.id, "name": marketing_executive.name}
        return representation



class PatientWiseLabReferralDoctorsSerializer(serializers.ModelSerializer):
    total_patients = serializers.CharField(read_only=True)
    total_paid = serializers.CharField(read_only=True)

    class Meta:
        model = LabDoctors
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['gender'] = instance.gender.name if instance.gender else None
        representation['department'] = instance.department.name if instance.department else None
        representation['specialization'] = instance.specialization.name if instance.specialization else None
        representation['branch'] = instance.branch.name if instance.branch else None

        marketing_executive = instance.marketing_executive

        if marketing_executive:
            representation['marketing_executive'] = {"id": marketing_executive.id, "name": marketing_executive.name}

        return representation


class ReferralAmountForDoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferralAmountForDoctor
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        lab_test_id = representation.pop('lab_test')
        if lab_test_id:
            lab_test = LabGlobalTests.objects.get(pk=lab_test_id)
            lab_test_data = {
                "id": lab_test.id,
                "name": lab_test.name,
                "price": lab_test.price,
                "department": lab_test.department.name

            }
            representation['lab_test'] = lab_test_data
        else:
            representation['lab_test'] = None
        return representation


class SyncDataForReferralDoctorSerializer(serializers.Serializer):
    source_doctor_id = serializers.IntegerField()
    target_doctor_id = serializers.IntegerField()


class ReferralDoctorsMergingSerializer(serializers.Serializer):
    main_doctor_id = serializers.IntegerField()
    duplicate_doctor_ids = serializers.ListField(child=serializers.IntegerField())


class LabtestForReferralDoctorSerializer(serializers.Serializer):
    lab_test = serializers.IntegerField()
    referral_amount = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_percentage = serializers.BooleanField(default=False)


class ReferralDoctorBulkEditSerializer(serializers.Serializer):
    referral_doctor = serializers.PrimaryKeyRelatedField(queryset=LabDoctors.objects.all())
    lab_tests_data = LabtestForReferralDoctorSerializer(many=True)


class SearchForMatchingDoctorsSerializer(serializers.ModelSerializer):
    pro_doctor = serializers.SerializerMethodField()

    # doctor = UserSerializer

    class Meta:
        model = User
        fields = ["id", "phone_number", "user_type", "country", "city", "state",
                  "HealthcareRegistryType", "full_name", "latitude", "longitude", "pro_doctor"]

    def get_pro_doctor(self, obj):
        try:
            pro_doctor = ProDoctor.objects.get(pro_user_id=obj.id)
            return ProDoctorSerializer(pro_doctor).data
        except ProDoctor.DoesNotExist:
            return None


class DoctorSpecializationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorSpecializations
        fields = '__all__'


class DefaultsForDepartmentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DefaultsForDepartments
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['doctor'] = {"id":instance.doctor.id, "name": instance.doctor.name} if instance.doctor else None
        representation['lab_technician'] = {"id":instance.lab_technician.id, "name":instance.lab_technician.name} if instance.lab_technician else None
        return representation