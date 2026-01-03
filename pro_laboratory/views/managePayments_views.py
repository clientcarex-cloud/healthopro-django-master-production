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




