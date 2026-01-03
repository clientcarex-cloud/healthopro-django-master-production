from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from django.db.models import Count, Case, When, Sum, F, Q
from pro_laboratory.filters import LabDoctorAuthorizationFilter, \
    LabDoctorAuthorizationAnalyticsFilter
from pro_laboratory.models.doctorAuthorization_models import LabDrAuthorization
from pro_laboratory.models.patient_models import LabPatientTests
from pro_laboratory.serializers.doctorAuthorization_serializers import LabPatientTestsSerializer, \
    AuthorizationAnalyticsSerializer
from pro_laboratory.serializers.doctorAuthorization_serializers import LabDrAuthorizationSerializer
from rest_framework import generics


class LabDoctorAuthorizationApprovalViewSet(viewsets.ModelViewSet):
    queryset = LabDrAuthorization.objects.all()
    serializer_class = LabDrAuthorizationSerializer


class LabDoctorAuthorizationView(generics.ListAPIView):
    serializer_class = LabPatientTestsSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = LabDoctorAuthorizationFilter

    def get_queryset(self):
        queryset = LabPatientTests.objects.filter(is_authorization=True)
        query = self.request.query_params.get('q', None)
        sort = self.request.query_params.get('sort', None)
        status_ids = self.request.query_params.get('status_id', None)
        if query is not None:
            search_query = (Q(name__icontains=query) | Q(patient__name__icontains=query) | Q(
                department__name__icontains=query))
            queryset = queryset.filter(search_query)

        if status_ids is not None:
            status_ids_list = status_ids.split(',')
            queryset = queryset.filter(status_id__in=status_ids_list)

        if sort == '-added_on':
            queryset = queryset.order_by('-added_on')
        if sort == 'added_on':
            queryset = queryset.order_by('added_on')

        queryset = queryset.filter(labtechnician__isnull=False)

        return queryset
