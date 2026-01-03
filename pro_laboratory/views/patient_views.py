import base64
import logging
import random
import string
from datetime import datetime, timedelta
from decimal import Decimal
from http.client import HTTPResponse

from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Prefetch, Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from django_tenants.utils import schema_context
from rest_framework import viewsets, generics, permissions
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from rest_framework.views import APIView

from healtho_pro_user.models.business_models import BusinessProfiles
from healtho_pro_user.models.users_models import Client
from pro_hospital.models.patient_wise_models import PatientServices, PatientDoctorConsultationDetails, IPRoomBooking, \
    PatientVitals
from pro_laboratory.filters import PatientFilter, LabTestFilter, LabTestFilterForPatientView
from pro_laboratory.models.client_based_settings_models import BusinessControls
from pro_laboratory.models.global_models import LabStaff, LabStaffDefaultBranch
from pro_laboratory.models.patient_models import Patient, LabPatientTests, LabPatientReceipts, LabPatientInvoice, \
    LabPatientRefund, PatientOTP, LabPatientPackages, PatientPDFs
from pro_laboratory.serializers.patient_serializers import PatientSerializer, StandardViewPatientSerializer, \
    LabPatientReceiptsSerializer, LabPatientRefundSerializer, \
    LabPatientInvoiceSerializer, LabPatientTestsSerializer, NewTrialStandardViewPatientSerializer

from pro_laboratory.views.universal_views import GeneratePatientReceiptViewSet
from pro_pharmacy.models import PatientMedicine
from pro_universal_data.models import ULabTestStatus, MessagingTemplates, MessagingSendType
from pro_universal_data.views import send_sms, send_and_log_whatsapp_sms

logger = logging.getLogger(__name__)

class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all()  # Default queryset
    serializer_class = PatientSerializer


class LabPatientTestsViewSet(viewsets.ModelViewSet):
    queryset = LabPatientTests.objects.all()
    serializer_class = LabPatientTestsSerializer


