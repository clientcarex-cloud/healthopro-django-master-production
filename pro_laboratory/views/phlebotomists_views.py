from datetime import timedelta, datetime

from django.db.models import Q, Count, Case, When, F
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from django_tenants.utils import schema_context
from rest_framework import viewsets, generics

from healtho_pro_user.views.business_views import get_business_from_client, get_client_from_business
from pro_laboratory.filters import LabPhlebotomistFilter, LabPhlebotomistAnalyticsFilter, PatientFilter, \
    LabPhlebotomistListFilter
from pro_laboratory.models.client_based_settings_models import BusinessControls
from pro_laboratory.models.global_models import LabStaffDefaultBranch
from pro_laboratory.models.labtechnicians_models import LabTechnicians
from pro_laboratory.models.patient_models import LabPatientTests, Patient
from pro_laboratory.models.sourcing_lab_models import SourcingLabTestsTracker, SourcingLabRegistration
from pro_laboratory.serializers.phlebotomists_serializers import LabPatientTestsSerializer, \
    LabPhlebotomistAnalyticsSerializer, PatientTestSerializer, LabTestsSerializer, PatientGetSerializer, \
    PatientListSerializer
from pro_laboratory.models.phlebotomists_models import LabPhlebotomist
from pro_laboratory.serializers.phlebotomists_serializers import LabPhlebotomistSerializer
from rest_framework.response import Response
from rest_framework import status

from pro_universal_data.models import ULabTestStatus


