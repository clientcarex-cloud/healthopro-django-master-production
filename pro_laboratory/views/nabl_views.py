from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, viewsets
from rest_framework.exceptions import ValidationError

from pro_laboratory.models.client_based_settings_models import BusinessControls
from pro_laboratory.models.global_models import LabStaffDefaultBranch
from pro_laboratory.models.patient_models import LabPatientTests
from pro_laboratory.serializers.nabl_serializers import LabPatientTestsSerializer
from pro_laboratory.filters import LabPatientTestsFilter
from django.db.models import Q


class LabNablReportListView(generics.ListAPIView):
    serializer_class = LabPatientTestsSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = LabPatientTestsFilter

    def get_queryset(self):
        user = self.request.user
        controls = BusinessControls.objects.first()
        if controls and controls.multiple_branches:
            default_branch_obj = LabStaffDefaultBranch.objects.get(lab_staff__mobile_number=user.phone_number)
            default_branch = default_branch_obj.default_branch.all()
            queryset = LabPatientTests.objects.filter(branch__in=default_branch,status_id__in=[3, 13, 17])
        else:
            queryset = LabPatientTests.objects.filter(status_id__in=[3, 13, 17])

        query = self.request.query_params.get('q', None)
        sort = self.request.query_params.get('sort', None)
        if query is not None:
            search_query = (Q(name__icontains=query) | Q(patient__name__icontains=query))
            queryset = queryset.filter(search_query)

        if sort == '-added_on':
            queryset = queryset.order_by('-added_on')
        if sort == 'added_on':
            queryset = queryset.order_by('added_on')
        return queryset