class StandardViewPatientsListView(generics.ListAPIView):
    serializer_class = StandardViewPatientSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = PatientFilter


    def get_queryset(self):
        try:
            query = self.request.query_params.get('q', None)
            sort = self.request.query_params.get('sort', None)
            page_size = self.request.query_params.get('page_size', None)
            date = self.request.query_params.get('date', None)
            date_range_after = self.request.query_params.get('date_range_after', None)
            date_range_before = self.request.query_params.get('date_range_before', None)
            departments_details = self.request.query_params.get('departments', [])
            receiptionist_details = self.request.query_params.get('labstaff_id', [])
            appointment = self.request.query_params.get('appointment', None)
            status_ids = self.request.query_params.get('status_id', None)
            patient_id = self.request.query_params.get('id', None)
            transaction_id = self.request.query_params.get('transaction', None)

            if page_size == 'all' and not (date or (date_range_after and date_range_before)) and not query:
                error_message = "Please select Date range for patient_standard_view!"
                logger.error(f'"Error": {error_message}', exc_info=True)
                raise ValidationError(error_message)


            user = self.request.user
            status_id_list=[]
            controls = BusinessControls.objects.first()
            if controls and controls.multiple_branches:
                default_branch_obj = LabStaffDefaultBranch.objects.get(lab_staff__mobile_number=user.phone_number)
                default_branch = default_branch_obj.default_branch.all()
                lab_tests_queryset = LabPatientTests.objects.filter(branch__in=default_branch).order_by('id')
            else:
                lab_tests_queryset = LabPatientTests.objects.all().order_by('id')
            room_booking_details = IPRoomBooking.objects.all()

            lab_tests_filter = LabTestFilter(self.request.GET, queryset=lab_tests_queryset)
            if not lab_tests_filter.is_valid():
                error_message = "Invalid filter parameters for lab tests in patient_standard_view!"
                logger.error(f'"Error":{error_message}', exc_info=True)
                raise ValidationError(f'"Error":{error_message}')

            filtered_lab_tests_qs = lab_tests_filter.qs
            patients_queryset = Patient.objects.none()

            if filtered_lab_tests_qs.exists():
                patients_queryset = Patient.objects.filter(
                    labpatienttests__in=filtered_lab_tests_qs
                ).distinct().prefetch_related(
                    Prefetch('labpatienttests_set', queryset=filtered_lab_tests_qs),
                ).select_related('labpatientinvoice')

            if str(transaction_id) == '1':
                consultations = PatientDoctorConsultationDetails.objects.all()
                if consultations.exists():
                    if status_ids:
                        # Parse status IDs and filter consultations by those statuses
                        status_id_list = [int(sid.strip()) for sid in status_ids.split(',')]
                        filtered_consultations = consultations.filter(status_id__id__in=status_id_list)
                    else:
                        # If no specific status is provided, include all consultations
                        filtered_consultations = consultations

                        # Fetch patients linked to the filtered consultations
                    patients_with_filtered_consultation = Patient.objects.filter(
                        patientdoctorconsultationdetails__in=filtered_consultations
                    ).distinct().prefetch_related(
                        Prefetch('patientdoctorconsultationdetails_set', queryset=filtered_consultations)
                    )
                    # Return patients filtered by the status-specific consultations
                    return patients_with_filtered_consultation

            if str(transaction_id) == '6':
                medicines = PatientMedicine.objects.all()

                patients_with_medicines = Patient.objects.filter(
                    patientmedicine__in=medicines
                ).distinct().prefetch_related('patientmedicine_set')
                return patients_with_medicines

            if status_ids:
                status_id_list = [int(status_id.strip()) for status_id in status_ids.split(',') if status_id.strip()]

            if status_id_list:
                consultations = PatientDoctorConsultationDetails.objects.filter(status_id__id__in=status_id_list)
            else:
                consultations = PatientDoctorConsultationDetails.objects.all()

            if patient_id:
                consultations = PatientDoctorConsultationDetails.objects.filter(patient__id=patient_id)

            if consultations.exists():
                patients_with_consultation = Patient.objects.filter(
                    patientdoctorconsultationdetails__in=consultations
                ).distinct().prefetch_related('patientdoctorconsultationdetails_set')
                patients_queryset |= patients_with_consultation

            if status_ids:
                services = PatientServices.objects.filter(status_id__id__in=status_id_list)
            else:
                services = PatientServices.objects.all()

            if patient_id:
                services = PatientServices.objects.filter(patient__id=patient_id)

            if services.exists():
                patients_with_services = Patient.objects.filter(
                    patientservices__in=services
                ).distinct().prefetch_related(
                Prefetch('patientservices_set'),
            ).select_related('labpatientinvoice')
                patients_queryset |= patients_with_services

            if patient_id:
                vitals = PatientVitals.objects.filter(patient__id=patient_id)
            else:
                vitals = PatientVitals.objects.all()

            if vitals.exists():
                patients_with_vitals = Patient.objects.filter(
                    patientvitals__in=vitals
                ).distinct().prefetch_related('patientvitals_set')
                patients_queryset |= patients_with_vitals

            if room_booking_details:
                room_ids = [room.id for room in room_booking_details]

                patients_with_room_booking = Patient.objects.filter(
                    iproombooking__id__in=room_ids
                ).distinct().prefetch_related('iproombooking_set', )
                patients_queryset |= patients_with_room_booking

            if patient_id:
                patient_medicines = PatientMedicine.objects.filter(patient__id=patient_id)
            else:
                patient_medicines = PatientMedicine.objects.all()

            if patient_medicines.exists():
                medicines = [medicine.id for medicine in patient_medicines]

                patients_with_medicines = Patient.objects.filter(patientmedicine__in=medicines).distinct().prefetch_related(
                    'patientmedicine_set')
                patients_queryset |= patients_with_medicines

            if departments_details:
                departments = [department.strip() for department in departments_details.split(',') if department.strip()]
                department_query = Q(labpatienttests__department__id__in=departments)

                patients_queryset = patients_queryset.filter(department_query)

            if receiptionist_details:
                labstaffs = [labstaff.strip() for labstaff in receiptionist_details.split(',') if labstaff.strip()]
                staff_query = Q(created_by__id__in=labstaffs)

                patients_queryset = patients_queryset.filter(staff_query)

            if appointment == 'check_in':
                patients_queryset = patients_queryset.filter(patient_appointment__isnull=False)
            elif appointment == 'paid':
                patients_queryset = patients_queryset.filter(patient_appointment__isnull=False, labpatientinvoice__total_due = 0)

            if query is not None:
                search_query = (Q(name__icontains=query) | Q(mr_no__icontains=query) | Q(visit_id__icontains=query) | Q(
                    labpatienttests__name__icontains=query) | Q(labpatienttests__short_code__icontains=query) | Q(
                    mobile_number__icontains=query))

                patients_queryset = patients_queryset.filter(search_query)

            if sort == '-added_on':
                patients_queryset = patients_queryset.order_by('-added_on')
            if sort == 'added_on':
                patients_queryset = patients_queryset.order_by('added_on')

            return patients_queryset

        except Exception as error:
            error_message = f"{error} for patient_standard_view!"
            logger.error(f'"Error":"{error_message}"', exc_info=True)
            raise ValidationError({"Error": f"{error}"})


