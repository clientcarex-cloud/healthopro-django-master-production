import redis
from datetime import datetime, timedelta
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q, Count, Sum, F, OuterRef, Exists, Max
from django.db.models.functions import Coalesce
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import viewsets, generics
from rest_framework.views import APIView

from healtho_pro_user.models.users_models import HealthOProUser
from healtho_pro_user.serializers.users_serializers import UserSerializer
from pro_laboratory.filters import LabDoctorFilter
from pro_laboratory.models.doctorAuthorization_models import LabDrAuthorization
from pro_laboratory.models.doctors_models import LabDoctors, LabDoctorsType, ReferralAmountForDoctor, \
    DefaultsForDepartments, DoctorSpecializations
from pro_laboratory.models.global_models import LabGlobalTests, LabDoctorRole, LabStaff, LabMenuAccess, LabStaffRole, \
    LabStaffDefaultBranch
from pro_laboratory.models.labtechnicians_models import LabTechnicians
from pro_laboratory.models.patient_models import Patient, LabPatientTests
from pro_laboratory.models.user_permissions_models import UserPermissionsAccess
from pro_laboratory.serializers.doctors_serializers import LabDoctorsSerializer, LabDoctorsTypeSerializer, \
    ConsultingDoctorCountSerializer, ReferralDoctorCountSerializer, ReferralAmountForDoctorSerializer, \
    SyncDataForReferralDoctorSerializer, ReferralDoctorsMergingSerializer, ReferralDoctorBulkEditSerializer, \
    SearchForMatchingDoctorsSerializer, PatientWiseLabReferralDoctorsSerializer, DefaultsForDepartmentsSerializer, \
    DoctorSpecializationsSerializer
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import MultipleObjectsReturned
from pro_laboratory.views.global_views import LabStaffLoginActionViewSet


class LabDoctorsTypeViewSet(viewsets.ModelViewSet):
    queryset = LabDoctorsType.objects.all()
    serializer_class = LabDoctorsTypeSerializer


class LabDoctorsViewSet(viewsets.ModelViewSet):
    serializer_class = LabDoctorsSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = LabDoctorFilter

    def get_queryset(self):
        queryset = LabDoctors.objects.all()
        query = self.request.query_params.get('q', None)
        if query is not None:
            search_query = (Q(name__icontains=query) | Q(specialization__name__icontains=query))
            queryset = queryset.filter(search_query)
        return queryset

    def perform_create(self, serializer):
        serializer.save()
        instance = serializer.instance
        self.invalidate_cache(instance)

    def perform_update(self, serializer):
        instance = self.get_object()
        super().perform_update(serializer)
        self.invalidate_cache(instance)

    def perform_destroy(self, instance):
        super().perform_destroy(instance)
        self.invalidate_cache(instance)

    def invalidate_cache(self, instance):
        try:
            client_id = self.request.client
            if client_id:
                cache_key_prefix = f'lab_referral_doctors_{client_id}_*'
                keys_to_delete = [key for key in cache.keys(f'{cache_key_prefix}*')]
                for key in keys_to_delete:
                    cache.delete(key)
                    print(f'Deleted cache key: {key}')
        except Exception as e:
            print(f"Cache invalidation failed: {e}")


