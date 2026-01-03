from django.forms import model_to_dict
from django_tenants.utils import schema_context
from rest_framework import serializers, status
from datetime import datetime, timedelta
from django.utils import timezone
from geopy.geocoders import Nominatim
from rest_framework.response import Response

from healtho_pro_user.models.pro_doctor_models import ProDoctorConsultation, ProdoctorAppointmentSlot
from healtho_pro_user.models.universal_models import ProDoctorProfessionalDetails, ProDoctor, Consultation
from healtho_pro_user.models.business_models import BusinessProfiles, BusinessTimings
from healtho_pro_user.models.universal_models import UProDoctorSpecializations, ProDoctorLanguageSpoken
from healtho_pro_user.models.users_models import Client, HealthOProUser
from healtho_pro_user.serializers.pro_doctor_serializers import ProDoctorConsultationSerializer, \
    ProdoctorAppointmentSlotSerializer, BusinessProfilesSerializer
from healtho_pro_user.serializers.universal_serializers import ProDoctorSerializer, ProDoctorLanguageSpokenSerializer
from mobile_app.models import QuickServices, MobileAppLabMenus, Category
from pro_laboratory.models.global_models import LabGlobalTests, LabGlobalPackages, LabDiscountType
from pro_laboratory.models.labtechnicians_models import LabTechnicians
from pro_laboratory.models.patient_appointment_models import PatientAppointmentWithDoctor
from pro_laboratory.models.patient_models import HomeService, LabPatientTests, LabPatientPayments, Patient, \
    LabPatientPackages, LabPatientInvoice, LabPatientReceipts, LabPatientRefund
from django.db import transaction, connection
import logging

from pro_laboratory.serializers.patient_serializers import StandardViewLabPackageSerializer, \
    ForViewsLabPatientInvoiceSerializer, StandardViewLabTestSerializer
from pro_pharmacy.models import PharmaItems, Orders, PharmaStock, Dosage, Payment, OrderItem, Order, DeliveryMode
from pro_universal_data.models import ULabTestStatus, MessagingTemplates, MessagingSendType
from pro_universal_data.serializers import ULabPaymentModeTypeSerializer


class QuickServicesSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuickServices
        fields = '__all__'


class MobileAppLabMenusSerializer(serializers.ModelSerializer):
    class Meta:
        model = MobileAppLabMenus
        fields = '__all__'


class DoctorSpecializationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UProDoctorSpecializations
        fields = '__all__'


class DoctorLanguageSpokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProDoctorLanguageSpoken
        fields = '__all__'


class BusinessTimingsSerializer(serializers.ModelSerializer):
    day = serializers.CharField(source='day.name')

    class Meta:
        model = BusinessTimings
        fields = ['day', 'start_time', 'end_time']


class HospitalSerializer(serializers.ModelSerializer):
    business_timings = BusinessTimingsSerializer(many=True)

    class Meta:
        model = BusinessProfiles
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.latitude and instance.longitude:
            address = self.get_address_from_lat_lon(instance.latitude, instance.longitude)
            representation['address'] = address
        state_id = representation.get('state')
        if state_id is not None:
            representation['state'] = instance.state.name
        return representation

    def get_address_from_lat_lon(self, lat, lon):
        geolocator = Nominatim(user_agent="healtho_user_location")
        location = geolocator.reverse((lat, lon), exactly_one=True)
        return location.address if location else None


class ProDoctorProfessionalDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProDoctorProfessionalDetails
        fields = ['geo_area', 'specialization', 'languages_spoken', 'awards_and_recognitions',
                  'research_and_publications']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        foreign_key_fields = ['specialization']
        for field in foreign_key_fields:
            field_instance = getattr(instance, field)
            if field_instance:
                representation[field] = str(field_instance)

        many_to_many_fields = ['languages_spoken', 'awards_and_recognitions', 'research_and_publications']
        for field in many_to_many_fields:
            field_instances = getattr(instance, field).all()
            representation[field] = [str(field_instance) for field_instance in field_instances]

        return representation