class NewTrailStandardViewPatientsListView(generics.ListAPIView):
    queryset = Patient.objects.all()
    serializer_class = NewTrialStandardViewPatientSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = PatientFilter

    def list(self, request, *args, **kwargs):
        try:
            print('started')
            patients_queryset = self.get_queryset()
            output_queryset = Patient.objects.none()

            query_params = self.request.query_params
            query = query_params.get('q', None)
            sort = query_params.get('sort', None)
            page_size = query_params.get('page_size', None)
            date = query_params.get('date', None)
            date_range_after = query_params.get('date_range_after', None)
            date_range_before = query_params.get('date_range_before', None)
            departments_details = query_params.get('departments', [])
            receptionist_details = query_params.get('labstaff_id', [])
            appointment = query_params.get('appointment', None)
            status_ids_details = query_params.get('status_id', None)
            patient_id = query_params.get('id', None)
            transaction_id = query_params.get('transaction', None)

            if page_size == 'all' and not (date or (date_range_after and date_range_before)) and not query:
                error_message = "Please select Date range for patient_standard_view!"
                logger.error(f'"Error": {error_message}', exc_info=True)
                raise ValidationError(error_message)

            user = self.request.user
            client = self.request.client
            business = BusinessProfiles.objects.get(organization_name=client.name)
            controls = BusinessControls.objects.first()
            print(111)

            departments = list(map(int, departments_details.split(','))) if departments_details else []
            status_ids = list(map(int, status_ids_details.split(','))) if status_ids_details else []
            lab_staffs = list(map(int, receptionist_details.split(','))) if receptionist_details else []

            if controls and controls.multiple_branches:
                default_branch_obj = LabStaffDefaultBranch.objects.get(lab_staff__mobile_number=user.phone_number)
                default_branch = default_branch_obj.default_branch.all()
                patients_queryset = patients_queryset.filter(branch__in=default_branch)

            print(222)

            lab_tests_queryset = LabPatientTests.objects.filter(patient__in=patients_queryset)

            lab_tests_filter = LabTestFilterForPatientView(self.request.GET, queryset=lab_tests_queryset)
            if not lab_tests_filter.is_valid():
                error_message = "Invalid filter parameters for lab tests in patient_standard_view!"
                logger.error(f'"Error":{error_message}', exc_info=True)
                return Response({"Error":error_message}, status=status.HTTP_400_BAD_REQUEST)

            filtered_lab_tests_qs = lab_tests_filter.qs

            if filtered_lab_tests_qs.exists():
                output_queryset = patients_queryset.filter(labpatienttests__in=filtered_lab_tests_qs
                ).distinct().prefetch_related(Prefetch('labpatienttests_set', queryset=filtered_lab_tests_qs),
                ).select_related('labpatientinvoice')

            print(333)

            if business.provider_type.name != 'Diagnostic Centre':
                if str(transaction_id) == '6':
                    patients_with_medicines = PatientMedicine.objects.filter(patient__in=patients_queryset
                                                        ).distinct().prefetch_related('patientmedicine_set')
                    return patients_with_medicines

                room_bookings = IPRoomBooking.objects.filter(patient__in=patients_queryset)
                consultations = PatientDoctorConsultationDetails.objects.filter(patient__in=patients_queryset)
                services = PatientServices.objects.filter(patient__in=patients_queryset)
                vitals = PatientVitals.objects.filter(patient__in=patients_queryset)
                patient_medicines = PatientMedicine.objects.filter(patient__in=patients_queryset)

                if status_ids:
                    consultations = consultations.filter(status_id__id__in=status_ids)
                    services = services.filter(status_id__id__in=status_ids)

                if patient_id:
                    consultations = consultations.filter(patient__id=patient_id)
                    services = services.filter(patient__id=patient_id)
                    vitals = vitals.filter(patient__id=patient_id)
                    patient_medicines = patient_medicines.filter(patient__id=patient_id)

                if consultations.exists():
                    patients_with_consultation = Patient.objects.filter(
                        patientdoctorconsultationdetails__in=consultations
                    ).distinct().prefetch_related('patientdoctorconsultationdetails_set')

                    output_queryset |= patients_with_consultation

                if services.exists():
                    patients_with_services = Patient.objects.filter(
                        patientservices__in=services
                    ).distinct().prefetch_related(
                        Prefetch('patientservices_set'),
                    ).select_related('labpatientinvoice')
                    output_queryset |= patients_with_services

                if vitals.exists():
                    patients_with_vitals = Patient.objects.filter(
                        patientvitals__in=vitals
                    ).distinct().prefetch_related('patientvitals_set')
                    output_queryset |= patients_with_vitals

                if room_bookings.exists():
                    patients_with_room_booking = Patient.objects.filter(
                        iproombooking__in=room_bookings
                    ).distinct().prefetch_related('iproombooking_set', )
                    output_queryset |= patients_with_room_booking

                if patient_medicines.exists():
                    patients_with_medicines = Patient.objects.filter(
                        patientmedicine__in=patient_medicines).distinct().prefetch_related(
                        'patientmedicine_set')
                    output_queryset |= patients_with_medicines

            print(444)

            if lab_staffs:
                output_queryset = output_queryset.filter(created_by__id__in=lab_staffs)

            if query is not None:
                search_query = (
                            Q(name__icontains=query) | Q(mr_no__icontains=query) | Q(visit_id__icontains=query) | Q(
                        labpatienttests__name__icontains=query) | Q(
                        labpatienttests__short_code__icontains=query) | Q(
                        mobile_number__icontains=query))

                output_queryset = output_queryset.filter(search_query)
            print(55)

            if appointment == 'check_in':
                output_queryset = output_queryset.filter(patient_appointment__isnull=False)
            elif appointment == 'paid':
                output_queryset = output_queryset.filter(patient_appointment__isnull=False,
                                                             labpatientinvoice__total_due=0)

            if sort == '-added_on':
                output_queryset = output_queryset.order_by('-added_on')
            elif sort == 'added_on':
                output_queryset = output_queryset.order_by('added_on')

            print(7777)

            page = self.paginate_queryset(output_queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True, context={"request":self.request})
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(output_queryset, many=True, context={"request":self.request})
            return Response(serializer.data)

        except Exception as error:
            return Response({"Error":error}, status=status.HTTP_400_BAD_REQUEST)


