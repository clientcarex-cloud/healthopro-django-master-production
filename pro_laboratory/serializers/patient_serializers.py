from datetime import datetime
from django.db.models import Sum
from django.utils import timezone
from rest_framework import serializers, status
from django.db import transaction
import logging
from rest_framework.response import Response
from healtho_pro_user.models.users_models import Client
from pro_hospital.models.patient_wise_models import PatientServices, \
    PatientDoctorConsultationDetails, IPRoomBooking, PatientPackages, PatientVitals
from pro_hospital.models.universal_models import GlobalServices, GlobalRoom, DoctorConsultationDetails, GlobalPackages, \
    GlobalPackageService, GlobalPackageConsultation, GlobalPackageRoom, GlobalRoomBeds, GlobalPackageLabTest
from pro_hospital.serializers.patient_wise_serializers import PatientDoctorConsultationDetailsSerializer, \
    IPRoomBookingGetSerializer, PatientVitalsSerializer, calculate_room_charges
from pro_hospital.views.patient_wise_views import get_patient_visit_count
from pro_laboratory.models.b2b_models import CompanyRevisedPrices
from pro_laboratory.models.client_based_settings_models import BusinessControls
from pro_laboratory.models.global_models import LabDiscountType, LabGlobalTests, LabGlobalPackages, \
    LabStaffDefaultBranch
from pro_laboratory.models.lab_appointment_of_patient_models import LabAppointmentForPatient
from pro_laboratory.models.labtechnicians_models import LabTechnicians
from pro_laboratory.models.patient_models import HomeService, Patient, LabPatientInvoice, \
    LabPatientReceipts, LabPatientTests, LabPatientRefund, LabPatientPayments, LabPatientPackages
from pro_laboratory.models.phlebotomists_models import LabPhlebotomist
from pro_laboratory.models.sourcing_lab_models import SourcingLabRevisedTestPrice, SourcingLabRegistration, \
    SourcingLabTestsTracker
from pro_laboratory.serializers.b2b_serializers import CompanyWorkPartnershipSerializer
from pro_laboratory.serializers.global_serializers import LabDiscountTypeSerializer, LabGlobalTestsSerializer, \
    LabGlobalPackagesSerializer
from pro_laboratory.serializers.labtechnicians_serializers import LabTechnicianListSerializer
from pro_laboratory.serializers.sourcing_lab_serializers import SourcingLabRegistrationSerializer
from pro_laboratory.views.privilege_card_views import CalculatePrivilegeCardDiscountView
from pro_pharmacy.models import PatientMedicine, PharmaStock
from pro_pharmacy.serializers import PharmaStockGetSerializer
from pro_universal_data.models import ULabTestStatus, ULabPaymentModeType, PaymentFor
from pro_universal_data.serializers import ULabPatientTitlesSerializer
from pro_universal_data.models import MessagingTemplates, MessagingSendType
from pro_universal_data.views import send_and_log_whatsapp_sms, send_and_log_sms


class HomeServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeService
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
            validated_data['display_name'] = lab_global_test.display_name
            validated_data['department'] = lab_global_test.department
            validated_data['price'] = validated_data.get('price', lab_global_test.price)
            validated_data['short_code'] = lab_global_test.short_code
            validated_data['is_authorization'] = lab_global_test.is_authorization

        validated_data['status_id'] = status_id

        return super(LabTestSerializer, self).create(validated_data)


# Used at Tests updation
class LabPatientTestsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabPatientTests
        fields = '__all__'


class PatientServicesSerializer(serializers.ModelSerializer):
    service = serializers.PrimaryKeyRelatedField(
        queryset=GlobalServices.objects.all(),
        write_only=True
    )
    name = serializers.CharField(read_only=True)
    # status_id = serializers.IntegerField(write_only=True, required=False)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = PatientServices
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        representation['status_id'] = instance.status_id.name if instance.status_id else None
        representation['department'] = instance.service.department.name if instance.service.department else None

        return representation

class IPRoomBookingSerializer(serializers.ModelSerializer):
    GlobalRoomId = serializers.PrimaryKeyRelatedField(
        queryset=GlobalRoom.objects.all(),
        write_only=True
    )
    bed_number = serializers.PrimaryKeyRelatedField(
        queryset=GlobalRoomBeds.objects.all(),
        write_only=True, required=False
    )
    name = serializers.CharField(read_only=True)
    admitted_date = serializers.DateTimeField(required=False)
    no_of_days = serializers.IntegerField(write_only=True, required=False)
    charges_per_bed = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = IPRoomBooking
        fields = '__all__'



# Setup a logger for this module
logger = logging.getLogger(__name__)


class LabPatientPaymentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabPatientPayments
        fields = '__all__'


class GenerateReceiptAtPatientUpdationSerializer(serializers.ModelSerializer):
    client_id = serializers.CharField()
    payments = LabPatientPaymentsSerializer(many=True)

    class Meta:
        model = LabPatientReceipts
        fields = ['patient', 'remarks', 'discount_type', 'discount_amt', 'created_by', 'payments','payment_for',
                  'is_discount_amt_by_ref_doc', 'client_id']

class PatientPackagesSerializer(serializers.ModelSerializer): #This is to add packages to patients in HIMS
    GlobalPackageId = serializers.PrimaryKeyRelatedField(queryset=GlobalPackages.objects.all(), write_only=True)
    name = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    offer_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_discount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = PatientPackages
        fields = "__all__"


class LabPatientPackagesSerializer(serializers.ModelSerializer): #This is to add packages to patients in LIMS
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


class PatientMedicineAddSerializer(serializers.ModelSerializer):
    stock = serializers.PrimaryKeyRelatedField(queryset=PharmaStock.objects.all())
    quantity = serializers.IntegerField(required=False)
    is_strip = serializers.BooleanField(required=False)
    expiry_date = serializers.DateField(read_only=True)
    batch_number = serializers.CharField(read_only=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)


    class Meta:
        model = PatientMedicine
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['stock'] = PharmaStockGetSerializer(instance.stock).data if instance.stock else None
        return representation


def calculate_ref_discount_for_tests(tests=None, packages=None, discount=None):
    if tests and not packages:
        tests_count = len(tests)
    elif not tests and packages:
        for package in packages:
            package_tests = package.tests.all()
    else:
        pass



class PatientSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all(), required=False)
    mr_no = serializers.CharField(read_only=True)
    visit_id = serializers.CharField(read_only=True)
    home_service = HomeServiceSerializer(required=False)
    lab_tests = LabTestSerializer(many=True, required=False)
    payments = LabPatientPaymentsSerializer(many=True, required=False)
    discount_amt = serializers.DecimalField(max_digits=10, decimal_places=2, write_only=True, required=False, default=0)
    payment_remarks = serializers.CharField(write_only=True, required=False, allow_blank=True, default='')
    lab_discount_type_id = serializers.IntegerField(write_only=True, required=False, allow_null=True, default=None)
    lab_packages = LabPatientPackagesSerializer(many=True, required=False)
    receipt = GenerateReceiptAtPatientUpdationSerializer(required=False)
    is_discount_amt_by_ref_doc = serializers.BooleanField(default=False)
    payment_for = serializers.PrimaryKeyRelatedField(
        queryset=PaymentFor.objects.all(), required=False, allow_null=True)

    appointment_id = serializers.PrimaryKeyRelatedField(
        queryset=LabAppointmentForPatient.objects.all(), required=False, allow_null=True)

    sourcing_lab = serializers.PrimaryKeyRelatedField(
        queryset=SourcingLabRegistration.objects.all(),
        required=False, allow_null=True
    )
    privilege_discount = serializers.CharField(write_only=True, required=False, allow_null=True)
    added_on_time = serializers.DateTimeField(write_only=True, required=False, allow_null=True)
    # services = serializers.PrimaryKeyRelatedField(queryset=GlobalServices.objects.all(), many=True, allow_null=True,required=False)
    services = PatientServicesSerializer(many=True, required=False)
    doctor_consultations = PatientDoctorConsultationDetailsSerializer(many=True, required=False)
    room_booking = IPRoomBookingSerializer(required=False)
    packages = PatientPackagesSerializer(many=True, required=False)
    last_receipt_id = serializers.IntegerField(read_only=True, required=False)
    medicine = PatientMedicineAddSerializer(required=False, many=True)
    vitals = PatientVitalsSerializer(required=False)


    class Meta:
        model = Patient
        fields = '__all__'

    def create(self, validated_data, **kwargs):
        with transaction.atomic():
            try:
                if validated_data:
                    pass
                else:
                    validated_data = kwargs.get('patient_data')

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

                added_on_time = validated_data.pop('added_on_time', None)
                discount_amt = validated_data.pop('discount_amt', 0)
                lab_discount_type_id = validated_data.pop('lab_discount_type_id', None)
                payment_remarks = validated_data.pop('payment_remarks', '')
                home_service_data = validated_data.pop('home_service', None)
                lab_tests_data = validated_data.pop('lab_tests', [])
                payments = validated_data.pop('payments', [])
                client = validated_data.pop('client', None)
                lab_packages_data = validated_data.pop('lab_packages', [])
                is_discount_amt_by_ref_doc = validated_data.pop('is_discount_amt_by_ref_doc', False)
                payment_for = validated_data.pop('payment_for', None)
                appointment = validated_data.pop('appointment_id', None)
                privilege_discount = validated_data.pop('privilege_discount', None)
                services_data = validated_data.pop('services', [])
                doctor_consultation_data = validated_data.pop('doctor_consultations', [])
                room_booking_data = validated_data.pop('room_booking',[])
                packages_data = validated_data.pop('packages',[])
                sourcing_lab_input = validated_data.get('sourcing_lab')
                medicine_data = validated_data.pop('medicine', [])

                name = validated_data.get('name')
                mobile_number = validated_data.get('mobile_number')
                today = timezone.now().date()

                if added_on_time:
                    today = added_on_time.date()

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

                    if added_on_time:
                        current_date = added_on_time.strftime('%y%m%d')

                    existing_patients = Patient.objects.filter(name=name, mobile_number=mobile_number).first()
                    existing_patients_visits = Patient.objects.filter(name=name, mobile_number=mobile_number).count()

                    if existing_patients:
                        visit_count = existing_patients_visits + 1
                    else:
                        visit_count = 1

                    validated_data['mr_no'] = None
                    # visit_id = f'{current_date}-{patients_count}'
                    validated_data['visit_id'] = None
                    validated_data['visit_count'] = visit_count
                    validated_data['client'] = client
                    validated_data['last_updated_by'] = validated_data['created_by']

                    if added_on_time:
                        validated_data['added_on'] = added_on_time

                    try:
                        patient = Patient.objects.create(**validated_data)
                    except Exception as error:
                        error_message = error
                        print(error_message)
                        raise serializers.ValidationError({"Error": "Please Save Again"})

                    if home_service_data:
                        HomeService.objects.create(patient=patient, **home_service_data)

                    total_cost = 0
                    default_status = ULabTestStatus.objects.get(id=1)
                    ultrasound_status_id = ULabTestStatus.objects.get(id=2)

                    added_tests_list = []
                    added_packages_list = []
                    added_consultations_list=[]
                    added_services_list = []
                    added_rooms_list = []
                    all_tests_list = []
                    added_medicines_list = []

                    if lab_tests_data:
                        for lab_test_data in lab_tests_data:
                            sourcing_lab = lab_test_data.get('sourcing_lab')
                            if sourcing_lab:
                                lab_test_data['sourcing_lab'] = sourcing_lab

                            lab_test_data['patient'] = patient
                            lab_test_data['branch'] = patient.branch
                            status_id = lab_test_data.get('status_id')
                            if status_id is not None:
                                status_id = ULabTestStatus.objects.get(id=status_id)
                                lab_test_data['status_id'] = status_id
                            else:
                                status_instance = default_status
                                lab_test_data['status_id'] = status_instance

                            lab_test_instance = LabTestSerializer().create(validated_data=lab_test_data)
                            lab_test_instance.save()

                            if patient.partner:
                                company_revised_price = CompanyRevisedPrices.objects.filter(
                                    company=patient.partner.company, LabGlobalTestId=lab_test_instance.LabGlobalTestId).first()
                                if company_revised_price:
                                    lab_test_instance.price = company_revised_price.revised_price
                                    lab_test_instance.save()

                            if lab_test_instance.LabGlobalTestId.sourcing_lab:
                                lab_test_instance.is_outsourcing = lab_test_instance.LabGlobalTestId.is_outsourcing
                                lab_test_instance.sourcing_lab = lab_test_instance.LabGlobalTestId.sourcing_lab
                                lab_test_instance.save()

                            if patient.referral_lab:
                                lab_test_instance.sourcing_lab = patient.referral_lab
                                lab_test_instance.save()

                            if lab_test_instance.sourcing_lab:
                                revised_price_instance = SourcingLabRevisedTestPrice.objects.filter(
                                    sourcing_lab=lab_test_instance.sourcing_lab,
                                    LabGlobalTestId=lab_test_instance.LabGlobalTestId
                                ).first()
                                if revised_price_instance:
                                    lab_test_instance.price = revised_price_instance.revised_price
                                    lab_test_instance.save()

                            total_cost += lab_test_instance.price

                            added_tests_list.append(lab_test_instance)


                            if lab_test_instance.department.department_flow_type.name == "Transcriptor":
                                if lab_test_instance.status_id.name in ["Pending", "Emergency (Pending)"]:
                                    lab_test_instance.status_id = ultrasound_status_id
                                    lab_test_instance.save()

                                if not lab_test_instance.LabGlobalTestId.sourcing_lab:
                                    LabTechnicians.objects.create(LabPatientTestID=lab_test_instance)
                                elif lab_test_instance.LabGlobalTestId.sourcing_lab:
                                    tracker = SourcingLabTestsTracker.objects.create(
                                        sourcing_lab=lab_test_instance.sourcing_lab,
                                        patient_id=lab_test_instance.patient.id,
                                        lab_patient_test=lab_test_instance.id, to_send=True)

                        all_tests_list.extend(added_tests_list)

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
                            if patient.partner:
                                company_revised_price = CompanyRevisedPrices.objects.filter(
                                    company=patient.partner.company,LabGlobalPackageId=lab_package_instance.LabGlobalPackageId).first()
                                if company_revised_price:
                                    lab_package_instance.offer_price = company_revised_price.revised_price
                                    lab_package_instance.save()

                            for test in lab_package_data.lab_tests.all():
                                status_id = ultrasound_status_id if test.department.department_flow_type.name == "Transcriptor" else default_status
                                price = (test.price/lab_package_data.total_amount) * lab_package_data.offer_price
                                lab_test_data = {
                                    'patient': patient,
                                    'LabGlobalTestId': test,
                                    'status_id': status_id,
                                    'price':price,
                                    'is_package_test': True,
                                    'branch':patient.branch
                                }

                                lab_test_instance = LabTestSerializer().create(validated_data=lab_test_data)
                                lab_package_instance.lab_tests.add(lab_test_instance)
                                all_tests_list.append(lab_test_instance)

                                if lab_test_instance.LabGlobalTestId.sourcing_lab:
                                    lab_test_instance.is_outsourcing = lab_test_instance.LabGlobalTestId.is_outsourcing
                                    lab_test_instance.sourcing_lab = lab_test_instance.LabGlobalTestId.sourcing_lab
                                    lab_test_instance.save()

                                if patient.referral_lab:
                                    lab_test_instance.sourcing_lab = patient.referral_lab
                                    lab_test_instance.save()

                                if lab_test_instance.department.department_flow_type.name == "Transcriptor":
                                    if lab_test_instance.status_id.name in ["Pending", "Emergency (Pending)"]:
                                        lab_test_instance.status_id = ultrasound_status_id
                                        lab_test_instance.save()

                                    if not lab_test_instance.LabGlobalTestId.sourcing_lab:
                                        LabTechnicians.objects.create(LabPatientTestID=lab_test_instance)
                                    elif lab_test_instance.LabGlobalTestId.sourcing_lab:
                                        tracker = SourcingLabTestsTracker.objects.create(
                                            sourcing_lab=lab_test_instance.sourcing_lab,
                                            patient_id=lab_test_instance.patient.id,
                                            lab_patient_test=lab_test_instance.id, to_send=True)
                            total_cost += lab_package_instance.offer_price

                    if payment_for and payment_for.name !='Lab Tests':
                        if doctor_consultation_data:
                            for doctor_consultation in doctor_consultation_data:
                                consultation = doctor_consultation['consultation']
                                status_id = doctor_consultation['status_id']
                                consultation_instance = PatientDoctorConsultationDetails.objects.create(patient=patient,
                                                                                                        consultation = consultation,
                                                                                                        status_id = status_id,
                                                                                                        case_type=consultation.case_type,
                                                                                                        is_online=consultation.is_online,
                                                                                                        consultation_fee=consultation.consultation_fee,
                                                                                                        created_by=patient.created_by,
                                                                                                        is_package=False
                                                                                                        )
                                total_cost += consultation_instance.consultation_fee
                                added_consultations_list.append(consultation_instance)

                                if consultation.case_type == "follow up":
                                    patient_visits = get_patient_visit_count(consultation.labdoctors.id,
                                                                             consultation.patient.mobile_number)

                                    doctor_allowed_visits = consultation.labdoctors.free_visits_count

                                    if patient_visits >= doctor_allowed_visits:
                                        raise serializers.ValidationError({
                                            "Error": f"Free visits for follow-up are completed for Doctor {consultation.labdoctors.name}."
                                        })

                        if services_data:
                            for service_data in services_data:
                                service = service_data['service']
                                status_id = service_data.get('status_id')
                                added_on = service_data.get('added_on', datetime.now())

                                service_instance = PatientServices.objects.create(patient=patient,
                                                                                  name=service.name,
                                                                                  price=service.price,
                                                                                  status_id=status_id,
                                                                                  short_code=service.short_code,
                                                                                  service=service,
                                                                                  created_by=patient.created_by,
                                                                                  last_updated_by=patient.created_by,
                                                                                  is_package=False,
                                                                                  added_on=added_on
                                                                                  )

                                added_services_list.append(service_instance)
                                total_cost += service_instance.price

                        if room_booking_data:
                            room_data = room_booking_data['GlobalRoomId']
                            admitted_date = room_booking_data.get('admitted_date', datetime.now())
                            room_booking_instance = IPRoomBooking.objects.create(patient=patient,
                                                                                GlobalRoomId=room_data,
                                                                                name=room_data.name,
                                                                                room_type=room_data.room_type,
                                                                                room_number=room_data.room_number,
                                                                                floor=room_data.floor,
                                                                                charges_per_bed=room_data.charges_per_bed,
                                                                                time_category=room_data.time_category,
                                                                                created_by=patient.created_by,
                                                                                admitted_date = admitted_date,
                                                                                is_package=False)

                            booked_bed = room_booking_data.get('bed_number')
                            room_booking_instance.booked_bed_number = booked_bed
                            room_booking_instance.save()
                            global_bed = GlobalRoomBeds.objects.get(global_room=room_data, bed_number=booked_bed.bed_number)

                            global_bed.is_booked = True
                            global_bed.patient = patient
                            global_bed.save()
                            added_rooms_list.append(room_booking_instance)
                            if room_booking_instance.no_of_days:
                                total_cost += room_booking_instance.no_of_days * room_booking_instance.charges_per_bed
                            #     if room_booking_instance.time_category.name == 'Day':
                            #         total_cost += (room_booking_instance.no_of_days * (room_booking_instance.charges_per_bed /24)) # calculating charges per hours and multiplying with no of days value in hours
                            #     else:
                            #         total_cost += (room_booking_instance.no_of_days * room_booking_instance.charges_per_bed) # no of days in hours * charges per bed in hours

                        if packages_data:
                            for package_data in packages_data:
                                package = package_data['GlobalPackageId']
                                patient_package_instance = PatientPackages.objects.create(patient=patient,
                                                                                         GlobalPackageId=package,
                                                                                         name=package.name,
                                                                                         description=package.description,
                                                                                         offer_price=package.offer_price,
                                                                                         total_amount=package.total_amount,
                                                                                         total_discount=package.total_discount,
                                                                                         is_disc_percentage=package.is_disc_percentage,
                                                                                         package_image=package.package_image,
                                                                                         created_by=patient.created_by
                                                                                          )
                                # global_package = GlobalPackages.objects.filter(id=package.id)
                                global_package_tests = GlobalPackageLabTest.objects.filter(package=package)
                                if global_package_tests:
                                    for global_test in global_package_tests:
                                        patient_test = LabPatientTests.objects.create(
                                            patient=patient,
                                            LabGlobalTestId=global_test.lab_test,
                                            name=global_test.lab_test.name,
                                            price=global_test.lab_test.price,
                                            short_code=global_test.lab_test.short_code,
                                            department=global_test.lab_test.department,
                                            display_name=global_test.lab_test.display_name,
                                            is_package_test=global_test.lab_test.is_package_test
                                        )
                                global_package_services = GlobalPackageService.objects.filter(package=package)
                                if global_package_services:
                                    for package_service in global_package_services:
                                        patient_services_instance = PatientServices.objects.create(
                                            patient=patient,
                                            name=package_service.service.name,
                                            price=package_service.service.price,
                                            service=package_service.service,
                                            is_package=True,
                                            package=patient_package_instance,
                                            created_by=patient.created_by
                                        )
                                global_package_consultations = GlobalPackageConsultation.objects.filter(package=package)
                                if global_package_consultations:
                                    for package_consultation in global_package_consultations:
                                        doctor_consultation_instance = PatientDoctorConsultationDetails.objects.create(
                                            patient=patient,
                                            case_type=package_consultation.consultation.case_type,
                                            is_online=package_consultation.consultation.is_online,
                                            consultation_fee=package_consultation.consultation.consultation_fee,
                                            consultation=package_consultation.consultation,
                                            is_package=True,
                                            package=patient_package_instance,
                                            created_by=patient.created_by
                                        )
                                global_room_bookings = GlobalPackageRoom.objects.filter(package=package)
                                if global_room_bookings:
                                    for package_room in global_room_bookings:
                                        room_booking_instance = IPRoomBooking.objects.create(
                                            patient=patient,
                                            name=package_room.room.name,
                                            charges_per_bed=package_room.room.charges_per_bed,
                                            room_type=package_room.room.room_type,
                                            room_number=package_room.room.room_number,
                                            floor=package_room.room.floor,
                                            GlobalRoomId=package_room.room,
                                            time_category=package_room.room.time_category,
                                            created_by=patient.created_by,
                                            is_package=True,
                                            package=patient_package_instance,
                                            no_of_days=package_room.quantity
                                        )
                                total_cost += patient_package_instance.offer_price

                        if medicine_data:
                            for medicine in medicine_data:
                                stock = medicine['stock']
                                medicine_instance = PatientMedicine.objects.create(patient=patient,
                                                                          stock=stock,
                                                                          name=stock.item.name,
                                                                          quantity=medicine['quantity'],
                                                                          is_strip=medicine['is_strip'],
                                                                          expiry_date=stock.expiry_date,
                                                                          batch_number=stock.batch_number,
                                                                          price=stock.price)
                                pharmacy_stock = PharmaStock.objects.filter(id=medicine_instance.stock.id).first()
                                if medicine_instance.is_strip:
                                    pharmacy_stock.available_quantity = pharmacy_stock.available_quantity - medicine_instance.quantity
                                    pharmacy_stock.save()
                                else:
                                    pharmacy_stock.total_quantity = pharmacy_stock.total_quantity - medicine_instance.quantity
                                    pharmacy_stock.save()

                                if medicine_instance.is_strip == 'True':
                                    total_cost += medicine_instance.quantity * stock.price
                                else:
                                    total_cost += ((medicine_instance.price / stock.packs) * medicine_instance.quantity)
                                added_medicines_list.append(medicine_instance)

                    invoice, created = LabPatientInvoice.objects.update_or_create(
                        patient=patient,
                        defaults={
                            'total_cost': total_cost,
                            'total_due': total_cost,
                            'total_price': total_cost,
                        }
                    )

                    membership = patient.privilege_membership
                    privilege_discount_type = None
                    privilege_card_discount = 0

                    if membership:
                        global_test_ids = [test.LabGlobalTestId.id for test in added_tests_list]
                        tests = LabGlobalTests.objects.filter(id__in=global_test_ids)
                        calculation = CalculatePrivilegeCardDiscountView()
                        response = calculation.list(membership=membership, tests=tests,
                                                    privilege_discount=privilege_discount, add_usage=True)
                        privilege_card_discount += response.data.get('discount')

                        privilege_discount_type, created = LabDiscountType.objects.get_or_create(
                            name='Privilege Card Discount', number=0)

                    discount = 0
                    paid_amount = 0
                    discount_type = None
                    receipt = None

                    if payments:
                        for payment in payments:
                            paid_amount += payment['paid_amount']

                    if discount_amt:
                        discount += discount_amt
                    elif lab_discount_type_id:
                        discount_type = LabDiscountType.objects.get(id=lab_discount_type_id)
                        if discount_type.is_percentage:
                            discount += invoice.total_due * (discount_type.number / 100)
                        elif not discount_type.is_percentage:
                            discount += discount_type.number

                    if privilege_card_discount > 0:
                        discount = privilege_card_discount
                        discount_type = privilege_discount_type

                    if (invoice.total_due - discount) < (
                            invoice.total_paid + paid_amount):  # this logic is different from receipt logic
                        error_message = "Payment more than Due amount is not accepted!"
                        raise serializers.ValidationError({"Error": error_message})

                    elif (invoice.total_due - discount) >= paid_amount:
                        before_payment_due = invoice.total_due
                        after_payment_due = before_payment_due - paid_amount - discount
                        receipt = LabPatientReceipts.objects.create(
                            patient=patient,
                            invoiceid=invoice,
                            remarks=payment_remarks,
                            discount_amt=discount,
                            discount_type=discount_type,
                            payment_for = payment_for,
                            created_by=patient.created_by,
                            before_payment_due=before_payment_due,
                            after_payment_due=after_payment_due,
                            is_discount_amt_by_ref_doc=is_discount_amt_by_ref_doc
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

                        if added_consultations_list:
                            receipt.consultations.add(*added_consultations_list)

                        if added_services_list:
                            receipt.services.add(*added_services_list)

                        if added_rooms_list:
                            receipt.rooms.add(*added_rooms_list)
                        if added_medicines_list:
                            receipt.medicines.add(*added_medicines_list)

                        invoice.total_paid += paid_amount
                        invoice.total_discount += discount
                        invoice.total_price = invoice.total_cost - invoice.total_discount
                        invoice.total_due = invoice.total_due - paid_amount - discount

                        if is_discount_amt_by_ref_doc:
                            invoice.total_ref_discount += discount
                        else:
                            invoice.total_lab_discount += discount
                        invoice.save()

                        try:
                            if discount and receipt.payment_for.name == 'Lab Tests':
                                for test in all_tests_list:
                                    total_tests_cost = sum(test.price for test in all_tests_list)
                                    test.discount = (test.price/total_tests_cost) * discount
                                    test.save()

                        except Exception as error:
                            print(error)

                    referral_lab = patient.referral_lab

                    if referral_lab:
                        if referral_lab.type == 'Cash':
                            if patient.referral_lab.available_balance >= paid_amount:
                                patient.referral_lab.available_balance -= paid_amount
                                patient.referral_lab.save()

                    if appointment:
                        appointment.patient = patient
                        appointment.save()

                    #To add patients as backdate:
                    if added_on_time:
                        patient.added_on = added_on_time
                        patient.save()

                        invoice.added_on = added_on_time
                        invoice.save()

                        receipt.added_on = added_on_time
                        receipt.save()

                        if added_tests_list:
                            for test in added_tests_list:
                                test.added_on = added_on_time
                                test.save()

                        if added_packages_list:
                            for package in added_packages_list:
                                package.added_on = added_on_time
                                package.save()

                                for test in package.lab_tests.all():
                                    test.added_on = added_on_time
                                    test.save()

                    # Optionally, handle SMS and WhatsApp notifications here
                    try:
                        send_and_log_sms(search_id=patient.id, numbers=patient.mobile_number,
                                         sms_template=MessagingTemplates.objects.get(pk=1),
                                         messaging_send_type=MessagingSendType.objects.get(pk=1), client=client)
                    except Exception as error:
                        print(error)
                        logger.error(f"SMS sending failed for patient {patient.id}: {error}", exc_info=True)

                    try:                        
                        print(1111, patient.name)
                        print(client)
                        send_and_log_whatsapp_sms(search_id=patient.id, numbers=patient.mobile_number,
                                                  mwa_template=MessagingTemplates.objects.get(pk=10),
                                                  messaging_send_type=MessagingSendType.objects.get(pk=1),
                                                  client=client,send_reports_type='Automatic')
                        
                        print(1111, patient.name)
                    except Exception as error:
                        print(error)
                        logger.error(f"Whatsapp SMS sending failed for patient {patient.id}: {error}", exc_info=True)
                    if not existing_patients:
                        try:
                            
                            send_and_log_whatsapp_sms(search_id=patient.id, numbers=patient.mobile_number,
                                                      mwa_template=MessagingTemplates.objects.get(pk=12),
                                                      messaging_send_type=MessagingSendType.objects.get(pk=1),
                                                      client=client, send_reports_type='Automatic')
                        except Exception as error:
                            print(error)
                            logger.error(f"Whatsapp SMS sending failed for patient {patient.id}: {error}",
                                         exc_info=True)
                    if patient.referral_doctor:
                        try:
                            send_and_log_sms(search_id=patient.id, numbers=patient.referral_doctor.mobile_number,
                                             sms_template=MessagingTemplates.objects.get(pk=5),
                                             messaging_send_type=MessagingSendType.objects.get(pk=1), client=client)
                        except Exception as error:
                            print(error)
                            logger.error(f"SMS sending failed for referral doctor {patient.id}: {error}", exc_info=True)
                    return patient

            except Exception as error:
                logger.error(f"Unexpected error creating patient: {error}", exc_info=True)
                raise serializers.ValidationError(error)

    def update(self, instance, validated_data):
        with transaction.atomic():
            try:
                payment_for = validated_data.pop('payment_for', None)
                privilege_discount = validated_data.pop('privilege_discount', None)
                lab_tests_data = validated_data.pop('lab_tests', [])
                lab_packages_data = validated_data.pop('lab_packages', [])
                receipt_data = validated_data.pop('receipt', [])
                services_data = validated_data.pop('services',[])
                doctor_consultation_data = validated_data.pop('doctor_consultations', [])
                room_booking_data = validated_data.pop('room_booking',[])
                packages_data = validated_data.pop('packages', [])
                medicines_data = validated_data.pop('medicine', [])
                vitals_data = validated_data.pop('vitals', None)

                # Update patient details
                instance = super().update(instance, validated_data)

                invoice = LabPatientInvoice.objects.get(patient=instance)

                cost_to_be_added = 0
                default_status = ULabTestStatus.objects.get(id=1)
                ultrasound_status_id = ULabTestStatus.objects.get(id=2)

                added_tests_list = []
                added_packages_list = []
                added_consultations_list=[]
                added_services_list = []
                added_rooms_list = []
                all_tests_list = []
                added_medicines_list = []

                if lab_tests_data:
                    for lab_test_data in lab_tests_data:
                        lab_test_data['patient'] = instance
                        lab_test_data['branch'] = instance.branch
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

                        if instance.partner:
                            company_revised_price = CompanyRevisedPrices.objects.filter(
                                company=instance.partner.company,
                                LabGlobalTestId=lab_test_instance.LabGlobalTestId).first()
                            if company_revised_price:
                                lab_test_instance.price = company_revised_price.revised_price
                                lab_test_instance.save()

                        if lab_test_instance.LabGlobalTestId.sourcing_lab:
                            lab_test_instance.is_outsourcing = lab_test_instance.LabGlobalTestId.is_outsourcing
                            lab_test_instance.sourcing_lab = lab_test_instance.LabGlobalTestId.sourcing_lab
                            lab_test_instance.save()

                        if instance.referral_lab:
                            lab_test_instance.sourcing_lab = instance.referral_lab
                            lab_test_instance.save()

                        if lab_test_instance.sourcing_lab:
                            revised_price_instance = SourcingLabRevisedTestPrice.objects.filter(
                                sourcing_lab=lab_test_instance.sourcing_lab,
                                LabGlobalTestId=lab_test_instance.LabGlobalTestId
                            ).first()
                            if revised_price_instance:
                                lab_test_instance.price = revised_price_instance.revised_price
                                lab_test_instance.save()

                        cost_to_be_added += lab_test_instance.price

                        if lab_test_instance.department.department_flow_type.name == "Transcriptor":
                            if lab_test_instance.status_id.name in ["Pending", "Emergency (Pending)"]:
                                lab_test_instance.status_id = ultrasound_status_id
                                lab_test_instance.save()

                            if not lab_test_instance.LabGlobalTestId.sourcing_lab:
                                LabTechnicians.objects.create(LabPatientTestID=lab_test_instance)
                            elif lab_test_instance.LabGlobalTestId.sourcing_lab:
                                tracker = SourcingLabTestsTracker.objects.create(
                                    sourcing_lab=lab_test_instance.sourcing_lab,
                                    patient_id=lab_test_instance.patient.id,
                                    lab_patient_test=lab_test_instance.id, to_send=True)

                    all_tests_list.extend(added_tests_list)

                if lab_packages_data:
                    for lab_package_data in lab_packages_data:
                        lab_package_data = lab_package_data['LabGlobalPackageId']
                        lab_package_instance = LabPatientPackages.objects.create(patient=instance,
                                                                                 LabGlobalPackageId=lab_package_data,
                                                                                 name=lab_package_data.name,
                                                                                 description=lab_package_data.description,
                                                                                 offer_price=lab_package_data.offer_price,
                                                                                 total_amount=lab_package_data.total_amount,
                                                                                 total_discount=lab_package_data.total_discount,
                                                                                 is_disc_percentage=lab_package_data.is_disc_percentage,
                                                                                 package_image=lab_package_data.package_image,
                                                                                 created_by=instance.created_by)
                        for test in lab_package_data.lab_tests.all():
                            status_id = ultrasound_status_id if test.department.department_flow_type.name == "Transcriptor" else default_status
                            price = (test.price / lab_package_data.total_amount) * lab_package_data.offer_price

                            lab_test_data = {
                                'patient': instance,
                                'LabGlobalTestId': test,
                                'price': price,
                                'status_id': status_id,
                                'is_package_test': True,
                                'branch': instance.branch
                            }

                            lab_test_instance = LabTestSerializer().create(validated_data=lab_test_data)
                            lab_package_instance.lab_tests.add(lab_test_instance)
                            all_tests_list.append(lab_test_instance)

                            if lab_test_instance.LabGlobalTestId.sourcing_lab:
                                lab_test_instance.is_outsourcing = lab_test_instance.LabGlobalTestId.is_outsourcing
                                lab_test_instance.sourcing_lab = lab_test_instance.LabGlobalTestId.sourcing_lab
                                lab_test_instance.save()

                            if instance.referral_lab:
                                lab_test_instance.sourcing_lab = instance.referral_lab
                                lab_test_instance.save()

                            if lab_test_instance.department.department_flow_type.name == "Transcriptor":
                                if lab_test_instance.status_id.name in ["Pending", "Emergency (Pending)"]:
                                    lab_test_instance.status_id = ultrasound_status_id
                                    lab_test_instance.save()

                                if not lab_test_instance.LabGlobalTestId.sourcing_lab:
                                    LabTechnicians.objects.create(LabPatientTestID=lab_test_instance)
                                elif lab_test_instance.LabGlobalTestId.sourcing_lab:
                                    tracker = SourcingLabTestsTracker.objects.create(
                                        sourcing_lab=lab_test_instance.sourcing_lab,
                                        patient_id=lab_test_instance.patient.id,
                                        lab_patient_test=lab_test_instance.id, to_send=True)

                        added_packages_list.append(lab_package_instance)

                        cost_to_be_added += lab_package_instance.offer_price

                if payment_for and payment_for.name != 'Lab Tests':
                    if packages_data:
                        for package_data in packages_data:
                            package = package_data['GlobalPackageId']
                            patient_package_instance = PatientPackages.objects.create(patient=instance,
                                                                                      GlobalPackageId=package,
                                                                                      name=package.name,
                                                                                      description=package.description,
                                                                                      offer_price=package.offer_price,
                                                                                      total_amount=package.total_amount,
                                                                                      total_discount=package.total_discount,
                                                                                      is_disc_percentage=package.is_disc_percentage,
                                                                                      package_image=package.package_image,
                                                                                      created_by=instance.created_by
                                                                                      )
                            # global_package = GlobalPackages.objects.filter(id=package.id)
                            global_package_services = GlobalPackageService.objects.filter(package=package)
                            if global_package_services:
                                for package_service in global_package_services:
                                    patient_services_instance = PatientServices.objects.create(
                                        patient=instance,
                                        name=package_service.service.name,
                                        price=package_service.service.price,
                                        service=package_service.service,
                                        is_package=True,
                                        package=patient_package_instance,
                                        created_by=instance.created_by
                                    )
                            global_package_consultations = GlobalPackageConsultation.objects.filter(package=package)
                            if global_package_consultations:
                                for package_consultation in global_package_consultations:
                                    doctor_consultation_instance = PatientDoctorConsultationDetails.objects.create(
                                        patient=instance,
                                        case_type=package_consultation.consultation.case_type,
                                        is_online=package_consultation.consultation.is_online,
                                        consultation_fee=package_consultation.consultation.consultation_fee,
                                        consultation=package_consultation.consultation,
                                        is_package=True,
                                        package=patient_package_instance,
                                        created_by=instance.created_by
                                    )
                            global_room_bookings = GlobalPackageRoom.objects.filter(package=package)
                            if global_room_bookings:
                                for package_room in global_room_bookings:
                                    room_booking_instance = IPRoomBooking.objects.create(
                                        patient=instance,
                                        name=package_room.room.name,
                                        charges_per_bed=package_room.room.charges_per_bed,
                                        room_type=package_room.room.room_type,
                                        room_number=package_room.room.room_number,
                                        floor=package_room.room.floor,
                                        GlobalRoomId=package_room.room,
                                        time_category=package_room.room.time_category,
                                        created_by=instance.created_by,
                                        is_package=True,
                                        package=patient_package_instance,
                                        no_of_days=package_room.quantity
                                    )

                            cost_to_be_added += patient_package_instance.offer_price

                    if services_data:
                        for service_data in services_data:
                            service = service_data['service']
                            added_on = service_data.get('added_on', datetime.now())
                            service_instance = PatientServices.objects.create(patient=instance,
                                                                              name=service.name,
                                                                              price=service.price,
                                                                              short_code=service.short_code,
                                                                              service=service,
                                                                              created_by=instance.created_by,
                                                                              last_updated_by=instance.created_by,
                                                                              added_on=added_on,
                                                                              is_package=False)
                            status_id = service_data.get('status_id')

                            service_instance.status_id = status_id
                            service_instance.save()
                            added_services_list.append(service_instance)
                            cost_to_be_added += service_instance.price

                    if doctor_consultation_data:
                        for doctor_consultation in doctor_consultation_data:
                            consultation = doctor_consultation['consultation']
                            status_id = doctor_consultation.get('status_id')
                            consultation_instance = PatientDoctorConsultationDetails.objects.create(patient=instance, consultation = consultation,
                                                                                                    status_id = status_id,
                                                                                                    case_type=consultation.case_type,
                                                                                                    is_online=consultation.is_online,
                                                                                                    consultation_fee=consultation.consultation_fee,
                                                                                                    created_by=instance.created_by,
                                                                                                    is_package=False
                                                                                                    )

                            added_consultations_list.append(consultation_instance)
                            cost_to_be_added += consultation_instance.consultation_fee

                    if room_booking_data:
                        room_data = room_booking_data['GlobalRoomId']
                        admitted_date = room_booking_data.get('admitted_date', datetime.now())
                        print(admitted_date, 'admitted_date')
                        room_booking_instance = IPRoomBooking.objects.create(patient=instance,
                                                                             GlobalRoomId=room_data,
                                                                             name=room_data.name,
                                                                             room_type=room_data.room_type,
                                                                             room_number=room_data.room_number,
                                                                             floor=room_data.floor,
                                                                             admitted_date=admitted_date,
                                                                             charges_per_bed=room_data.charges_per_bed,
                                                                             time_category=room_data.time_category,
                                                                             created_by=instance.created_by,
                                                                             is_package=False)
                        no_of_days = room_booking_data.get('no_of_days')
                        booked_bed = room_booking_data.get('bed_number')
                        room_booking_instance.no_of_days = no_of_days
                        room_booking_instance.booked_bed_number = booked_bed
                        room_booking_instance.save()
                        global_bed = GlobalRoomBeds.objects.get(global_room=room_data, bed_number=booked_bed.bed_number)
                        global_bed.is_booked = True
                        global_bed.patient = instance
                        global_bed.save()

                        added_rooms_list.append(room_booking_instance)
                        if room_booking_instance.no_of_days:
                            cost_to_be_added += room_booking_instance.no_of_days * room_booking_instance.charges_per_bed
                            # if room_booking_instance.time_category.name == 'Day':
                            #
                            #     cost_to_be_added += (room_booking_instance.no_of_days * (
                            #                 room_booking_instance.charges_per_bed / 24))  # calculating charges per hours and multiplying with no of days value in hours
                            # else:
                            #     cost_to_be_added += (
                            #                 room_booking_instance.no_of_days * room_booking_instance.charges_per_bed)  # no of days in hours * charges per bed in hours

                    if vitals_data:
                        vitals_instance = PatientVitals.objects.create(patient=instance,
                                                                       bp1=vitals_data['bp1'],
                                                                       bp2=vitals_data['bp2'],
                                                                       pulse=vitals_data['pulse'],
                                                                       height=vitals_data['height'],
                                                                       weight=vitals_data['weight'],
                                                                       spo2=vitals_data['spo2'],
                                                                       temperature=vitals_data['temperature'],
                                                                       grbs=vitals_data['grbs'],
                                                                       added_on=vitals_data['added_on'],
                                                                       created_by=instance.last_updated_by
                                                                       )

                    if medicines_data:
                        for medicine in medicines_data:
                            stock = medicine['stock']
                            medicine_instance = PatientMedicine.objects.create(patient=instance,
                                                                      stock=stock,
                                                                      name=stock.item.name,
                                                                      is_strip=medicine['is_strip'],
                                                                      quantity=medicine['quantity'],
                                                                      expiry_date=stock.expiry_date,
                                                                      batch_number=stock.batch_number,
                                                                      price=stock.price)
                            if medicine_instance.is_strip == 'True':
                                cost_to_be_added += medicine_instance.quantity * medicine_instance.price
                            else:
                                cost_to_be_added += ((medicine_instance.price / stock.packs) * medicine_instance.quantity)
                            added_medicines_list.append(medicine_instance)

                invoice.total_cost += cost_to_be_added
                invoice.total_price += cost_to_be_added
                invoice.total_due += cost_to_be_added
                invoice.save()

                membership = instance.privilege_membership
                privilege_discount_type = None
                privilege_card_discount = 0

                if membership:
                    global_test_ids = [test.LabGlobalTestId.id for test in added_tests_list]
                    tests = LabGlobalTests.objects.filter(id__in=global_test_ids)

                    calculation = CalculatePrivilegeCardDiscountView()
                    response = calculation.list(membership=membership, tests=tests,
                                                privilege_discount=privilege_discount, add_usage=True)
                    privilege_card_discount += response.data.get('discount')

                    privilege_discount_type, created = LabDiscountType.objects.get_or_create(
                        name='Privilege Card Discount', number=0)

                if receipt_data:
                    patient = receipt_data.get('patient')
                    remarks = receipt_data.get('remarks')
                    discount_type = receipt_data.get('discount_type')
                    discount_amt = receipt_data.get('discount_amt')
                    payment_for = receipt_data.get('payment_for')
                    created_by = receipt_data.get('created_by')
                    client_id = receipt_data.pop('client_id', None)
                    payments = receipt_data.pop('payments', None)
                    is_discount_amt_by_ref_doc = receipt_data.pop('is_discount_amt_by_ref_doc', False)


                    if discount_type and discount_amt:
                        return Response(
                            {
                                "Error": 'Only one or none of the parameters should be given - discount_type, '
                                         'discount_amt'},
                            status=status.HTTP_400_BAD_REQUEST)

                    else:
                        if patient:
                            try:
                                discount = 0
                                paid_amount = 0
                                for payment in payments:
                                    paid_amount += payment['paid_amount']

                                invoiceid = LabPatientInvoice.objects.get(patient=patient)

                                if discount_amt:
                                    discount = discount_amt
                                elif discount_type:
                                    if discount_type.is_percentage:
                                        discount = invoiceid.total_due * (discount_type.number / 100)
                                    elif not discount_type.is_percentage:
                                        discount = discount_type.number

                                if privilege_card_discount > 0:
                                    discount = privilege_card_discount
                                    discount_type = privilege_discount_type

                                if (invoiceid.total_due - discount) >= paid_amount:
                                    before_payment_due = invoiceid.total_due
                                    after_payment_due = before_payment_due - paid_amount - discount
                                    receipt = LabPatientReceipts.objects.create(patient=patient, invoiceid=invoiceid,
                                                                                discount_type=discount_type,
                                                                                remarks=remarks,
                                                                                payment_for=payment_for,
                                                                                discount_amt=discount,
                                                                                before_payment_due=before_payment_due,
                                                                                after_payment_due=after_payment_due,
                                                                                is_discount_amt_by_ref_doc=is_discount_amt_by_ref_doc,
                                                                                created_by=created_by)

                                    if is_discount_amt_by_ref_doc:
                                        invoice.total_ref_discount += discount
                                    else:
                                        invoice.total_lab_discount += discount

                                    for payment in payments:
                                        payment_instance = LabPatientPayments.objects.create(
                                            paid_amount=payment['paid_amount'],
                                            pay_mode=payment['pay_mode']
                                        )

                                        receipt.payments.add(payment_instance)

                                        try:
                                            if discount and receipt.payment_for.name == 'Lab Tests':
                                                for test in all_tests_list:
                                                    total_tests_cost = sum(test.price for test in all_tests_list)
                                                    test.discount = (test.price / total_tests_cost) * discount
                                                    test.save()

                                        except Exception as error:
                                            print(error)

                                    if added_tests_list:
                                        receipt.tests.add(*added_tests_list)

                                    if added_packages_list:
                                        receipt.packages.add(*added_packages_list)

                                    if added_consultations_list:
                                        receipt.consultations.add(*added_consultations_list)

                                    if added_services_list:
                                        receipt.services.add(*added_services_list)

                                    if added_rooms_list:
                                        receipt.rooms.add(*added_rooms_list)
                                    if added_medicines_list:
                                        receipt.medicines.add(*added_medicines_list)

                                    #Amount_due
                                    invoiceid.total_discount += discount
                                    invoiceid.total_price -= discount
                                    invoiceid.total_paid += paid_amount
                                    invoiceid.total_due = invoiceid.total_due-paid_amount-discount
                                    invoiceid.save()

                            except Exception as error:
                                raise serializers.ValidationError({"Error": str(error)})
                return instance
            except Exception as error:
                logger.error(f"Unexpected error creating patient: {error}", exc_info=True)
                raise serializers.ValidationError(error)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        title_id = representation.get('title')
        if title_id is not None:
            title_name = instance.title.name
            representation['title'] = title_name

        last_receipt = LabPatientReceipts.objects.filter(patient=instance).last()
        representation['last_receipt_id']=last_receipt.id if last_receipt else ""
        return representation


class LabPatientReceiptsSerializer(serializers.ModelSerializer):
    discount_type = LabDiscountTypeSerializer()

    class Meta:
        model = LabPatientReceipts
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        payments = representation.get('payments')

        if payments is not None:
            payments_data = []
            for payment in instance.payments.all():
                payment_data = {
                    'id':payment.id,
                    'pay_mode': payment.pay_mode.name,
                    'paid_amount': payment.paid_amount
                }
                payments_data.append(payment_data)

            representation['payments'] = payments_data

        if instance.payment_for:
            representation['payment_for']={"id":instance.payment_for.id, "name":instance.payment_for.name}

        created_by_id = representation.get('created_by')
        if created_by_id is not None:
            created_by_name = instance.created_by.name
            representation['created_by'] = created_by_name
        return representation


# Standard View Page code

class ForViewsLabPatientInvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabPatientInvoice
        fields = ['total_cost', 'total_price', 'total_discount', 'total_due', 'total_paid', 'total_refund', 'patient',
                  'discountType']


class LabPhlebotomistSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabPhlebotomist
        fields = '__all__'


class StandardViewLabTestSerializer(serializers.ModelSerializer):
    department = serializers.CharField(source='department.name', read_only=True)
    status_id = serializers.CharField(source='status_id.name', read_only=True)
    phlebotomist = LabPhlebotomistSerializer()
    technician = serializers.SerializerMethodField()
    sourcing_lab = serializers.SerializerMethodField()
    department_flow_type = serializers.SerializerMethodField()

    class Meta:
        model = LabPatientTests
        fields = ['id', 'LabGlobalTestId', 'price', 'name', 'status_id', 'department', 'department_flow_type',
                  'short_code', 'added_on', 'technician',
                  'is_package_test', 'is_outsourcing', 'sourcing_lab', 'phlebotomist', 'technician']

    def get_sourcing_lab(self, obj):
        if obj.sourcing_lab:
            return SourcingLabRegistrationSerializer(obj.sourcing_lab, context=self.context['context']).data
        else:
            return None

    def get_technician(self, obj):
        technician = LabTechnicians.objects.filter(LabPatientTestID=obj).first()
        return LabTechnicianListSerializer(technician).data if technician else None

    def get_department_flow_type(self, obj):
        return obj.department.department_flow_type.id


class StandardViewLabPackageSerializer(serializers.ModelSerializer):
    lab_tests = StandardViewLabTestSerializer(many=True, read_only=True)

    class Meta:
        model = LabPatientPackages
        fields = ['id', 'LabGlobalPackageId', 'name', 'description', 'offer_price', 'total_amount', 'total_discount',
                  'is_disc_percentage', 'package_image', 'added_on', 'created_by', 'lab_tests']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        created_by_id = representation.get('created_by')
        if created_by_id is not None:
            created_by_name = instance.created_by.name
            representation['created_by'] = created_by_name
        return representation

class StandardViewPackagesSerializer(serializers.ModelSerializer):
    lab_tests = StandardViewLabTestSerializer(many=True, read_only=True)
    doctor_consultation = serializers.SerializerMethodField()
    services = serializers.SerializerMethodField()
    booked_rooms = serializers.SerializerMethodField()

    class Meta:
        model = PatientPackages
        fields = ['id', 'GlobalPackageId', 'name', 'description', 'offer_price', 'total_amount', 'total_discount',
                  'is_disc_percentage', 'package_image', 'added_on', 'created_by', 'lab_tests', 'doctor_consultation', 'services', 'booked_rooms']

    def get_doctor_consultation(self,obj):
        consultations = PatientDoctorConsultationDetails.objects.filter(package=obj)
        return PatientDoctorConsultationDetailsSerializer(consultations, many=True).data if consultations else None

    def get_services(self,obj):
        services = PatientServices.objects.filter(package=obj)
        return PatientServicesSerializer(services, many=True).data if services else None
    def get_booked_rooms(self, obj):
        rooms = IPRoomBooking.objects.filter(package=obj)
        return IPRoomBookingGetSerializer(rooms,
                                         many=True).data if rooms else None

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        created_by_id = representation.get('created_by')
        if created_by_id is not None:
            created_by_name = instance.created_by.name
            representation['created_by'] = created_by_name
        return representation

class LabAppointmentsSerializer(serializers.ModelSerializer):
    tests = LabGlobalTestsSerializer(many=True, read_only=True)
    packages = LabGlobalPackagesSerializer(many=True, read_only=True)

    class Meta:
        model = LabAppointmentForPatient
        fields = '__all__'

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
        #
        # referral_doctor = representation.get('referral_doctor')
        # if referral_doctor is not None:
        #     representation['referral_doctor'] = ReferralDoctorCountSerializer(instance.referral_doctor).data

        consulting_doctor = representation.get('consulting_doctor')
        if consulting_doctor is not None:
            representation['consulting_doctor'] = {"id": instance.consulting_doctor.id, "name": instance.consulting_doctor.name}

        return representation


class StandardViewPatientSerializer(serializers.ModelSerializer):
    lab_tests = serializers.SerializerMethodField()
    invoice = ForViewsLabPatientInvoiceSerializer(read_only=True, source='labpatientinvoice')
    title = ULabPatientTitlesSerializer(read_only=True)
    lab_packages = serializers.SerializerMethodField()  # this is to fetch the packages of LIMS patients
    appointment = serializers.SerializerMethodField()
    doctor_consultation = serializers.SerializerMethodField()
    services = serializers.SerializerMethodField()
    booked_rooms = serializers.SerializerMethodField()
    packages = serializers.SerializerMethodField() # this is to fetch the packages of HIMS patients
    medicines = serializers.SerializerMethodField()
    vitals = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = ['id', 'title', 'dob', 'name', 'lab_tests', 'lab_packages', 'added_on', 'created_by', 'mr_no',
                  'visit_id', 'invoice', 'email', 'is_sourcing_lab', 'privilege_membership',
                  'age', 'mobile_number', 'gender', 'referral_doctor', 'ULabPatientAge', 'attender_relationship_title',
                  'attender_name', 'department', 'prescription_attach', 'address', 'visit_count', 'appointment',
                  'partner', 'doctor_consultation', 'services', 'booked_rooms', 'packages', 'medicines', 'vitals']

    def get_lab_tests(self, obj):
        lab_tests = obj.labpatienttests_set.exclude(is_package_test=True)

        lab_tests_invoice = {
                "total_cost":"0.00", "total_discount":"0.00", "total_price":"0.00",
                "total_paid":"0.00","total_due":"0.00"
            }

        if lab_tests:
            total_cost = sum(lab_test.price for lab_test in lab_tests)

            receipts = LabPatientReceipts.objects.filter(patient=obj,payment_for__name='Lab Tests')

            total_discount = sum(receipt.discount_amt for receipt in receipts)

            paid_amount = 0
            for receipt in receipts:
                payments = receipt.payments.all()
                total_value = sum(getattr(obj, 'paid_amount', 0) for obj in payments)
                paid_amount+=total_value

            net_amount = total_cost - total_discount

            total_due = total_cost - total_discount - paid_amount

            lab_tests_invoice = {
                "total_cost":str(total_cost), "total_discount":str(total_discount), "total_price":str(net_amount),
                "total_paid":str(paid_amount),"total_due":str(total_due)
            }
        return {"invoice":lab_tests_invoice,
                "lab_tests": StandardViewLabTestSerializer(instance=lab_tests, many=True, context={"context": self.context}).data}


    def get_lab_packages(self, obj):
        lab_packages = obj.labpatientpackages_set
        return StandardViewLabPackageSerializer(instance=lab_packages, many=True,
                                                context={"context": self.context}).data

    def get_appointment(self, obj):
        return LabAppointmentsSerializer(instance=obj.patient_appointment, many=True).data

    def get_doctor_consultation(self, obj):
        consultations = obj.patientdoctorconsultationdetails_set.exclude(is_package=True)
        consultations_invoice={
                "total_cost":"0.00", "total_discount":"0.00", "total_price":"0.00",
                "total_paid":"0.00","total_due":"0.00"
            }

        if consultations:
            total_cost = sum(consultation.consultation_fee for consultation in consultations)

            receipts = LabPatientReceipts.objects.filter(patient=obj,payment_for__name='Doctor Consultation')

            total_discount = sum(receipt.discount_amt for receipt in receipts)

            paid_amount = 0
            for receipt in receipts:
                payments = receipt.payments.all()
                total_value = sum(getattr(obj, 'paid_amount', 0) for obj in payments)
                paid_amount+=total_value

            net_amount = total_cost - total_discount

            total_due = total_cost - total_discount - paid_amount

            consultations_invoice = {
                "total_cost":str(total_cost), "total_discount":str(total_discount), "total_price":str(net_amount),
                "total_paid":str(paid_amount),"total_due":str(total_due)
            }

        return {"invoice":consultations_invoice,"consultations": PatientDoctorConsultationDetailsSerializer(instance=consultations, many=True).data}

    def get_services(self, obj):
        services = obj.patientservices_set.exclude(is_package=True)
        services_invoice = {
                "total_cost":"0.00", "total_discount":"0.00", "total_price":"0.00",
                "total_paid":"0.00","total_due":"0.00"
            }
        if services:
            total_cost = sum(service.price for service in services)

            receipts = LabPatientReceipts.objects.filter(patient=obj,payment_for__name='Services')

            total_discount = sum(receipt.discount_amt for receipt in receipts)

            paid_amount = 0
            for receipt in receipts:
                payments = receipt.payments.all()
                total_value = sum(getattr(obj, 'paid_amount', 0) for obj in payments)
                paid_amount+=total_value

            net_amount = total_cost - total_discount

            total_due = total_cost - total_discount - paid_amount

            services_invoice = {
                "total_cost":str(total_cost), "total_discount":str(total_discount), "total_price":str(net_amount),
                "total_paid":str(paid_amount),"total_due":str(total_due)
            }

        return {"invoice": services_invoice,
                "services": PatientServicesSerializer(instance=services, many=True).data}

    def get_booked_rooms(self,obj):
        booked_rooms = obj.iproombooking_set.exclude(is_package=True)

        rooms_invoice = {
                "total_cost":"0.00", "total_discount":"0.00", "total_price":"0.00",
                "total_paid":"0.00","total_due":"0.00"
        }
        if booked_rooms:
            total_cost = sum((room.charges_per_bed * room.no_of_days if room.no_of_days else 1) for room in booked_rooms)

            receipts = LabPatientReceipts.objects.filter(patient=obj,payment_for__name='Rooms')

            total_discount = sum(receipt.discount_amt for receipt in receipts)

            paid_amount = 0
            for receipt in receipts:
                payments = receipt.payments.all()
                total_value = sum(getattr(obj, 'paid_amount', 0) for obj in payments)
                paid_amount += total_value

            net_amount = total_cost - total_discount

            total_due = total_cost - total_discount - paid_amount

            rooms_invoice = {
                "total_cost":str(total_cost), "total_discount":str(total_discount), "total_price":str(net_amount),
                "total_paid":str(paid_amount),"total_due":str(total_due)
            }

        return {"invoice": rooms_invoice,
                "rooms": IPRoomBookingGetSerializer(instance=booked_rooms, many=True).data}

    def get_medicines(self, obj):
        patient_medicines = obj.patientmedicine_set.all()

        patient_medicines_invoice = {
            "total_cost": "0.00", "total_discount": "0.00", "total_price": "0.00",
            "total_paid": "0.00", "total_due": "0.00"
        }

        if patient_medicines:
            total_cost = sum(
                (medicine.price - (medicine.price * (medicine.stock.item.discount / 100))) * medicine.quantity
                if medicine.is_strip else
                (medicine.quantity * ((medicine.price - (
                            medicine.price * (medicine.stock.item.discount / 100))) / medicine.stock.packs))
                for medicine in patient_medicines
            )
            receipts = LabPatientReceipts.objects.filter(patient=obj, payment_for__name='Medicines')

            total_discount = sum(receipt.discount_amt for receipt in receipts)

            paid_amount = 0
            for receipt in receipts:
                payments = receipt.payments.all()
                total_value = sum(getattr(obj, 'paid_amount', 0) for obj in payments)
                paid_amount += total_value

            net_amount = total_cost - total_discount

            total_due = total_cost - total_discount - paid_amount

            patient_medicines_invoice = {
                "total_cost": str(total_cost), "total_discount": str(total_discount), "total_price": str(net_amount),
                "total_paid": str(paid_amount), "total_due": str(total_due)
            }

        return {"invoice": patient_medicines_invoice,
                "medicines": PatientMedicineAddSerializer(instance=patient_medicines, many=True).data}

    def get_vitals(self, obj):
        vitals =obj.patientvitals_set
        return PatientVitalsSerializer(instance=vitals,many=True).data

    def get_packages(self,obj):
        packages = obj.patientpackages_set
        return StandardViewPackagesSerializer(instance=packages, many=True,
                                                context={"context": self.context}).data


    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['created_by'] = instance.created_by.name if instance.created_by else None
        representation['doctor_name'] = {instance.referral_doctor.name, instance.referral_doctor.mobile_number} if instance.referral_doctor else None

        if instance.privilege_membership:
            representation['privilege_membership'] = {"id": instance.privilege_membership.id,
                                                      "pc_no": instance.privilege_membership.pc_no}

        if instance.referral_lab:
            representation['referral_lab'] = SourcingLabRegistrationSerializer(instance=instance.referral_lab).data
        else:
            representation['referral_lab'] = None

        if instance.partner:
            representation['partner'] = CompanyWorkPartnershipSerializer(instance.partner).data
        else:
            representation['partner'] = None

        return representation



class NewTrialStandardViewPatientSerializer(serializers.ModelSerializer):
    # packages = serializers.SerializerMethodField() # this is to fetch the packages of HIMS patients

    class Meta:
        model = Patient
        fields = ['id', 'dob', 'name', 'added_on', 'created_by', 'mr_no', 'visit_id', 'email', 'is_sourcing_lab',
                  'privilege_membership', 'age', 'mobile_number', 'gender', 'referral_doctor', 'ULabPatientAge',
                  'attender_relationship_title', 'attender_name', 'department', 'prescription_attach', 'address',
                  'visit_count', 'partner']

    def get_lab_tests(self, obj):
        lab_tests = obj.labpatienttests_set.exclude(is_package_test=True)

        lab_tests_invoice = {
            "total_cost": "0.00", "total_discount": "0.00", "total_price": "0.00",
            "total_paid": "0.00", "total_due": "0.00"
        }

        lab_tests_data = []

        if lab_tests:
            total_cost = sum(lab_test.price for lab_test in lab_tests)

            receipts = LabPatientReceipts.objects.filter(patient=obj, payment_for__name='Lab Tests')

            total_discount = receipts.aggregate(total_discount_sum=Sum('discount_amt'))['total_discount_sum'] or 0

            paid_amount = receipts.annotate(total_paid=Sum('payments__paid_amount')).aggregate(
                                            total_paid_sum=Sum('total_paid'))['total_paid_sum'] or 0

            net_amount = total_cost - total_discount

            total_due = total_cost - total_discount - paid_amount

            lab_tests_invoice = {
                "total_cost": str(total_cost), "total_discount": str(total_discount),
                "total_price": str(net_amount),
                "total_paid": str(paid_amount), "total_due": str(total_due)
            }

            lab_tests_data = StandardViewLabTestSerializer(instance=lab_tests, many=True,
                                                           context={"context": self.context}).data

        return {"invoice": lab_tests_invoice, "lab_tests": lab_tests_data}

    def get_doctor_consultation(self, obj):
        consultations = obj.patientdoctorconsultationdetails_set.exclude(is_package=True)
        consultations_invoice={
                "total_cost":"0.00", "total_discount":"0.00", "total_price":"0.00",
                "total_paid":"0.00","total_due":"0.00"
            }

        consultations_data = []

        if consultations:
            total_cost = sum(consultation.consultation_fee for consultation in consultations)

            receipts = LabPatientReceipts.objects.filter(patient=obj,payment_for__name='Doctor Consultation')

            total_discount = receipts.aggregate(total_discount_sum=Sum('discount_amt'))['total_discount_sum'] or 0

            paid_amount = receipts.annotate(total_paid=Sum('payments__paid_amount')).aggregate(
                                            total_paid_sum=Sum('total_paid'))['total_paid_sum'] or 0

            net_amount = total_cost - total_discount

            total_due = total_cost - total_discount - paid_amount

            consultations_invoice = {
                "total_cost":str(total_cost), "total_discount":str(total_discount), "total_price":str(net_amount),
                "total_paid":str(paid_amount),"total_due":str(total_due)
            }

            consultations_data = PatientDoctorConsultationDetailsSerializer(instance=consultations, many=True).data

        return {"invoice":consultations_invoice,"consultations": consultations_data}

    def get_services(self, obj):
        services = obj.patientservices_set.exclude(is_package=True)
        services_invoice = {
                "total_cost":"0.00", "total_discount":"0.00", "total_price":"0.00",
                "total_paid":"0.00","total_due":"0.00"
            }
        services_data = []
        if services:
            total_cost = services.aggregate(total_cost_sum=Sum('price'))['total_cost_sum'] or 0

            receipts = LabPatientReceipts.objects.filter(patient=obj,payment_for__name='Services')

            total_discount = receipts.aggregate(total_discount_sum=Sum('discount_amt'))['total_discount_sum'] or 0

            paid_amount = receipts.annotate(total_paid=Sum('payments__paid_amount')).aggregate(
                                            total_paid_sum=Sum('total_paid'))['total_paid_sum'] or 0

            net_amount = total_cost - total_discount

            total_due = total_cost - total_discount - paid_amount

            services_invoice = {
                "total_cost":str(total_cost), "total_discount":str(total_discount), "total_price":str(net_amount),
                "total_paid":str(paid_amount),"total_due":str(total_due)
            }

            services_data = PatientServicesSerializer(instance=services, many=True).data

        return {"invoice": services_invoice, "services": services_data}

    def get_booked_rooms(self,obj):
        booked_rooms = obj.iproombooking_set.exclude(is_package=True)

        rooms_invoice = {
                "total_cost":"0.00", "total_discount":"0.00", "total_price":"0.00",
                "total_paid":"0.00","total_due":"0.00"
        }

        rooms_data = []
        if booked_rooms:
            total_cost = sum((room.charges_per_bed * room.no_of_days if room.no_of_days else 1) for room in booked_rooms)

            receipts = LabPatientReceipts.objects.filter(patient=obj,payment_for__name='Rooms')

            total_discount = receipts.aggregate(total_discount_sum=Sum('discount_amt'))['total_discount_sum'] or 0

            paid_amount = receipts.annotate(total_paid=Sum('payments__paid_amount')).aggregate(
                                            total_paid_sum=Sum('total_paid'))['total_paid_sum'] or 0

            net_amount = total_cost - total_discount

            total_due = total_cost - total_discount - paid_amount

            rooms_invoice = {
                "total_cost":str(total_cost), "total_discount":str(total_discount), "total_price":str(net_amount),
                "total_paid":str(paid_amount),"total_due":str(total_due)
            }

            rooms_data = IPRoomBookingGetSerializer(instance=booked_rooms, many=True).data

        return {"invoice": rooms_invoice, "rooms": rooms_data}

    def get_medicines(self, obj):
        patient_medicines = obj.patientmedicine_set.all()

        patient_medicines_invoice = {
            "total_cost": "0.00", "total_discount": "0.00", "total_price": "0.00",
            "total_paid": "0.00", "total_due": "0.00"
        }

        medicines_data = []

        if patient_medicines:
            total_cost = sum(medicine.price - (medicine.price * (medicine.stock.item.discount/100)) * medicine.quantity if medicine.is_strip==True else (medicine.quantity * ((medicine.price - (medicine.price * (medicine.stock.item.discount/100))) / medicine.stock.packs)) for medicine in patient_medicines)

            receipts = LabPatientReceipts.objects.filter(patient=obj, payment_for__name='Medicines')

            total_discount = receipts.aggregate(total_discount_sum=Sum('discount_amt'))['total_discount_sum'] or 0

            paid_amount = receipts.annotate(total_paid=Sum('payments__paid_amount')).aggregate(
                                            total_paid_sum=Sum('total_paid'))['total_paid_sum'] or 0

            net_amount = total_cost - total_discount

            total_due = total_cost - total_discount - paid_amount

            patient_medicines_invoice = {
                "total_cost": str(total_cost), "total_discount": str(total_discount), "total_price": str(net_amount),
                "total_paid": str(paid_amount), "total_due": str(total_due)
            }
            medicines_data = PatientMedicineAddSerializer(instance=patient_medicines, many=True).data

        return {"invoice": patient_medicines_invoice, "medicines": medicines_data}


    # def get_packages(self,obj):
    #     packages = obj.patientpackages_set
    #     return StandardViewPackagesSerializer(instance=packages, many=True,
    #                                             context={"context": self.context}).data


    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['title'] = ULabPatientTitlesSerializer(instance.title).data if instance.title else None
        representation['created_by'] = instance.created_by.name if instance.created_by else None
        representation['doctor_name'] = {instance.referral_doctor.name, instance.referral_doctor.mobile_number} if instance.referral_doctor else None

        representation['lab_tests'] = self.get_lab_tests(instance)
        representation['invoice'] = ForViewsLabPatientInvoiceSerializer(instance.labpatientinvoice).data if instance.labpatientinvoice else None

        lab_packages = instance.labpatientpackages_set
        if lab_packages:
            representation['lab_packages'] = StandardViewLabPackageSerializer(instance=lab_packages, many=True,
                                                    context={"context": self.context}).data
        else:
            representation['lab_packages'] = None

        if instance.privilege_membership:
            representation['privilege_membership'] = {"id": instance.privilege_membership.id,
                                                      "pc_no": instance.privilege_membership.pc_no}

        if instance.referral_lab:
            representation['referral_lab'] = SourcingLabRegistrationSerializer(instance=instance.referral_lab).data
        else:
            representation['referral_lab'] = None

        if instance.partner:
            representation['partner'] = CompanyWorkPartnershipSerializer(instance.partner).data
        else:
            representation['partner'] = None


        if instance.patient_appointment:
            representation['appointment'] = LabAppointmentsSerializer(instance=instance.patient_appointment, many=True).data
        else:
            representation['appointment'] = None

        provider_type = None
        if provider_type != 'Diagnostic Centre':
            representation['doctor_consultation'] = self.get_doctor_consultation(instance)
            representation['services'] = self.get_services(instance)
            representation['booked_rooms'] = self.get_booked_rooms(instance)
            representation['medicines'] = self.get_medicines(instance)

            vitals = instance.patientvitals_set
            if vitals:
                representation['vitals'] = PatientVitalsSerializer(instance=vitals, many=True).data
            else:
                representation['vitals'] = []

        return representation


# Single View Page Code
class SingleViewLabTestSerializer(serializers.ModelSerializer):
    department = serializers.CharField(source='department.name', read_only=True)
    status_id = serializers.CharField(source='status_id.name', read_only=True)

    class Meta:
        model = LabPatientTests
        fields = ['LabGlobalTestId', 'price', 'name', 'status_id', 'department']


class SingleViewPatientSerializer(serializers.ModelSerializer):
    lab_tests = SingleViewLabTestSerializer(many=True, read_only=True, source='labpatienttests_set')

    class Meta:
        model = Patient
        fields = ['id', 'title', 'name', 'lab_tests', 'added_on']


class LabPatientReceiptPaymentsSerializer(serializers.ModelSerializer):
    payments = LabPatientPaymentsSerializer(many=True)

    class Meta:
        model = LabPatientReceipts
        fields = ['patient', 'remarks', 'discount_type', 'discount_amt', 'created_by', 'payments']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        created_by_id = representation.get('created_by')
        if created_by_id is not None:
            created_by_name = instance.created_by.name
            representation['created_by'] = created_by_name
        return representation


class ReferralDoctorDetailSerializer(serializers.Serializer):
    doctor_name = serializers.CharField()
    total_patients = serializers.IntegerField()
    total_cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_paid = serializers.DecimalField(max_digits=10, decimal_places=2)


class LabPatientTestDetailSerializer(serializers.Serializer):
    test_name = serializers.CharField()
    test_count = serializers.IntegerField()


class DepartmentAnalyticsSerializer(serializers.Serializer):
    department_name = serializers.CharField()
    test_count = serializers.IntegerField()


class PatientOverviewSerializer(serializers.ModelSerializer):
    total_patients = serializers.IntegerField()
    male_count = serializers.IntegerField()
    female_count = serializers.IntegerField()
    age_group = serializers.DictField()

    def get_age_group(self, age_groups):
        return age_groups


class BusinessStatusSerializer(serializers.Serializer):
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_discount = serializers.DecimalField(max_digits=10, decimal_places=2)
    net_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    balance_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    refund_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_paid = serializers.DecimalField(max_digits=10, decimal_places=2)


class PatientRegistrationOverviewSerializer(serializers.Serializer):
    created_by = serializers.CharField()
    total_patients = serializers.IntegerField()
    total_amount = serializers.IntegerField()
    total_paid = serializers.IntegerField()
    total_due = serializers.IntegerField()
    total_cash = serializers.IntegerField()


class PayModeAnalyticsSerializer(serializers.Serializer):
    pay_mode = serializers.CharField(max_length=100)
    total_patients = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)


class LabPatientRefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabPatientRefund
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        created_by_id = representation.get('created_by')
        refund_mode_id = representation.get('refund_mode')
        if created_by_id is not None:
            created_by_name = instance.created_by.name
            representation['created_by'] = created_by_name
        if refund_mode_id is not None:
            refund_mode_name = instance.refund_mode.name
            representation['refund_mode'] = refund_mode_name
        return representation


class LabPatientInvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabPatientInvoice
        fields = '__all__'


class PatientCountSerializer(serializers.Serializer):
    month = serializers.IntegerField()
    total_patients = serializers.IntegerField()

    class Meta:
        model = Patient
        fields = ['month', 'total_patients']