class ReferralAmountForDoctorViewSet(viewsets.ModelViewSet):
    queryset = ReferralAmountForDoctor.objects.all()
    serializer_class = ReferralAmountForDoctorSerializer

    def get_queryset(self):
        queryset = ReferralAmountForDoctor.objects.all()
        doctor_id = self.request.query_params.get('doctor_id', None)
        department_id = self.request.query_params.get('department_id', None)
        query_param_tests = self.request.query_params.get('tests')

        if query_param_tests:
            test_ids = [int(test_id) for test_id in query_param_tests.split(',')]
            queryset = ReferralAmountForDoctor.objects.filter(lab_test__id__in=test_ids)

        if doctor_id is not None:
            queryset = queryset.filter(referral_doctor=doctor_id)

        if department_id is not None:
            queryset = queryset.filter(Q(lab_test__department_id=department_id))

        return queryset

    def create(self, request, *args, **kwargs):
        referral_doctor_id = request.data.get('referral_doctor')
        if not referral_doctor_id:
            return Response({'error': 'Referral doctor ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            referral_doctor = LabDoctors.objects.get(id=referral_doctor_id)
        except LabDoctors.DoesNotExist:
            return Response({'error': 'Referral doctor not found'}, status=status.HTTP_404_NOT_FOUND)

        if referral_doctor.doctor_type_id.id==1:
            lab_tests = LabGlobalTests.objects.all()
        else:
            lab_tests = LabGlobalTests.objects.filter(department__department_flow_type__id=2)
        created_objects = []

        for test in lab_tests:
            referral_amount_for_doctor = ReferralAmountForDoctor(
                referral_doctor=referral_doctor,
                referral_amount=0,
                is_percentage=False,
                lab_test=test
            )
            referral_amount_for_doctor.save()
            created_objects.append(referral_amount_for_doctor)

        serializer = self.get_serializer(created_objects, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LabConsultingDoctorsListView(generics.ListAPIView):
    serializer_class = ConsultingDoctorCountSerializer
    # filter_backends = [DjangoFilterBackend]
    # filterset_class = LabDoctorFilter

    def get_queryset(self):
        queryset = LabDoctors.objects.filter(doctor_type_id=2)
        query = self.request.query_params.get('q', None)
        department = self.request.query_params.get('department', None)
        mobile_number = self.request.query_params.get('mobile_number', None)

        if mobile_number:
            queryset = queryset.filter(mobile_number__icontains=mobile_number)
        if query is not None:
            search_query = (Q(name__icontains=query) | Q(specialization__name__icontains=query) | Q (department__name__icontains=query) | Q(mobile_number__icontains=query))
            queryset = queryset.filter(search_query)
        if department:
            queryset = queryset.filter(department__name__icontains=department)

        queryset = queryset.order_by('name')
        return queryset


class LabReferralDoctorsListView(generics.ListAPIView):
    serializer_class = ReferralDoctorCountSerializer
    # filter_backends = [DjangoFilterBackend]
    # filterset_class = LabDoctorFilter

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['date'] = self.request.query_params.get('date')
        context['date_range_after'] = self.request.query_params.get('date_range_after')
        context['date_range_before'] = self.request.query_params.get('date_range_before')
        return context

    def get_queryset(self):
        try:
            client_id = self.request.client
            query = self.request.query_params.get('q', '')
            sort = self.request.query_params.get('sort', '')
            marketing_executive = self.request.query_params.get('marketing_executive', '')
            cache_key = f'lab_referral_doctors_{client_id}_{query}_{marketing_executive}_{sort}_*'
            cache_data = cache.get(cache_key)
            if cache_data:
                return cache_data
            queryset = LabDoctors.objects.filter(doctor_type_id=1).annotate(
                last_patient_date=Max('patient__added_on')
            )

            if marketing_executive:
                queryset = queryset.filter(marketing_executive__id=marketing_executive)

            if query:
                search_query = (Q(name__icontains=query) |
                                Q(specialization__name__icontains=query) |
                                Q(mobile_number__icontains=query))
                queryset = queryset.filter(search_query)

            if sort == '-added_on':
                queryset = queryset.order_by('-added_on', 'name')
            elif sort == 'added_on':
                queryset = queryset.order_by('added_on', 'name')

            elif sort == '-last_patient_date':
                queryset = queryset.order_by('-last_patient_date', 'name')
            elif sort == 'last_patient_date':
                queryset = queryset.order_by('last_patient_date', 'name')
            elif sort == 'name':
                queryset = queryset.order_by('name')
            elif sort == '-name':
                queryset = queryset.order_by('-name')
            else:
                queryset = queryset.order_by('name')

            cache.set(cache_key, queryset)
            return queryset

        except Exception as e:
            query = self.request.query_params.get('q', '')
            sort = self.request.query_params.get('sort', '')
            marketing_executive = self.request.query_params.get('marketing_executive', '')

            queryset = LabDoctors.objects.filter(doctor_type_id=1).annotate(
                last_patient_date=Max('patient__added_on'))

            if marketing_executive:
                queryset = queryset.filter(marketing_executive__id=marketing_executive)

            if query:
                search_query = (Q(name__icontains=query) |
                                Q(specialization__name__icontains=query) |
                                Q(mobile_number__icontains=query))
                queryset = queryset.filter(search_query)

            if sort == '-added_on':
                queryset = queryset.order_by('-added_on')
            elif sort == 'added_on':
                queryset = queryset.order_by('added_on')
            elif sort == '-last_patient_date':
                queryset = queryset.order_by('-last_patient_date', 'name')
            elif sort == 'last_patient_date':
                queryset = queryset.order_by('last_patient_date', 'name')
            elif sort == 'name':
                queryset = queryset.order_by('name')
            elif sort == '-name':
                queryset = queryset.order_by('-name')
            else:
                queryset = queryset.order_by('name')

            return queryset


class PatientWiseLabReferralDoctorsListView(generics.ListAPIView):
    serializer_class = PatientWiseLabReferralDoctorsSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = LabDoctorFilter

    def get_queryset(self):
        start_date = self.request.query_params.get('date_range_after', None)
        end_date = self.request.query_params.get('date_range_before', None)
        query = self.request.query_params.get('q', None)
        marketing_executive = self.request.query_params.get('marketing_executive', None)
        doctor_type_id = self.request.query_params.get('d_id', None)

        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')

            if not end_date:
                end_date = start_date + timedelta(days=1) - timedelta(seconds=1)  # Last second of the day
            else:
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
                end_date = datetime.combine(end_date, datetime.max.time())


        except ValueError:
            return LabDoctors.objects.none()
        if doctor_type_id == '1':
            patients_in_range = Patient.objects.filter(added_on__range=(start_date, end_date))

            doctors = LabDoctors.objects.filter(patient__in=patients_in_range).distinct()

            # Annotate each doctor with the total number of patients and the total amount paid within the date range
            doctors = doctors.annotate(
                total_patients=Count('patient', filter=Q(patient__in=patients_in_range)),
                total_paid=Sum('patient__labpatientinvoice__total_cost', filter=Q(patient__in=patients_in_range))
            )

        else:
            patients_in_range = Patient.objects.filter(added_on__range=(start_date, end_date))

            lab_tests = LabPatientTests.objects.filter(patient__in=patients_in_range,
                department__department_flow_type__id=2
            )

            lab_technicians = LabTechnicians.objects.filter(LabPatientTestID__in=lab_tests)
            doctors = LabDoctors.objects.filter(id__in=lab_technicians.values_list('consulting_doctor', flat=True))

            # Annotate with distinct patients and total paid
            doctors = doctors.annotate(
                total_patients=Count('labtechnicians__LabPatientTestID__patient',
                                     filter=Q(labtechnicians__LabPatientTestID__patient__in=patients_in_range),
                                     distinct=True),
                total_paid=Sum('labtechnicians__LabPatientTestID__patient__labpatientinvoice__total_cost',
                               filter=Q(labtechnicians__LabPatientTestID__patient__in=patients_in_range),
                               distinct=True)
            )

        if marketing_executive:
            doctors = doctors.filter(marketing_executive__id=marketing_executive)

        if query:
            search_query = (Q(name__icontains=query) | Q(specialization__name__icontains=query) | Q(
                mobile_number__icontains=query))

            doctors = doctors.filter(search_query)

        doctors = doctors.order_by('name')
        return doctors

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class ConsultantDoctorsStatsListView(generics.ListAPIView):
    def get(self, request, *args, **kwargs):
        doctor_count = LabDoctors.objects.filter(doctor_type_id=2).count()
        department_count = LabDoctors.objects.filter(doctor_type_id=2).values('department').distinct().count()
        specialization_count = LabDoctors.objects.filter(doctor_type_id=2).values('specialization').distinct().count()

        data = {
            'doctor_count': doctor_count,
            'department_count': department_count,
            'specialization_count': specialization_count
        }

        return Response(data)


class ReferralDoctorsStatsListView(generics.ListAPIView):
    def get(self, request, *args, **kwargs):
        doctor_count = LabDoctors.objects.filter(doctor_type_id=1).count()
        department_count = LabDoctors.objects.filter(doctor_type_id=1).values('department').distinct().count()
        specialization_count = LabDoctors.objects.filter(doctor_type_id=1).values('specialization').distinct().count()
        active_doctors_count = LabDoctors.objects.filter(doctor_type_id=1, is_active=True).count()

        data = {
            'doctor_count': doctor_count,
            'department_count': department_count,
            'specialization_count': specialization_count,
            'active_doctors_count': active_doctors_count
        }
        return Response(data)


class SyncDataForReferralDoctorViewset(viewsets.ModelViewSet):
    queryset = ReferralAmountForDoctor.objects.all()
    serializer_class = SyncDataForReferralDoctorSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            source_doctor_id = serializer.validated_data.get('source_doctor_id')
            target_doctor_id = serializer.validated_data.get('target_doctor_id')

        try:
            source_doctor_data = ReferralAmountForDoctor.objects.filter(referral_doctor_id=source_doctor_id)
            target_doctor = LabDoctors.objects.get(id=target_doctor_id)

            ReferralAmountForDoctor.objects.filter(referral_doctor=target_doctor).delete()

            for data in source_doctor_data:
                ReferralAmountForDoctor.objects.create(
                    referral_doctor=target_doctor,
                    referral_amount=data.referral_amount,
                    is_percentage=data.is_percentage,
                    lab_test=data.lab_test
                )
            serialized_data = ReferralAmountForDoctorSerializer(target_doctor.referralamountfordoctor_set.all(),
                                                                many=True)
            return Response(serialized_data.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ReferralDoctorsMergingViewSet(viewsets.ModelViewSet):
    serializer_class = ReferralDoctorsMergingSerializer

    def get_queryset(self):
        return []

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            main_doctor_id = serializer.validated_data.get('main_doctor_id')
            duplicate_doctor_ids = serializer.validated_data.get('duplicate_doctor_ids')

            merged_data = {}

            try:
                with transaction.atomic():
                    main_doctor = LabDoctors.objects.get(id=main_doctor_id)
                    Patient.objects.filter(referral_doctor__in=duplicate_doctor_ids).update(referral_doctor=main_doctor)

                    # Iterate through duplicate doctors and update them using save() to trigger signals
                    duplicate_doctors = LabDoctors.objects.filter(id__in=duplicate_doctor_ids)
                    for duplicate_doctor in duplicate_doctors:
                        duplicate_doctor.is_duplicate = True
                        duplicate_doctor.is_active = False
                        duplicate_doctor.save()  # This will trigger the post_save signal
                return Response("Data merged successfully", status=status.HTTP_200_OK)
            except LabDoctors.DoesNotExist:
                return Response({'error': 'Main doctor not found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ReferralDoctorsBulkEditViewSet(viewsets.ModelViewSet):
    queryset = ReferralAmountForDoctor.objects.all()
    serializer_class = ReferralAmountForDoctorSerializer

    def create(self, request, *args, **kwargs):
        referral_doctor_id = request.data.get('referral_doctor')
        updates = request.data.get('lab_tests_data', [])

        if not referral_doctor_id or not updates:
            return Response({'error': 'Referral doctor ID and updates are required'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            referral_doctor = LabDoctors.objects.get(id=referral_doctor_id)
        except LabDoctors.DoesNotExist:
            return Response({'error': 'Referral doctor not found'}, status=status.HTTP_404_NOT_FOUND)

        updated_objects = []

        for update in updates:
            lab_test_id = update.get('lab_test')
            referral_amount = update.get('referral_amount')
            is_percentage = update.get('is_percentage', False)

            if lab_test_id is None or referral_amount is None:
                continue

            try:
                lab_test = LabGlobalTests.objects.get(id=lab_test_id)

                try:
                    referral_object, created = ReferralAmountForDoctor.objects.get_or_create(
                        referral_doctor=referral_doctor, lab_test=lab_test)
                except MultipleObjectsReturned:
                    referral_objects = ReferralAmountForDoctor.objects.filter(
                        referral_doctor=referral_doctor, lab_test=lab_test)

                    referral_object = referral_objects.first()
                    created = False

                referral_object.referral_amount = referral_amount
                referral_object.is_percentage = is_percentage
                referral_object.save()
                updated_objects.append(referral_object)
            except LabGlobalTests.DoesNotExist:
                continue

        serializer = self.serializer_class(updated_objects, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SearchForMatchingDoctors(generics.ListAPIView):
    # serializer_class = UserSerializer
    serializer_class = SearchForMatchingDoctorsSerializer

    def get_queryset(self):
        queryset = HealthOProUser.objects.filter(user_type=1)
        name = self.request.query_params.get('name', None)
        mobile_number = self.request.query_params.get('mobile_number', None)
        geo_area = self.request.query_params.get('geo_area', None)

        if geo_area:
            queryset = queryset.filter(city__icontains=geo_area)

        if mobile_number is not None:
            queryset = queryset.filter(username__icontains=mobile_number)

        if name is not None:
            queryset = queryset.filter(Q(full_name__icontains=name))

        if not (geo_area or mobile_number or name):
            queryset = HealthOProUser.objects.none()

        return queryset


class DefaultsForDepartmentsViewSet(viewsets.ModelViewSet):
    queryset = DefaultsForDepartments.objects.all()
    serializer_class = DefaultsForDepartmentsSerializer


class DoctorSpecializationsViewSet(viewsets.ModelViewSet):
    queryset = DoctorSpecializations.objects.all()
    serializer_class = DoctorSpecializationsSerializer

class DoctorLoginAPIView(APIView):
    def post(self, request):
        doctor_id = self.request.data.get('doctor_id')
        menus = self.request.data.get('lab_menu')
        permissions = self.request.data.get('permissions')
        branches = self.request.data.get('branches')
        number = self.request.data.get('number')
        can_login = self.request.data.get('can_login')

        # Retrieve the doctor details
        doctor_details = LabDoctors.objects.get(id=doctor_id)

        if doctor_details:
            # Get or create the LabStaffRole instance
            role_obj, created = LabStaffRole.objects.get_or_create(name='Doctor')

            lab_staff = LabStaff.objects.filter(mobile_number=doctor_details.mobile_number).first()
            lab_staff.role = role_obj
            lab_staff.save()
            if not lab_staff:
                lab_staff = LabStaff.objects.create(
                    name=doctor_details.name,
                    mobile_number=doctor_details.mobile_number,
                    is_active=True,
                    is_superadmin=False,
                    role=role_obj  # Pass only the LabStaffRole instance
                )
            if branches:
                lab_staff.branches.set(branches)
                default_branch = LabStaffDefaultBranch.objects.filter(lab_staff=lab_staff).first()
                if not default_branch:
                    default_branch = LabStaffDefaultBranch.objects.create(lab_staff=lab_staff)
                default_branch.default_branch.set(branches)

            # Call LabStaffLoginActionViewSet to give login access
            lab_staff_login_access_api = LabStaffLoginActionViewSet()
            staff_login_access = lab_staff_login_access_api.create(
                client=request.client,
                lab_staff=lab_staff,
                can_login=can_login
            )
            lab_menu_access = LabMenuAccess.objects.filter(lab_staff=lab_staff).first()
            if not lab_menu_access:
                lab_menu_access = LabMenuAccess.objects.create(
                    is_access=True,
                    lab_staff=lab_staff
                )
            if menus:
                lab_menu_access.lab_menu.set(menus)

            user_permissions = UserPermissionsAccess.objects.filter(lab_staff=lab_staff).first()
            if not user_permissions:
                user_permissions = UserPermissionsAccess.objects.create(
                    is_access=True,
                    lab_staff=lab_staff,
                    number= number if number else 0
                )
            if permissions:
                user_permissions.permissions.set(permissions)

        return Response({"message": "Login access given to the doctor successfully"}, status=status.HTTP_200_OK)

    def get(self, request):
        doctor_id = self.request.query_params.get('doctor_id')

        if not doctor_id:
            return Response({"Error": "doctor_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            lab_doctor = LabDoctors.objects.get(id=doctor_id)
        except LabDoctors.DoesNotExist:
            return Response({"Error": "Doctor not found"}, status=status.HTTP_404_NOT_FOUND)

        lab_staff = LabStaff.objects.filter(name=lab_doctor.name, mobile_number=lab_doctor.mobile_number).first()

        response_data = {
            "lab_staff": lab_staff.id if lab_staff else None
        }
        return Response(response_data, status=status.HTTP_200_OK)