class LabPatientReceiptsListView(generics.ListAPIView):
    serializer_class = LabPatientReceiptsSerializer

    def get_queryset(self):
        queryset = LabPatientReceipts.objects.all()
        patient = self.request.query_params.get('patient', None)
        if patient is not None:
            queryset = LabPatientReceipts.objects.filter(patient=patient)
        queryset = queryset.order_by('-added_on')
        return queryset


class LabPatientRefundViewSet(viewsets.ModelViewSet):
    queryset = LabPatientRefund.objects.all()
    serializer_class = LabPatientRefundSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        patient = validated_data.get('patient')
        tests_to_cancel = validated_data.pop('tests', [])
        packages_to_cancel = validated_data.pop('packages', [])
        refund = validated_data.get('refund')
        remarks = validated_data.get('remarks')
        add_refund_to_due = validated_data.get('add_refund_to_due')

        with transaction.atomic():
            if refund:
                total_refund_amount = patient.labpatientinvoice.total_refund + refund
                total_paid_amount = patient.labpatientinvoice.total_paid

                if total_paid_amount >= total_refund_amount:
                    patient.labpatientinvoice.total_refund += refund
                    patient.labpatientinvoice.save()
                else:
                    return Response({"Error": "Total Refund Given Cannot be more than Total Paid Amount"},
                                    status=status.HTTP_400_BAD_REQUEST)

            refund_object = LabPatientRefund.objects.create(**validated_data)

            patient = refund_object.patient

            if tests_to_cancel:
                for test in tests_to_cancel:
                    test.status_id = ULabTestStatus.objects.get(pk=21)
                    test.save()
                    refund_object.tests.add(test)

            if packages_to_cancel:
                for package in packages_to_cancel:
                    package.is_package_cancelled=True
                    package.save()
                    for test in package.lab_tests.all():
                        test.status_id = ULabTestStatus.objects.get(pk=21)
                        test.save()

            # Calculation of totals
            invoiceid = LabPatientInvoice.objects.get(patient=patient)
            receipts = LabPatientReceipts.objects.filter(patient=patient)

            all_tests_in_receipts = []
            all_packages_in_receipts = []
            all_payments_in_receipts = []

            for receipt_id in receipts:
                tests = receipt_id.tests.all()
                all_tests_in_receipts.extend(tests)

                packages = receipt_id.packages.all()
                all_packages_in_receipts.extend(packages)

                payments = receipt_id.payments.all()
                all_payments_in_receipts.extend(payments)

            # Total cost
            total_cost_of_tests = sum(
                getattr(obj, 'price', 0) for obj in all_tests_in_receipts if
                getattr(obj.status_id, 'name', None) != "Cancelled")
            total_cost_of_packages = sum(
                getattr(obj, 'offer_price', 0) for obj in all_packages_in_receipts if
                not obj.is_package_cancelled)

            invoice_total_cost = total_cost_of_tests + total_cost_of_packages

            # Total discount
            invoice_total_discount = sum(
                getattr(obj, 'discount', 0) for obj in all_tests_in_receipts if
                getattr(obj.status_id, 'name', None) != "Cancelled")

            # Amount_due
            invoiceid.total_cost = invoice_total_cost
            invoiceid.total_price = invoiceid.total_cost - invoiceid.total_discount
            invoiceid.total_due = invoiceid.total_price - (invoiceid.total_paid - invoiceid.total_refund)
            invoiceid.save()

            if invoiceid.total_due < 0:
                invoiceid.total_due = 0

            if invoiceid.total_price < 0:
                invoiceid.total_price = 0
                invoiceid.total_discount = 0

            invoiceid.save()

        serializer = LabPatientRefundSerializer(refund_object)
        return Response(serializer.data)