class DoctorConsultationSerializer(serializers.ModelSerializer):
    hospital = serializers.SerializerMethodField()
    hospital_address = serializers.SerializerMethodField()

    class Meta:
        model = ProDoctorConsultation
        fields = '__all__'

    def get_hospital(self, obj):
        return obj.hospital.organization_name if obj.hospital else None

    def get_hospital_address(self, obj):
        if obj.hospital.latitude and obj.hospital.longitude:
            return self.get_address_from_lat_lon(obj.hospital.latitude, obj.hospital.longitude)

    def get_address_from_lat_lon(self, lat, lon):
        geolocator = Nominatim(user_agent="healtho_user_location")
        location = geolocator.reverse((lat, lon), exactly_one=True)
        return location.address if location else None

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        consultation_type_id = representation.get('consultation_type')
        if consultation_type_id is not None:
            consultation_type_name = instance.consultation_type.name
            representation['consultation_type'] = consultation_type_name
        return representation


class DoctorAppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProdoctorAppointmentSlot
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        consultation_type_id = representation.get('consultation_type')
        if consultation_type_id is not None:
            consultation_type_name = instance.consultation_type.consultation_type.name
            representation['consultation_type'] = consultation_type_name
        return representation


class DoctorSerializer(serializers.ModelSerializer):
    professional_details = ProDoctorProfessionalDetailsSerializer(many=True)
    full_name = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    consultation = DoctorConsultationSerializer(many=True)
    # appointment_slots = DoctorAppointmentSerializer(many=True)
    upcoming_availability = serializers.SerializerMethodField()
    b_id = serializers.SerializerMethodField()
    class Meta:
        model = ProDoctor
        fields = ['id', 'full_name', 'phone_number', 'pro_user_id', 'license_number', 'years_of_experience',
                  'medical_school', 'graduation_year', 'latitude', 'longitude', 'profile_image',
                  'added_on', 'last_updated', 'b_id', 'professional_details', 'consultation',
                  'upcoming_availability']

    def get_full_name(self, obj):
        return obj.pro_user_id.full_name

    def get_phone_number(self, obj):
        return obj.pro_user_id.phone_number

    def get_b_id(self, obj):
        try:
            business = BusinessProfiles.objects.get(pro_user_id=obj.pro_user_id)
            return business.id
        except BusinessProfiles.DoesNotExist:
            return None

    def get_upcoming_availability(self, obj):
        current_datetime = datetime.now()

        # Filter the appointments to get only future slots
        appointments = ProdoctorAppointmentSlot.objects.filter(
            pro_doctor=obj,
            is_active=True,
            date__gte=current_datetime.date()
        ).exclude(
            date=current_datetime.date(),
            session_start_time__lte=current_datetime.time()
        )

        if appointments.exists():
            closest_appointment = min(
                appointments,
                key=lambda x: datetime.combine(x.date, x.session_start_time) - current_datetime
            )
            appointment_datetime = datetime.combine(closest_appointment.date, closest_appointment.session_start_time)

            if appointment_datetime.date() == current_datetime.date():
                return f"Today {appointment_datetime.strftime('%I:%M %p')}"

            tomorrow_date = current_datetime.date() + timedelta(days=1)
            if appointment_datetime.date() == tomorrow_date:
                return f"Tomorrow {appointment_datetime.strftime('%I:%M %p')}"

            return appointment_datetime.strftime('%Y-%m-%d %I:%M %p')

        return None

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.latitude and instance.longitude:
            address = self.get_address_from_lat_lon(instance.latitude, instance.longitude)
            for detail in representation['professional_details']:
                detail['geo_area'] = address
        return representation

    def get_address_from_lat_lon(self, lat, lon):
        geolocator = Nominatim(user_agent="healtho_user_location")
        location = geolocator.reverse((lat, lon), exactly_one=True)
        return location.address if location else None


class PharmaItemsSerializer(serializers.ModelSerializer):
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
        if hasattr(instance, 'details'):
            representation['details'] = PharmaStockSerializer(instance.details).data
        else:
            representation['details'] = None
        return representation


class PharmaStockSerializer(serializers.ModelSerializer):
    class Meta:
        model = PharmaStock
        fields = '__all__'


class DosageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dosage
        fields = ['dosage_value', 'unit']


class OrdersPharmaItemsSerializer(serializers.ModelSerializer):
    details = PharmaStockSerializer()
    dosage = DosageSerializer(many=True)

    class Meta:
        model = PharmaItems
        fields = '__all__'


class OrdersSerializer(serializers.ModelSerializer):
    item = OrdersPharmaItemsSerializer()

    class Meta:
        model = Orders
        fields = '__all__'