class LabPhlebotomistsViewSet(viewsets.ModelViewSet):
    queryset = LabPhlebotomist.objects.all()
    serializer_class = LabPhlebotomistSerializer

    def generate_accession_number(self, lab_phlebotomist):
        if lab_phlebotomist.is_collected:
            test_time = lab_phlebotomist.LabPatientTestID.added_on.replace(second=0, microsecond=0)
            minute_start = test_time
            minute_end = test_time + timedelta(minutes=1)
            current_sample = lab_phlebotomist.LabPatientTestID.LabGlobalTestId.sample
            same_sample_tests = LabPhlebotomist.objects.filter(
                LabPatientTestID__patient=lab_phlebotomist.LabPatientTestID.patient,
                LabPatientTestID__LabGlobalTestId__sample=current_sample,
                LabPatientTestID__LabGlobalTestId__sample__isnull=False,
                id__lt=lab_phlebotomist.id,
                assession_number__isnull=False,
                LabPatientTestID__added_on__range=(minute_start, minute_end)
            )
            if same_sample_tests.exists():
                return same_sample_tests.last().assession_number
            else:
                return f"S{lab_phlebotomist.LabPatientTestID.patient.id}{lab_phlebotomist.id}"
        return None

    def create(self, request=None, phlebotomist_data=None, *args, **kwargs):
        if request:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            validated_data = serializer.validated_data
        else:
            validated_data = phlebotomist_data
        print(validated_data)

        lab_test = validated_data.pop('LabPatientTestID')
        is_collected = validated_data.get('is_collected', False)
        if lab_test:
            patient = lab_test.patient
            sample = lab_test.LabGlobalTestId.sample
            sample_tests = LabPatientTests.objects.filter(LabGlobalTestId__sample=sample, patient=patient).order_by(
                'id')

            if lab_test.status_id.name == 'Cancelled':
                return Response({"Error": "Cannot take sample, for a Cancelled Test"})
            else:
                if lab_test.LabGlobalTestId.sample is None:
                    lab_phlebotomist = LabPhlebotomist.objects.create(LabPatientTestID=lab_test, **validated_data)
                    if is_collected:
                        lab_patient_test = lab_phlebotomist.LabPatientTestID
                        patient_status_id = lab_patient_test.status_id
                        if patient_status_id == ULabTestStatus.objects.get(id=1):
                            new_status = 'Sample Collected'
                        elif patient_status_id == ULabTestStatus.objects.get(id=10):
                            new_status = 'Emergency (Sample Collected)'
                        elif patient_status_id == ULabTestStatus.objects.get(id=14):
                            new_status = 'Urgent (Sample Collected)'
                        else:
                            new_status = 'Sample Collected'

                        lab_patient_test.status_id = ULabTestStatus.objects.get(name=new_status)
                        lab_patient_test.save()

                        if not lab_patient_test.is_outsourcing:
                            LabTechnicians.objects.create(LabPatientTestID=lab_patient_test)
                        else:
                            tracker = SourcingLabTestsTracker.objects.create(sourcing_lab=lab_patient_test.sourcing_lab,
                                                                             patient_id=lab_patient_test.patient.id,
                                                                             lab_patient_test=lab_patient_test.id,
                                                                             to_send=True)

                    accession_number = self.generate_accession_number(lab_phlebotomist)
                    if accession_number:
                        lab_phlebotomist.assession_number = accession_number
                        lab_phlebotomist.save(update_fields=['assession_number'])
                    serializer = LabPhlebotomistSerializer(lab_phlebotomist)
                    return Response(serializer.data)
                else:
                    for test in sample_tests:
                        if LabPhlebotomist.objects.filter(LabPatientTestID=test).exists():
                            continue
                        lab_phlebotomist = LabPhlebotomist.objects.create(LabPatientTestID=test, **validated_data)

                        if is_collected:
                            lab_patient_test = lab_phlebotomist.LabPatientTestID
                            patient_status_id = lab_patient_test.status_id
                            if patient_status_id == ULabTestStatus.objects.get(id=1):
                                new_status = 'Sample Collected'
                            elif patient_status_id == ULabTestStatus.objects.get(id=10):
                                new_status = 'Emergency (Sample Collected)'
                            elif patient_status_id == ULabTestStatus.objects.get(id=14):
                                new_status = 'Urgent (Sample Collected)'
                            else:
                                new_status = 'Sample Collected'

                            lab_patient_test.status_id = ULabTestStatus.objects.get(name=new_status)
                            lab_patient_test.save()

                            if not lab_patient_test.is_outsourcing:
                                LabTechnicians.objects.create(LabPatientTestID=lab_patient_test)

                            else:
                                tracker = SourcingLabTestsTracker.objects.create(
                                    sourcing_lab=lab_patient_test.sourcing_lab,
                                    patient_id=lab_patient_test.patient.id,
                                    lab_patient_test=lab_patient_test.id, to_send=True)

                        accession_number = self.generate_accession_number(lab_phlebotomist)
                        if accession_number:
                            lab_phlebotomist.assession_number = accession_number
                            lab_phlebotomist.save(update_fields=['assession_number'])

                        serializer = LabPhlebotomistSerializer(lab_phlebotomist)
                    return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        return Response({'Error': 'Method not Allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


class LabPhlebotomistListView(generics.ListAPIView):
    serializer_class = LabPatientTestsSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = LabPhlebotomistFilter

    def get_queryset(self):
        # queryset = LabPatientTests.objects.filter(status_id__in=[1, 4, 5, 10, 12, 14, 16])
        user = self.request.user

        controls = BusinessControls.objects.first()
        if controls and controls.multiple_branches:
            default_branch_obj = LabStaffDefaultBranch.objects.get(lab_staff__mobile_number=user.phone_number)
            default_branch = default_branch_obj.default_branch.all()
            queryset = LabPatientTests.objects.filter(branch__in=default_branch)

        else:
            queryset = LabPatientTests.objects.all()

        queryset = LabPatientTests.objects.all()
        query = self.request.query_params.get('q', None)
        sort = self.request.query_params.get('sort', None)
        status_ids = self.request.query_params.get('status_id')
        departments_details = self.request.query_params.get('departments', [])

        if query is not None:
            search_query = Q(patient__name__icontains=query) | Q(name__icontains=query) | Q(
                phlebotomist__assession_number__icontains=query)
            queryset = queryset.filter(search_query)

        if status_ids:
            status_ids_list = status_ids.split(',')
            sample_collected_status_ids = ['18', '19', '20']
            if len(status_ids_list) == len(sample_collected_status_ids):
                current_date = timezone.now().date()
                queryset = queryset.filter(
                    status_id__in=status_ids_list,
                    phlebotomist__collected_at__date=current_date
                )
            else:
                queryset = queryset.filter(status_id__in=status_ids_list)

        if departments_details:
            departments = [department.strip() for department in departments_details.split(',') if department.strip()]
            department_query = Q(department__id__in=departments)

            queryset = queryset.filter(department_query)

        if sort == '-added_on':
            queryset = queryset.order_by('-added_on')
        if sort == 'added_on':
            queryset = queryset.order_by('added_on')

        return queryset


class AllPatientsTestsView(generics.ListAPIView):
    queryset = Patient.objects.all()
    serializer_class = PatientTestSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = LabPhlebotomistListFilter

    def get_queryset(self):
        queryset = Patient.objects.all()
        sort = self.request.query_params.get('sort', None)
        departments_details = self.request.query_params.get('departments', [])

        if departments_details:
            departments = [department.strip() for department in departments_details.split(',') if department.strip()]
            queryset = queryset.filter(labpatienttests__department__id__in=departments)

        if sort == '-added_on':
            queryset = queryset.order_by('-added_on')
        elif sort == 'added_on':
            queryset = queryset.order_by('added_on')

        queryset = queryset.distinct()

        return queryset


class PatientListView(generics.ListAPIView):
    queryset = Patient.objects.all()
    serializer_class = PatientListSerializer


    def get_queryset(self):
        queryset = Patient.objects.all()
        date = self.request.query_params.get('date')
        date_range_after = self.request.query_params.get('date_range_after')
        date_range_before = self.request.query_params.get('date_range_before')
        sort = self.request.query_params.get('sort', None)

        if date:
            queryset = queryset.filter(added_on__date=date)
        if date_range_after and date_range_before:
            try:
                start_date = datetime.strptime(date_range_after, "%Y-%m-%d")
                end_date = datetime.strptime(date_range_before, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
                queryset = queryset.filter(
                    added_on__range=[start_date, end_date]
                )
            except ValueError:
                pass

        if sort == '-added_on':
            queryset = queryset.order_by('-added_on')
        elif sort == 'added_on':
            queryset = queryset.order_by('added_on')

        queryset = queryset.distinct()
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        transformed_data = []
        status_ids = self.request.query_params.get('status_id')
        departments_details = self.request.query_params.get('departments', [])
        query = self.request.query_params.get('q', None)

        for patient in queryset:
            tests = LabPatientTests.objects.filter(patient=patient)

            if status_ids:
                status_ids_list = status_ids.split(',')
                tests = tests.filter(status_id__in=status_ids_list)

            if departments_details:
                departments = [department.strip() for department in departments_details.split(',') if
                               department.strip()]
                tests = tests.filter(department__id__in=departments)
            if query is not None:
                search_query = Q(name__icontains=query) | Q(patient__name__icontains=query) | Q(
                    phlebotomist__assession_number__icontains=query)
                tests = tests.filter(search_query)

            grouped_tests = {}

            for test in tests:
                sample_type = test.LabGlobalTestId.sample
                if sample_type is None:
                    sample_type = 'No Sample'

                if sample_type not in grouped_tests:
                    grouped_tests[sample_type] = []
                grouped_tests[sample_type].append(LabTestsSerializer(test).data)

            for sample_type, tests in grouped_tests.items():
                patient_data = {
                    **PatientListSerializer(patient).data,
                    'tests': tests
                }
                transformed_data.append(patient_data)

        page = self.paginate_queryset(transformed_data)
        return self.get_paginated_response(page)