class LabPatientInvoiceListAPIView(generics.ListAPIView):
    serializer_class = LabPatientInvoiceSerializer

    def get_queryset(self):
        patient = self.request.query_params.get('patient', None)
        if patient is not None:
            queryset = LabPatientInvoice.objects.filter(patient=patient)
        else:
            queryset = LabPatientInvoice.objects.none()
        return queryset


class LabPatientRefundListAPIView(generics.ListAPIView):
    serializer_class = LabPatientRefundSerializer

    def get_queryset(self):
        queryset = LabPatientRefund.objects.all()
        patient = self.request.query_params.get('patient')
        if patient is not None:
            queryset = queryset.filter(patient=patient)
        return queryset


class SendOTPforreportViewset(viewsets.ModelViewSet):
    permission_classes = [permissions.AllowAny]

    def decode_id(self, value):
        decoded_bytes = base64.urlsafe_b64decode(value.encode('utf-8'))
        return decoded_bytes.decode('utf-8')

    def create(self, request, *args, **kwargs):
        mobile_number = self.request.query_params.get('m')
        client_id = self.request.query_params.get('c')

        mobile_number = self.decode_id(mobile_number)
        client_id = self.decode_id(client_id)
        if mobile_number and client_id:
            client = Client.objects.get(pk=client_id)
            with schema_context(client.schema_name):
                try:
                    otp_code = ''.join(random.choices(string.digits, k=4))
                    send_sms(mobile_number, otp_code)
                    otp_instance, created = PatientOTP.objects.get_or_create(mobile_number=mobile_number)
                    if otp_instance.can_resend():
                        new_otp = ''.join(random.choices(string.digits, k=4))
                        otp_instance.reset_otp(new_otp)
                    otp_instance.otp_code = otp_code
                    otp_instance.save()
                    return Response('OTP sent successfully')
                except Exception as error:
                    return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)


class ResendOTPViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.AllowAny]

    def decode_id(self, value):
        decoded_bytes = base64.urlsafe_b64decode(value.encode('utf-8'))
        return decoded_bytes.decode('utf-8')

    def create(self, request, *args, **kwargs):
        mobile_number = request.query_params.get('m')
        client_id = request.query_params.get('c')

        mobile_number = self.decode_id(mobile_number)
        client_id = self.decode_id(client_id)

        if mobile_number and client_id:
            client = Client.objects.get(pk=client_id)
            with schema_context(client.schema_name):
                try:
                    otp_instance = PatientOTP.objects.get(mobile_number=mobile_number)

                    if otp_instance.can_resend():
                        new_otp_code = ''.join(random.choices(string.digits, k=4))
                        otp_instance.reset_otp(new_otp_code)
                        send_sms(mobile_number, f"{new_otp_code} | HealthO Pro")

                        return Response({'message': 'OTP sent Successfully'}, status=status.HTTP_200_OK)
                    else:
                        return Response({'error': 'OTP resend request too soon'},
                                        status=status.HTTP_400_BAD_REQUEST)
                except PatientOTP.DoesNotExist:
                    return Response('No OTP exists for the given mobile number', status=status.HTTP_400_BAD_REQUEST)
                except Exception as error:
                    return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response('Mobile number and client ID are required', status=status.HTTP_400_BAD_REQUEST)


@receiver(post_save, sender=LabPatientReceipts)
def send_report_ready_sms_on_receipt_creation(sender, instance, created, **kwargs):
    print('accessing rceipt')
    if created:
        patient = instance.patient
        client = patient.client
        try:
            patient_receipt = GeneratePatientReceiptViewSet()

            patient_response = patient_receipt.create(patient_id=patient.id, client_id=client.id,
                                                     receipt_id=instance.id,
                                                     printed_by_id=instance.created_by.id)

            pdf_base64=patient_response.data.get('pdf_base64')

            pdf_base64 = pdf_base64.split(",", 1)[1]

            pdf_binary = base64.b64decode(pdf_base64)
            current_datetime = timezone.now()
            formatted_datetime = current_datetime.strftime("%I:%M %p")
            report_name = f"{patient.name}_{formatted_datetime}.pdf"
            patient_pdf = PatientPDFs.objects.create(
                receipt_pdf=ContentFile(pdf_binary, name=report_name)
            )
            file_location = PatientPDFs.objects.last()
            file_location = file_location.receipt_pdf
            print(file_location, 'file loc')
            send_and_log_whatsapp_sms(
                search_id=patient.id,
                numbers=patient.mobile_number,
                mwa_template=MessagingTemplates.objects.get(pk=17),
                messaging_send_type=MessagingSendType.objects.get(pk=1),
                client=client,
                receipt=instance.id,
                send_reports_type='Automatic',
                file_location=file_location
            )
        except Exception as error:
            print(f"Error sending message: {error}")
            return Response({'Error': str(error)})