class LabTestSerializer(serializers.ModelSerializer):
    LabGlobalTestId = serializers.PrimaryKeyRelatedField(
        queryset=LabGlobalTests.objects.all(),
        write_only=True
    )

    price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    department = serializers.SerializerMethodField()
    status_id = serializers.IntegerField(write_only=True, required=False, default=1)  # Add status_id field
    name = serializers.CharField(read_only=True)  # Set as read-only
    department = serializers.CharField(read_only=True)  # Set as read-only
    patient = serializers.PrimaryKeyRelatedField(read_only=True)  # Set as read-only

    class Meta:
        model = LabPatientTests
        fields = ['id', 'LabGlobalTestId', 'patient', 'price', 'name', 'status_id', 'department', 'is_authorization']

    def get_department(self, obj):
        return obj.department.name if obj.department else None

    def create(self, validated_data):
        lab_global_test_id = validated_data.get('LabGlobalTestId')
        status_id = validated_data.get('status_id')

        if lab_global_test_id:
            lab_global_test = LabGlobalTests.objects.get(id=lab_global_test_id.id)
            validated_data['name'] = lab_global_test.name
            validated_data['department'] = lab_global_test.department
            validated_data['price'] = lab_global_test.price
            validated_data['short_code'] = lab_global_test.short_code
            validated_data['is_authorization'] = lab_global_test.is_authorization

        validated_data['status_id'] = status_id

        return super(LabTestSerializer, self).create(validated_data)


# Used at Tests updation
class LabPatientTestsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabPatientTests
        fields = '__all__'


# Setup a logger for this module
logger = logging.getLogger(__name__)


class LabPatientPaymentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabPatientPayments
        fields = '__all__'


class LabPatientPackagesSerializer(serializers.ModelSerializer):
    LabGlobalPackageId = serializers.PrimaryKeyRelatedField(
        queryset=LabGlobalPackages.objects.all(),
        write_only=True
    )
    name = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    offer_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_discount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = LabPatientPackages
        fields = "__all__"


class StandardViewMobileAppPatientSerializer(serializers.ModelSerializer):
    lab_tests = serializers.SerializerMethodField()
    lab_packages = StandardViewLabPackageSerializer(many=True, read_only=True, source='labpatientpackages_set')
    payments = serializers.SerializerMethodField()
    b_id = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = ['id', 'dob', 'name', 'added_on', 'mr_no', 'visit_id',
                  'age', 'mobile_number', 'gender', 'referral_doctor', 'ULabPatientAge',
                  'attender_name', 'department', 'prescription_attach', 'address', 'visit_count', 'payments',
                  'lab_tests', 'lab_packages', 'b_id']

    def get_lab_tests(self, obj):
        lab_tests = obj.labpatienttests_set.exclude(is_package_test=True)
        return StandardViewLabTestSerializer(instance=lab_tests, many=True).data

    def get_payments(self, obj):
        receipts = LabPatientReceipts.objects.filter(patient=obj)
        payments = LabPatientPayments.objects.filter(labpatientreceipts__in=receipts).distinct()
        return LabPatientPaymentsSerializer(payments, many=True).data

    def get_b_id(self, obj):
        client_name = obj.client.name
        business = BusinessProfiles.objects.get(organization_name=client_name)
        business_data = BusinessProfilesSerializer(business).data
        return business_data


