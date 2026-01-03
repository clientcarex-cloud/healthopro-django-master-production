from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics
from pro_laboratory.filters import PatientFilter
from pro_laboratory.models.client_based_settings_models import BusinessControls
from pro_laboratory.models.global_models import LabStaffDefaultBranch
from pro_laboratory.models.patient_models import Patient
from pro_laboratory.serializers.managePayments_serializers import PatientSerializer


class ManagePaymentListView(generics.ListAPIView):
    serializer_class = PatientSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = PatientFilter

    def get_queryset(self):
        user = self.request.user
        controls = BusinessControls.objects.first()
        if controls and controls.multiple_branches:
            default_branch_obj = LabStaffDefaultBranch.objects.get(lab_staff__mobile_number=user.phone_number)
            default_branch = default_branch_obj.default_branch.all()
            queryset = Patient.objects.filter(branch__in=default_branch)
        else:
            queryset = Patient.objects.all()

        query = self.request.query_params.get('q', None)
        sort = self.request.query_params.get('sort', None)
        payment_status = self.request.query_params.get('payment_status', None)
        lab_staff = self.request.query_params.get('lab_staff', None)

        if lab_staff:
            queryset = queryset.filter(created_by=lab_staff)

        if query is not None:
            search_query = (Q(name__icontains=query) | Q(labpatienttests__name__icontains=query) | Q(
                labpatienttests__short_code__icontains=query))
            queryset = queryset.filter(search_query)

        if payment_status:
            if payment_status.lower() == 'paid':
                queryset = queryset.filter(labpatientinvoice__total_paid__gt=0, labpatientinvoice__total_due=0,
                                           labpatientinvoice__total_refund=0)
            elif payment_status.lower() == 'due':
                queryset = queryset.filter(labpatientinvoice__total_due__gt=0, labpatientinvoice__total_refund=0,
                                           labpatientinvoice__total_paid=0)
            elif payment_status.lower() == 'refund':
                queryset = queryset.filter(labpatientinvoice__total_refund__gt=0)

            elif payment_status.lower() == 'partial':
                queryset = queryset.filter(labpatientinvoice__total_due__gt=0, labpatientinvoice__total_refund=0,
                                           labpatientinvoice__total_paid__gt=0)
            if sort == '-added_on':
                queryset = queryset.order_by('-added_on')
            if sort == 'added_on':
                queryset = queryset.order_by('added_on')

        return queryset.distinct()





from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from pro_laboratory.models.patient_models import (
    Patient, LabPatientTests, LabPatientPackages, LabPatientReceipts,
    LabPatientRefund, LabPatientInvoice, HomeService, PatientOTP,
    LabPatientPayments
)
from pro_hospital.models.patient_wise_models import (
    PatientPackages as HospitalPatientPackages,
    PatientDoctorConsultationDetails,
    PatientServices,
    IPRoomBooking,
    PatientVitals
)
from pro_hospital.models.universal_models import GlobalRoomBeds

class DeletePatientFinanceAPIView(APIView):
    def post(self, request, *args, **kwargs):
        patient_ids = request.data.get('ids', [])
        if not patient_ids:
            return Response({"error": "No patient IDs provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # 1. Fetch Patients
                patients = Patient.objects.filter(id__in=patient_ids)
                if not patients.exists():
                     return Response({"message": "No patients found for the provided IDs"}, status=status.HTTP_404_NOT_FOUND)

                # 2. Delete Related Data manually due to PROTECT
                
                # --- Pro Laboratory Data ---
                # Delete Tests
                LabPatientTests.objects.filter(patient__in=patients).delete()

                # Delete Packages
                LabPatientPackages.objects.filter(patient__in=patients).delete()

                # Delete Receipts
                receipts = LabPatientReceipts.objects.filter(patient__in=patients)
                # Optional: Delete orphaned payments if needed.
                # Since LabPatientPayments has no FK to Receipt, deleting them relies on collecting IDs from receipts.
                # payments_to_delete_ids = []
                # for r in receipts:
                #     payments_to_delete_ids.extend(r.payments.values_list('id', flat=True))
                # if payments_to_delete_ids:
                #    LabPatientPayments.objects.filter(id__in=payments_to_delete_ids).delete()
                
                receipts.delete()

                # Delete Refunds
                LabPatientRefund.objects.filter(patient__in=patients).delete()

                # --- Pro Hospital Data ---
                # Hospital Patient Packages
                HospitalPatientPackages.objects.filter(patient__in=patients).delete()

                # Consultation Details
                PatientDoctorConsultationDetails.objects.filter(patient__in=patients).delete()

                # Patient Services
                PatientServices.objects.filter(patient__in=patients).delete()

                # IP Room Booking
                IPRoomBooking.objects.filter(patient__in=patients).delete()

                # Patient Vitals
                PatientVitals.objects.filter(patient__in=patients).delete()

                # Global Room Beds - Update, don't delete
                GlobalRoomBeds.objects.filter(patient__in=patients).update(patient=None, is_booked=False)

                # --- Final Cleanup ---
                # Delete Invoices
                LabPatientInvoice.objects.filter(patient__in=patients).delete()

                # Delete HomeService
                HomeService.objects.filter(patient__in=patients).delete()

                # Finally, Delete Patients
                count, _ = patients.delete()

                return Response({"message": f"Successfully deleted {count} patient records and related finance/service data."}, status=status.HTTP_200_OK)

        except Exception as e:
            # Helpful error message for debugging
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