class PatientMaxRefundLimitAPIView(APIView):
    def post(self, request, *args, **kwargs):
        patient_id = request.data.get('patient_id')
        test_ids = request.data.pop('test_ids', [])
        test_package_ids = request.data.pop('test_package_ids', [])

        if not patient_id:
            return Response({"Error": "No patient id provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({"Error": "Patient not found"}, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(test_ids, list):
            return Response({"Error": "Test IDs should be provided as a list."}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(test_package_ids, list):
            return Response({"Error": "Test package IDs should be provided as a list."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate that provided test_ids and test_packages belong to the patient
        tests = LabPatientTests.objects.filter(patient=patient, id__in=test_ids)
        test_packages = LabPatientPackages.objects.filter(patient=patient, id__in=test_package_ids)

        valid_test_ids = set(tests.values_list('id', flat=True))
        valid_test_package_ids = set(test_packages.values_list('id', flat=True))

        if not set(test_ids).issubset(valid_test_ids) or not set(test_package_ids).issubset(valid_test_package_ids):
            return Response({"Error": "Please provide patient-related test IDs or test package IDs only."}, status=status.HTTP_400_BAD_REQUEST)

        # fetch patient invoice
        try:
            patient_invoice = LabPatientInvoice.objects.get(patient=patient)
        except LabPatientInvoice.DoesNotExist:
            return Response({"Error": "Invoice not found for the patient"}, status=status.HTTP_400_BAD_REQUEST)

        invoice_total_paid = patient_invoice.total_paid
        invoice_total_refund = patient_invoice.total_refund
        invoice_total_price= patient_invoice.total_price
        invoice_total_cost= patient_invoice.total_cost
        invoice_total_discount = patient_invoice.total_discount
        invoice_total_due = patient_invoice.total_due

        # fetch lab tests relevant to patient
        lab_patient_tests = LabPatientTests.objects.filter(patient=patient, is_package_test=False)
        lab_patient_packages = LabPatientPackages.objects.filter(patient=patient)
        if not lab_patient_tests.exists() and not lab_patient_packages.exists():
            return Response({"Error": "No lab tests or packages found for the patient."}, status=status.HTTP_400_BAD_REQUEST)

        # fetch  all tests accounts data or net amount
        test_cost = 0

        tests_and_packages_total_cost = invoice_total_cost

        # Cancelling tests net amount
        cancelled_test_total_cost = 0

        cancelled_tests = LabPatientTests.objects.filter(patient=patient, id__in=test_ids)
        for test in cancelled_tests:
            cancelled_test_total_cost += Decimal(test.price)

        # Cancelled test packages net amount
        cancelled_package_total_cost = 0
        cancelled_lab_patient_packages = LabPatientPackages.objects.filter(patient=patient, id__in=test_package_ids)

        for test_package in cancelled_lab_patient_packages:
            tests = test_package.lab_tests.all()
            if all(test.status_id.name == "Cancelled" for test in tests):
                pass
            else:
                cancelled_package_total_cost += test_package.offer_price or 0

        # all Cancelled tests and test packages net amount
        cancelled_tests_and_test_packages_total_cost = cancelled_test_total_cost + cancelled_package_total_cost

        if cancelled_tests_and_test_packages_total_cost != 0:
            cost_difference = tests_and_packages_total_cost - cancelled_tests_and_test_packages_total_cost
            net_total = cost_difference-invoice_total_discount
            if net_total < 0:
                net_total = 0

            refund_max_limit = invoice_total_paid - invoice_total_refund - net_total


        else:
            refund_max_limit = invoice_total_paid - invoice_total_refund - invoice_total_due

        response_data = {
            "refund_max_limit": refund_max_limit
        }

        return Response(response_data, status=status.HTTP_200_OK)



def get_lab_staff_from_request(request):
    client=request.client
    if client:
        user=request.user
        lab_staff = LabStaff.objects.get(mobile_number=user.phone_number)
        return lab_staff


class PaymentModePatientReportView(APIView):
    def get(self, request):
        # Retrieve filter parameters
        start_date = request.GET.get('date_range_after', None)
        end_date = request.GET.get('date_range_before', None)

        # Parse dates
        if start_date and end_date:
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
            end_date = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
        else:
            return Response({"error": "Please provide a valid start_date and end_date."}, status=400)

        patients = Patient.objects.filter(added_on__range=[start_date, end_date])
        receipts = LabPatientReceipts.objects.filter(patient__in=patients).prefetch_related('payments')

        grouped_data = {}
        for receipt in receipts:
            for payment in receipt.payments.all():
                pay_mode = payment.pay_mode.name  # Assuming `pay_mode` has a `name` field
                if pay_mode not in grouped_data:
                    grouped_data[pay_mode] = []
                grouped_data[pay_mode].append({
                    "pay_mode": pay_mode,
                    "patient_name": receipt.patient.name,
                    "age": receipt.patient.age,
                    "bill_no": receipt.invoiceid.invoice_id,
                    "receipt_id": receipt.Receipt_id,
                    "date": receipt.added_on.date(),
                    "referral_doctor": receipt.patient.referral_doctor.name if receipt.patient.referral_doctor else None,
                    "amount_paid": payment.paid_amount,
                })

        # Generate HTML content grouped by payment mode
        html_content = f'''
                    <table border="1" style="border-collapse: collapse; width: 100%;">
                        <tr>
                            <th colspan="8" class="text-center py-1" style="padding: 5px;">Pay Mode Wise Collection Report</th>
                        </tr>
                        <tr>
                            <th colspan="8" class="text-center py-1" style="padding: 5px;">Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}</th>
                        </tr>
                '''

        for pay_mode, records in grouped_data.items():
            # Add the payment mode row
            html_content += f'''
                        <tr>
                            <th colspan="8" style="text-align:center; padding: 5px; background-color:#d3d3d3;">{pay_mode} Collection</th>
                        </tr>
                        <tr>
                            <th style="text-align:center; padding: 5px; background-color:#e6e8e6;">Date</th>
                            <th style="text-align:center; padding: 5px; background-color:#e6e8e6;">Bill No</th>
                            <th style="text-align:center; padding: 5px; background-color:#e6e8e6;">Receipt ID</th>
                            <th style="text-align:center; padding: 5px; background-color:#e6e8e6;">Patient Name</th>
                            <th style="text-align:center; padding: 5px; background-color:#e6e8e6;">Age</th>
                            <th style="text-align:center; padding: 5px; background-color:#e6e8e6;">Referral Doctor</th>
                            <th style="text-align:center; padding: 5px; background-color:#e6e8e6;">Amount Paid</th>
                        </tr>
                    '''
            total_amount = 0  # Initialize total collection for the current payment mode

            # Add rows for each record under the current payment mode
            for record in records:
                html_content += f'''
                            <tr>
                                <td style="text-align:center; padding: 5px;">{record["date"]}</td>
                                <td style="text-align:center; padding: 5px;">{record["bill_no"]}</td>
                                <td style="text-align:center; padding: 5px;">{record["receipt_id"]}</td>
                                <td style="text-align:center; padding: 5px;">{record["patient_name"]}</td>
                                <td style="text-align:center; padding: 5px;">{record["age"]}</td>
                                <td style="text-align:center; padding: 5px;">{record["referral_doctor"]}</td>
                                <td style="text-align:center; padding: 5px;">{record["amount_paid"]}</td>
                            </tr>
                        '''
                total_amount += record["amount_paid"]  # Accumulate the amount paid

            # Add the total collection for the current payment mode
            html_content += f'''
                        <tr>
                            <td colspan="6" style="text-align:right; padding: 5px; background-color:#f2f2f2;"><strong>Total {pay_mode} Collection:</strong></td>
                            <td style="text-align:center; padding: 5px; background-color:#f2f2f2;"><strong>{total_amount}</strong></td>
                        </tr>
                    '''

        html_content += '</table>'

        return Response({'html_content': html_content})
        # return HttpResponse(html_content)