class MobileAppPatientSerializer(serializers.ModelSerializer):
    b_id = serializers.PrimaryKeyRelatedField(queryset=BusinessProfiles.objects.all(), required=False)
    mr_no = serializers.CharField(read_only=True)
    visit_id = serializers.CharField(read_only=True)
    lab_tests = LabTestSerializer(many=True, required=False)
    payments = LabPatientPaymentsSerializer(many=True, required=False)
    discount_amt = serializers.DecimalField(max_digits=10, decimal_places=2, write_only=True, required=False, default=0)
    payment_remarks = serializers.CharField(write_only=True, required=False, allow_blank=True, default='')
    lab_discount_type_id = serializers.IntegerField(write_only=True, required=False, allow_null=True, default=None)
    lab_packages = LabPatientPackagesSerializer(many=True, required=False)

    class Meta:
        model = Patient
        fields = ['id','name', 'age', 'dob', 'mobile_number', 'mr_no', 'visit_id', 'gender', 'title', 'ULabPatientAge',
                  'discount_amt', 'lab_discount_type_id',

                  'payment_remarks', 'b_id', 'lab_tests', 'payments', 'lab_packages']

    def create(self, validated_data):
        with transaction.atomic():
            try:
                discount_amt = validated_data.pop('discount_amt', 0)
                lab_discount_type_id = validated_data.pop('lab_discount_type_id', None)
                payment_remarks = validated_data.pop('payment_remarks', '')
                # home_service_data = validated_data.pop('home_service', None)
                lab_tests_data = validated_data.pop('lab_tests', [])
                payments = validated_data.pop('payments', [])
                client = validated_data.pop('client', None)
                lab_packages_data = validated_data.pop('lab_packages', [])
                b_id = validated_data.pop('b_id', [])
                # print(b_id)
                client = Client.objects.get(name=b_id.organization_name)
                # print(client)

                name = validated_data.get('name')
                mobile_number = validated_data.get('mobile_number')
                today = timezone.now().date()

                existing_patients = Patient.objects.filter(mobile_number=mobile_number)
                existing_patients_data = None
                existing_patients_details = None

                if existing_patients:
                    existing_patients_data = existing_patients.filter(name=name,
                                                                      added_on__date__gte=today,
                                                                      added_on__date__lt=today + timezone.timedelta(
                                                                          days=1)
                                                                      )
                if existing_patients_data is not None:
                    for patient in existing_patients_data:
                        existing_patients_details = ','.join(
                            [patient.name + '-' + patient.mobile_number, 'MR.No:' + str(patient.mr_no)]
                        )

                if existing_patients_details is not None:
                    error_message = f"Patient already registered today, with the details:{existing_patients_details}!"
                    raise serializers.ValidationError({"Error": error_message})

                elif lab_discount_type_id is not None and discount_amt:
                    error_message = "Only one of the parameters should be given-discount_amt,lab_discount_type_id!"
                    raise serializers.ValidationError({"Error": error_message})

                else:
                    patients = Patient.objects.filter(added_on__date__gte=today,
                                                      added_on__date__lt=today + timezone.timedelta(days=1))
                    patients_count = patients.count() + 1
                    current_date = datetime.now().strftime('%y%m%d')

                    existing_patients = Patient.objects.filter(name=name, mobile_number=mobile_number).first()
                    existing_patients_visits = Patient.objects.filter(name=name, mobile_number=mobile_number).count()

                    if existing_patients:
                        mr_no = existing_patients.mr_no
                        visit_count = existing_patients.visit_count + 1
                    else:
                        mr_no = f'{current_date}-{patients_count}'
                        visit_count = 1

                    validated_data['mr_no'] = mr_no
                    visit_id = f'{current_date}-{patients_count}'
                    validated_data['visit_id'] = visit_id
                    validated_data['visit_count'] = visit_count
                    validated_data['client'] = client

                    patient = Patient.objects.create(**validated_data)

                    # if home_service_data:
                    #     HomeService.objects.create(patient=patient, **home_service_data)

                    total_cost = 0
                    default_status = ULabTestStatus.objects.get(id=1)
                    ultrasound_status_id = ULabTestStatus.objects.get(id=2)

                    added_tests_list = []
                    added_packages_list = []

                    if lab_packages_data:
                        for lab_package_data in lab_packages_data:
                            lab_package_data = lab_package_data['LabGlobalPackageId']
                            lab_package_instance = LabPatientPackages.objects.create(patient=patient,
                                                                                     LabGlobalPackageId=lab_package_data,
                                                                                     name=lab_package_data.name,
                                                                                     description=lab_package_data.description,
                                                                                     offer_price=lab_package_data.offer_price,
                                                                                     total_amount=lab_package_data.total_amount,
                                                                                     total_discount=lab_package_data.total_discount,
                                                                                     is_disc_percentage=lab_package_data.is_disc_percentage,
                                                                                     package_image=lab_package_data.package_image,
                                                                                     created_by=patient.created_by)
                            added_packages_list.append(lab_package_instance)
                            for test in lab_package_data.lab_tests.all():
                                status_id = ultrasound_status_id if test.department.department_flow_type.name == "Transcriptor" else default_status
                                lab_test_data = {
                                    'patient': patient,
                                    'LabGlobalTestId': test,
                                    'status_id': status_id,
                                    'is_package_test': True
                                }
                                lab_test_instance = LabTestSerializer().create(validated_data=lab_test_data)
                                lab_package_instance.lab_tests.add(lab_test_instance)

                                if lab_test_instance.department.department_flow_type.name == "Transcriptor":
                                    LabTechnicians.objects.create(LabPatientTestID=lab_test_instance)
                            total_cost += lab_package_instance.offer_price

                    if lab_tests_data:
                        for lab_test_data in lab_tests_data:
                            lab_test_data['patient'] = patient
                            status_id = lab_test_data.get('status_id')
                            status_id = ULabTestStatus.objects.get(id=status_id)
                            status_instance = default_status
                            if status_id is not None:
                                lab_test_data['status_id'] = status_id
                            else:
                                lab_test_data['status_id'] = status_instance
                            lab_test_instance = LabTestSerializer().create(validated_data=lab_test_data)
                            lab_test_instance.save()
                            added_tests_list.append(lab_test_instance)
                            total_cost += lab_test_instance.price

                            if lab_test_instance.department.department_flow_type.name == "Transcriptor":
                                LabTechnicians.objects.create(LabPatientTestID=lab_test_instance)

                    invoice, created = LabPatientInvoice.objects.update_or_create(
                        patient=patient,
                        defaults={
                            'total_cost': total_cost,
                            'total_due': total_cost,
                            'total_price': total_cost,
                        }
                    )

                    discount = 0
                    paid_amount = 0
                    discount_type = None
                    if payments:
                        for payment in payments:
                            paid_amount += payment['paid_amount']

                    if discount_amt:
                        discount = discount_amt
                    elif lab_discount_type_id:
                        discount_type = LabDiscountType.objects.get(id=lab_discount_type_id)
                        if discount_type.is_percentage:
                            discount = invoice.total_due * (discount_type.number / 100)
                        elif not discount_type.is_percentage:
                            discount = discount_type.number

                    if (invoice.total_due - discount) < (
                            invoice.total_paid + paid_amount):  # this logic is different from receipt logic
                        error_message = "Payment more than Due amount is not accepted!"
                        raise serializers.ValidationError({"Error": error_message})

                    elif (invoice.total_due - discount) >= paid_amount:
                        receipt = LabPatientReceipts.objects.create(
                            patient=patient,
                            invoiceid=invoice,
                            remarks=payment_remarks,
                            discount_amt=discount,
                            discount_type=discount_type,
                            created_by=patient.created_by
                        )

                        for payment in payments:
                            payment_instance = LabPatientPayments.objects.create(
                                paid_amount=payment['paid_amount'],
                                pay_mode=payment['pay_mode']
                            )
                            receipt.payments.add(payment_instance)

                        if added_tests_list:
                            receipt.tests.add(*added_tests_list)

                        if added_packages_list:
                            receipt.packages.add(*added_packages_list)

                        if discount:
                            lab_tests = LabPatientTests.objects.filter(patient=patient)
                            lab_tests = lab_tests.exclude(status_id__name="Cancelled")
                            tests_count = lab_tests.count()
                            discount_per_test = discount / tests_count

                            for test in lab_tests:
                                test.discount += discount_per_test
                                test.save()

                        invoice.total_paid += paid_amount
                        invoice.total_discount += discount
                        invoice.total_price = invoice.total_cost - invoice.total_discount
                        invoice.total_due = invoice.total_due - paid_amount - discount
                        invoice.save()

                    return patient

            except Exception as error:
                logger.error(f"Unexpected error creating patient: {error}", exc_info=True)
                raise serializers.ValidationError(error)


class PatientAppointmentWithDoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientAppointmentWithDoctor
        fields = ['pro_doctor', 'consultation', 'appointment_slot', 'pay_mode', 'paid_amount']


class ProDoctorDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProDoctor
        fields = ['years_of_experience', 'pro_user_id', 'profile_image']

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        doctor = instance.pro_user_id
        specialization = ProDoctorProfessionalDetails.objects.get(pro_doctor=instance).specialization.name
        languages = list(
            ProDoctorProfessionalDetails.objects.get(pro_doctor=instance).languages_spoken.values_list('id', flat=True))

        representation['doctor_id'] = instance.id
        representation['name'] = doctor.full_name
        representation['specialization'] = specialization
        representation['languages_spoken'] = languages
        return representation


class PatientRegistrationSerializer(serializers.ModelSerializer):
    b_id = serializers.PrimaryKeyRelatedField(queryset=BusinessProfiles.objects.all(), required=False)
    mr_no = serializers.CharField(read_only=True)
    visit_id = serializers.CharField(read_only=True)
    appointment = PatientAppointmentWithDoctorSerializer(write_only=True)

    class Meta:
        model = Patient
        fields = ['name', 'age', 'dob', 'mobile_number', 'mr_no', 'visit_id', 'gender', 'title', 'ULabPatientAge',
                  'appointment', 'b_id']

    def create(self, validated_data):
        with transaction.atomic():
            appointment_data = validated_data.pop('appointment')
            b_id = validated_data.pop('b_id', None)

            client = Client.objects.get(name=b_id.organization_name) if b_id else None

            name = validated_data.get('name')
            mobile_number = validated_data.get('mobile_number')
            today = timezone.now().date()

            existing_patients = Patient.objects.filter(mobile_number=mobile_number)
            existing_patients_data = None
            existing_patients_details = None

            if existing_patients:
                existing_patients_data = existing_patients.filter(name=name,
                                                                  added_on__date__gte=today,
                                                                  added_on__date__lt=today + timezone.timedelta(
                                                                      days=1)
                                                                  )
            if existing_patients_data is not None:
                for patient in existing_patients_data:
                    existing_patients_details = ','.join(
                        [patient.name + '-' + patient.mobile_number, 'MR.No:' + str(patient.mr_no)]
                    )

            # if existing_patients_details is not None:
            #     error_message = f"Patient already registered today, with the details:{existing_patients_details}!"
            #     raise serializers.ValidationError({"Error": error_message})
            # else:
            patients = Patient.objects.filter(added_on__date__gte=today,
                                              added_on__date__lt=today + timezone.timedelta(days=1))
            patients_count = patients.count() + 1
            current_date = datetime.now().strftime('%y%m%d')

            existing_patients = Patient.objects.filter(name=name, mobile_number=mobile_number).first()
            existing_patients_visits = Patient.objects.filter(name=name, mobile_number=mobile_number).count()

            if existing_patients:
                mr_no = existing_patients.mr_no
                visit_count = existing_patients.visit_count + 1
            else:
                mr_no = f'{current_date}-{patients_count}'
                visit_count = 1

            validated_data['mr_no'] = mr_no
            visit_id = f'{current_date}-{patients_count}'
            validated_data['visit_id'] = visit_id
            validated_data['visit_count'] = visit_count

            if client:
                validated_data['client'] = client

            patient = Patient.objects.create(**validated_data)

            appointment_data['patient'] = patient
            PatientAppointmentWithDoctor.objects.create(**appointment_data)

            return patient


class PatientAppointmentWithDoctorGetSerializer(serializers.ModelSerializer):
    pro_doctor = ProDoctorDetailsSerializer()
    consultation = ProDoctorConsultationSerializer()
    appointment_slot = ProdoctorAppointmentSlotSerializer()
    pay_mode = ULabPaymentModeTypeSerializer()

    class Meta:
        model = PatientAppointmentWithDoctor
        fields = ['pro_doctor', 'consultation', 'appointment_slot', 'pay_mode', 'paid_amount']


class PatientDetailSerializer(serializers.ModelSerializer):
    appointment = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = ['name', 'age', 'dob', 'mobile_number', 'mr_no', 'visit_id', 'gender', 'title', 'ULabPatientAge',
                  'appointment']

    def get_appointment(self, obj):
        try:
            appointment = PatientAppointmentWithDoctor.objects.get(patient=obj)
            return PatientAppointmentWithDoctorGetSerializer(appointment).data
        except PatientAppointmentWithDoctor.DoesNotExist:
            return None


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['amount', 'payment_method', 'transaction_id', 'created_at', 'updated_at']


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['medicine', 'quantity']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    payment = PaymentSerializer()

    class Meta:
        model = Order
        fields = ['delivery_method', 'address', 'total_price', 'created_at', 'items', 'payment']
        read_only_fields = ['total_price']


class PatientSerializer(serializers.ModelSerializer):
    b_id = serializers.PrimaryKeyRelatedField(queryset=BusinessProfiles.objects.all(), required=False)
    order = OrderSerializer()

    class Meta:
        model = Patient
        fields = ['b_id', 'name', 'age', 'gender', 'mobile_number', 'ULabPatientAge', 'order']

    def create(self, validated_data):
        b_id = validated_data.pop('b_id', None)
        client = Client.objects.get(name=b_id.organization_name) if b_id else None

        order_data = validated_data.pop('order')
        order_items_data = order_data.pop('items')
        payment_data = order_data.pop('payment')

        if client:
            validated_data['client'] = client

        patient = Patient.objects.create(**validated_data)

        total_price = sum(item['medicine'].price * item['quantity'] for item in order_items_data)
        order_data['total_price'] = total_price
        order = Order.objects.create(patient=patient, **order_data)
        for item_data in order_items_data:
            OrderItem.objects.create(order=order, **item_data)

        Payment.objects.create(order=order, **payment_data)

        return patient


class OrderItemgetSerializer(serializers.ModelSerializer):
    medicine = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        # fields = '__all__'
        fields = ['quantity', 'order', 'medicine']

    def get_medicine(self, obj):
        medicine = obj.medicine
        if medicine:
            medicine = PharmaStockSerializer(medicine).data
            name = PharmaItems.objects.get(id=medicine['item']).name
            item_image = PharmaItems.objects.get(id=medicine['item']).item_image
            return {
                'item': name,
                'description': medicine['description'],
                'price': medicine['price'],
                'item_image': item_image
            }
        return None


class OrdergetSerializer(serializers.ModelSerializer):
    items = OrderItemgetSerializer(many=True, read_only=True)
    payment = PaymentSerializer(read_only=True)

    class Meta:
        model = Order
        fields = '__all__'

    # def to_representation(self, instance):
    #     representation = super().to_representation(instance)
    #
    #     # items = instance.items
    #     items = OrderItem.objects.get(order=instance)
    #     representation['delivery_method'] = instance.delivery_method.name
    #     representation['items'] = items
    #     # representation['specialization'] = specialization
    #     return representation


class PatientMedicinesOrderingGetSerializer(serializers.ModelSerializer):
    b_id = serializers.SerializerMethodField()
    order = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = ['b_id', 'name', 'age', 'gender', 'mobile_number', 'ULabPatientAge', 'order']

    def get_b_id(self, obj):
        client_name = obj.client.name
        business = BusinessProfiles.objects.get(organization_name=client_name)
        business_data = BusinessProfilesSerializer(business).data
        return business_data

    def get_order(self, obj):
        order = Order.objects.filter(patient=obj).first()
        if order:
            return OrdergetSerializer(order).data
        return None


class DoctorAppointmentsListSerializer(serializers.ModelSerializer):
    consultation_type = serializers.SerializerMethodField()
    hospital = serializers.SerializerMethodField()

    class Meta:
        model = ProdoctorAppointmentSlot
        fields = '__all__'

    def get_consultation_type(self, obj):
        return obj.consultation_type.consultation_type.name if obj.consultation_type else None

    def get_hospital(self, obj):
        return obj.consultation_type.hospital.id if obj.consultation_type else None


class DeliveryModeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryMode
        fields = "__all__"


class PharmaStockGetSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    item_image = serializers.SerializerMethodField()

    class Meta:
        model = PharmaStock
        fields = ['name', 'description', 'item_image', 'price']

    def get_name(self, obj):
        return obj.item.name

    def get_item_image(self, obj):
        return obj.item.item_image


class GetNearestSerializer(serializers.Serializer):
    latitude = serializers.CharField(max_length=30)
    longitude = serializers.CharField(max_length=30)


class PharmaItemsGetSerializer(serializers.ModelSerializer):
    quantity = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    class Meta:
        model = PharmaItems
        fields = ['name', 'item_image', 'quantity', 'price', 'description']

    def get_quantity(self, obj):
        try:
            return obj.details.quantity
        except PharmaStock.DoesNotExist:
            return None

    def get_price(self, obj):
        try:
            return obj.details.price
        except PharmaStock.DoesNotExist:
            return None

    def get_description(self, obj):
        try:
            return obj.details.description
        except PharmaStock.DoesNotExist:
            return None


class CategoryPharmaItemsSerializer(serializers.Serializer):
    client = serializers.CharField()
    medicines = PharmaItemsGetSerializer(many=True)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'
