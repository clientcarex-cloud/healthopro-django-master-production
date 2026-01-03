from datetime import time
from django.db import connection
from django.db.models import Q, Count
from django_tenants.utils import schema_context
from geopy import Nominatim
from geopy.distance import geodesic
from rest_framework import viewsets, generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import APIView

from healtho_pro_user.models.business_models import BusinessProfiles
from healtho_pro_user.models.pro_doctor_models import ProdoctorAppointmentSlot
from healtho_pro_user.models.universal_models import ProDoctor, Shift, Consultation, DeliveryMode
from healtho_pro_user.models.users_models import Client
from healtho_pro_user.serializers.pro_doctor_serializers import BusinessProfilesSerializer
from healtho_pro_user.serializers.universal_serializers import ShiftSerializer, ConsultationSerializer
import logging
from mobile_app.serializers import DoctorSerializer, HospitalSerializer, \
    MobileAppPatientSerializer, \
    StandardViewMobileAppPatientSerializer, PatientRegistrationSerializer, PatientDetailSerializer, PatientSerializer, \
    PatientMedicinesOrderingGetSerializer, DoctorAppointmentsListSerializer, DeliveryModeSerializer, OrderSerializer, \
    PharmaStockGetSerializer, GetNearestSerializer, PharmaItemsGetSerializer, \
    CategorySerializer
from pro_laboratory.models.global_models import LabGlobalTests, LabGlobalPackages, LabDepartments
from pro_laboratory.models.patient_models import Patient
from pro_laboratory.serializers.global_serializers import LabGlobalTestsSerializer, LabGlobalPackagesSerializer, \
    LabDepartmentsSerializer
from mobile_app.serializers import QuickServicesSerializer, \
    MobileAppLabMenusSerializer, \
    DoctorLanguageSpokenSerializer, DoctorSpecializationsSerializer, PharmaItemsSerializer

from healtho_pro_user.models.universal_models import UProDoctorSpecializations, ProDoctorLanguageSpoken
from mobile_app.models import QuickServices, MobileAppLabMenus, Category
from pro_pharmacy.models import PharmaItems, OrderItem, PharmaStock

logger = logging.getLogger(__name__)


class ShiftAPIView(generics.ListAPIView):
    queryset = Shift.objects.all()
    serializer_class = ShiftSerializer


class ConsultationAPIView(generics.ListAPIView):
    queryset = Consultation.objects.all()
    serializer_class = ConsultationSerializer


class HospitalListAPIView(generics.ListAPIView):
    serializer_class = HospitalSerializer

    def get_queryset(self):
        return BusinessProfiles.objects.filter(provider_type_id=2)


class LaboratoryListAPIView(generics.ListAPIView):
    serializer_class = HospitalSerializer

    def get_queryset(self):
        return BusinessProfiles.objects.filter(provider_type_id=1)


class DoctorAPIView(generics.ListAPIView):  ##Not using this api
    serializer_class = DoctorSerializer

    def get_queryset(self):
        queryset = ProDoctor.objects.all()
        doctor = self.request.query_params.get('doctor', None)
        date = self.request.query_params.get('date', None)
        specialization = self.request.query_params.get('specialization', None)
        if doctor:
            queryset = queryset.filter(pro_user_id__full_name__icontains=doctor)
        if specialization:
            queryset = queryset.filter(professional_details__specialization__id__icontains=specialization)
        if date:
            queryset = queryset.filter(appointment_slots__date=date)
        return queryset


class PopularDoctorsInCityView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = GetNearestSerializer(data=request.data)
        if serializer.is_valid():
            user_location = (
                float(serializer.validated_data['latitude']),
                float(serializer.validated_data['longitude'])
            )

            geolocator = Nominatim(user_agent="HealthO-Your Caring Partner")

            user_location_details = geolocator.reverse(user_location, exactly_one=True)
            user_city = user_location_details.raw['address'].get('city', '')
            specialization_id = request.query_params.get('specialization_id')

            popular_doctors = []
            doctors = ProDoctor.objects.all()
            if specialization_id:
                doctors = doctors.filter(professional_details__specialization__id=specialization_id)

            for doctor in doctors:
                if doctor.latitude and doctor.longitude:
                    doctor_location = (float(doctor.latitude), float(doctor.longitude))
                    doctor_location_details = geolocator.reverse(doctor_location, exactly_one=True)
                    doctor_city = doctor_location_details.raw['address'].get('city', '')
                    if user_city and doctor_city and user_city.lower() == doctor_city.lower():
                        popular_doctors.append(doctor)

            paginator = api_settings.DEFAULT_PAGINATION_CLASS()
            page = paginator.paginate_queryset(popular_doctors, request)
            if page is not None:
                doctor_serializer = DoctorSerializer(page, many=True)
                return paginator.get_paginated_response(doctor_serializer.data)

            doctor_serializer = DoctorSerializer(popular_doctors, many=True)
            return Response(doctor_serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LabtestAPIView(generics.ListAPIView):
    serializer_class = LabGlobalTestsSerializer

    def get_queryset(self):
        b_id = self.request.query_params.get('b_id', None)
        try:
            business = BusinessProfiles.objects.get(pk=b_id)
            business_name = business.organization_name
            client = Client.objects.get(name=business_name)
        except (BusinessProfiles.DoesNotExist, Client.DoesNotExist) as e:
            return LabGlobalTests.objects.none()

        connection.set_schema(client.schema_name)
        queryset = LabGlobalTests.objects.all()
        # queryset = queryset.annotate(test_count=Count('labpatienttests')).order_by('-test_count')[:5]

        query = self.request.query_params.get('q', None)
        body_part = self.request.query_params.get('body_part', None)
        department = self.request.query_params.get('department', None)
        if query is not None:
            search_query = (Q(name__icontains=query) | Q(short_code__icontains=query))
            queryset = queryset.filter(search_query)
        if body_part is not None:
            search_query = (Q(body_parts__id__icontains=body_part))
            queryset = queryset.filter(search_query)
        if department is not None:
            department_search = Q(department__id__icontains=department)
            queryset = queryset.filter(department_search)
        return queryset


class QuickServicesViewSet(viewsets.ModelViewSet):
    queryset = QuickServices.objects.all()
    serializer_class = QuickServicesSerializer


class MobileAppLabMenusViewSet(viewsets.ModelViewSet):
    queryset = MobileAppLabMenus.objects.all()
    serializer_class = MobileAppLabMenusSerializer


class DoctorSpecializationsAPIView(generics.ListAPIView):
    queryset = UProDoctorSpecializations.objects.all()
    serializer_class = DoctorSpecializationsSerializer


class DoctorLanguageSpokenAPIView(generics.ListAPIView):
    queryset = ProDoctorLanguageSpoken.objects.all()
    serializer_class = DoctorLanguageSpokenSerializer


class PharmaciesAPIView(generics.ListAPIView):
    serializer_class = HospitalSerializer

    def get_queryset(self):
        return BusinessProfiles.objects.filter(provider_type_id=3)

    # def get_queryset(self):
    #     user_city = self.request.query_params.get('city')
    #     if not user_city:
    #         return BusinessProfiles.objects.none()  # Return an empty queryset if no city is provided
    #
    #     all_pharmacies = BusinessProfiles.objects.filter(provider_type_id=3)
    #     geolocator = Nominatim(user_agent="healtho_user_location")
    #
    #     filtered_pharmacies = []
    #
    #     for pharmacy in all_pharmacies:
    #         if pharmacy.latitude and pharmacy.longitude:
    #             location = geolocator.reverse((pharmacy.latitude, pharmacy.longitude), exactly_one=True)
    #             if location:
    #                 address_components = location.raw.get('address', {})
    #                 city = address_components.get('city', '') or address_components.get('town', '')
    #                 if city.lower() == user_city.lower():
    #                     filtered_pharmacies.append(pharmacy.id)
    #
    #     return BusinessProfiles.objects.filter(id__in=filtered_pharmacies)
    #


class DoctorAppointmentsListView(generics.ListAPIView):
    serializer_class = DoctorAppointmentsListSerializer

    def get_queryset(self):
        queryset = ProdoctorAppointmentSlot.objects.all()
        shift = self.request.query_params.get('shift', None)
        doctor = self.request.query_params.get('doctor', None)
        date = self.request.query_params.get('date', None)
        consultation = self.request.query_params.get('consultation', None)

        if doctor is not None:
            queryset = queryset.filter(pro_doctor=doctor)
        if consultation:
            queryset = queryset.filter(consultation_type__consultation_type=consultation)
        if date is not None:
            queryset = queryset.filter(date=date)

        if shift is not None:
            if shift == 'morning':
                queryset = queryset.filter(session_start_time__range=(time(0, 0), time(11, 59)))
            elif shift == 'afternoon':
                queryset = queryset.filter(session_start_time__range=(time(12, 0), time(15, 59)))
            elif shift == 'evening':
                queryset = queryset.filter(session_start_time__range=(time(16, 0), time(23, 59)))

        return queryset


class MedicineCategoriesAPIView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_queryset(self):
        b_id = self.request.query_params.get('b_id', None)
        try:
            business = BusinessProfiles.objects.get(pk=b_id)
            business_name = business.organization_name
            client = Client.objects.get(name=business_name)
        except (BusinessProfiles.DoesNotExist, Client.DoesNotExist) as e:
            return Category.objects.none()

        connection.set_schema(client.schema_name)
        queryset = Category.objects.all()
        return queryset


class PharmaItemsAPIView(generics.ListAPIView):
    serializer_class = PharmaItemsSerializer

    def get_queryset(self):
        b_id = self.request.query_params.get('b_id', None)
        try:
            business = BusinessProfiles.objects.get(pk=b_id)
            business_name = business.organization_name
            client = Client.objects.get(name=business_name)
        except (BusinessProfiles.DoesNotExist, Client.DoesNotExist) as e:
            return PharmaItems.objects.none()

        connection.set_schema(client.schema_name)
        queryset = PharmaItems.objects.all()
        query = self.request.query_params.get('q', None)
        if query is not None:
            queryset = PharmaItems.objects.filter(category_id=query)
        return queryset


class FrequentlyOrderedMedicinesView(APIView):
    def get(self, request):
        b_id = self.request.query_params.get('b_id')
        if not b_id:
            return Response({'error': 'b_id is mandatory'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            business = BusinessProfiles.objects.get(pk=b_id)
            business_name = business.organization_name
            client = Client.objects.get(name=business_name)
        except (BusinessProfiles.DoesNotExist, Client.DoesNotExist):
            return Response({'error': 'Invalid b_id'}, status=status.HTTP_400_BAD_REQUEST)

        with schema_context(client.schema_name):
            medicine_counts = OrderItem.objects.values('medicine').annotate(count=Count('medicine')).order_by('-count')

            medicine_ids = [item['medicine'] for item in medicine_counts]
            medicines = PharmaStock.objects.filter(id__in=medicine_ids).select_related('item')

            serializer = PharmaStockGetSerializer(medicines, many=True)

            response_data = {
                'frequently_ordered_medicines': serializer.data
            }

            return Response(response_data)


class MobileAppPatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all()
    serializer_class = MobileAppPatientSerializer

    def create(self, request, *args, **kwargs):
        b_id = request.data.get('b_id')
        bProfile = BusinessProfiles.objects.get(pk=b_id)
        client = Client.objects.get(name=bProfile.organization_name)
        with schema_context(client.schema_name):
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                patient = serializer.save()

                patient_serializer = StandardViewMobileAppPatientSerializer(patient)

                return Response(patient_serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PatientRegistrationWithDoctorViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all()
    serializer_class = PatientRegistrationSerializer

    def create(self, request, *args, **kwargs):
        b_id = request.data.get('b_id')
        bProfile = BusinessProfiles.objects.get(pk=b_id)
        client = Client.objects.get(name=bProfile.organization_name)

        with schema_context(client.schema_name):
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                try:
                    patient = serializer.save()
                    response_data = PatientDetailSerializer(patient).data
                    return Response(response_data, status=status.HTTP_201_CREATED)
                except Exception as e:
                    return Response({"Error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PatientMedicineOrderViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer

    def create(self, request, *args, **kwargs):
        b_id = request.data.get('b_id')
        bProfile = BusinessProfiles.objects.get(pk=b_id)
        client = Client.objects.get(name=bProfile.organization_name)
        schema_name = client.schema_name

        with schema_context(schema_name):
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                try:
                    patient = serializer.save()
                    response_data = PatientMedicinesOrderingGetSerializer(patient).data
                    return Response(response_data, status=status.HTTP_201_CREATED)
                except Exception as e:
                    return Response({"Error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeliveryModeView(generics.ListAPIView):
    queryset = DeliveryMode.objects.all()
    serializer_class = DeliveryModeSerializer


def search_medicines_in_pharmacies(medicine_name):
    clients = Client.objects.filter(users__HealthcareRegistryType__id=3).distinct()
    result = []

    for client in clients:
        with schema_context(client.schema_name):
            cursor = connection.cursor()
            cursor.execute("SELECT to_regclass('pro_pharmacy_pharmaitems')")
            table_exists = cursor.fetchone()[0]

            if table_exists:
                medicines = PharmaItems.objects.filter(name__icontains=medicine_name)
                if medicines.exists():
                    result.append({
                        "client": client.schema_name,
                        "pharma_items": PharmaItemsGetSerializer(medicines, many=True).data
                    })
    return result


@api_view(['GET'])
def master_search(request):
    query = request.query_params.get('q', '')
    doctors = ProDoctor.objects.filter(pro_user_id__full_name__icontains=query)
    # medicines = PharmaItems.objects.filter(name__icontains=query)
    labs = BusinessProfiles.objects.filter(organization_name__icontains=query)

    doctor_serializer = DoctorSerializer(doctors, many=True)
    labs_serializer = BusinessProfilesSerializer(labs, many=True)
    medicines_results = search_medicines_in_pharmacies(query)

    response_data = {
        'doctors': doctor_serializer.data,
        'medicines': medicines_results,
        'organizations': labs_serializer.data

    }
    return Response(response_data)


class NearbyDoctorsView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = GetNearestSerializer(data=request.data)
        if serializer.is_valid():
            user_location = (
                float(serializer.validated_data['latitude']),
                float(serializer.validated_data['longitude'])
            )

            specialization_id = request.query_params.get('specialization_id')

            nearby_doctors = []
            doctors = ProDoctor.objects.all()
            if specialization_id:
                doctors = doctors.filter(professional_details__specialization__id=specialization_id)
            for doctor in doctors:
                if doctor.latitude and doctor.longitude:
                    doctor_location = (float(doctor.latitude), float(doctor.longitude))
                    distance = geodesic(user_location, doctor_location).km
                    if distance <= 2:
                        nearby_doctors.append(doctor)

            paginator = api_settings.DEFAULT_PAGINATION_CLASS()
            page = paginator.paginate_queryset(nearby_doctors, request)
            if page is not None:
                doctor_serializer = DoctorSerializer(page, many=True)
                return paginator.get_paginated_response(doctor_serializer.data)

            doctor_serializer = DoctorSerializer(nearby_doctors, many=True)
            return Response(doctor_serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NearbyHospitalsView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = GetNearestSerializer(data=request.data)
        if serializer.is_valid():
            user_location = (
                float(serializer.validated_data['latitude']), float(serializer.validated_data['longitude']))
            nearby_hospitals = []
            for hospital in BusinessProfiles.objects.filter(provider_type_id=2):
                if hospital.latitude and hospital.longitude:
                    hospital_location = (float(hospital.latitude), float(hospital.longitude))
                    distance = geodesic(user_location, hospital_location).km
                    if distance <= 10:
                        nearby_hospitals.append(hospital)

            paginator = api_settings.DEFAULT_PAGINATION_CLASS()
            page = paginator.paginate_queryset(nearby_hospitals, request)
            if page is not None:
                hospital_serializer = HospitalSerializer(page, many=True)
                return paginator.get_paginated_response(hospital_serializer.data)

            hospital_serializer = HospitalSerializer(nearby_hospitals, many=True)
            return Response(hospital_serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NearbyLaboratoriesView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = GetNearestSerializer(data=request.data)
        if serializer.is_valid():
            user_location = (
                float(serializer.validated_data['latitude']), float(serializer.validated_data['longitude']))
            nearby_laboratories = []
            for laboratory in BusinessProfiles.objects.filter(provider_type_id=1):
                if laboratory.latitude and laboratory.longitude:
                    laboratory_location = (float(laboratory.latitude), float(laboratory.longitude))
                    distance = geodesic(user_location, laboratory_location).km
                    if distance <= 2:
                        nearby_laboratories.append(laboratory)

            paginator = api_settings.DEFAULT_PAGINATION_CLASS()
            page = paginator.paginate_queryset(nearby_laboratories, request)
            if page is not None:
                hospital_serializer = HospitalSerializer(page, many=True)
                return paginator.get_paginated_response(hospital_serializer.data)

            hospital_serializer = HospitalSerializer(nearby_laboratories, many=True)
            return Response(hospital_serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NearbyPharmaciesView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = GetNearestSerializer(data=request.data)
        if serializer.is_valid():
            user_location = (
                float(serializer.validated_data['latitude']), float(serializer.validated_data['longitude']))
            nearby_pharmacies = []
            for pharmacy in BusinessProfiles.objects.filter(provider_type_id=3):
                if pharmacy.latitude and pharmacy.longitude:
                    pharmacy_location = (float(pharmacy.latitude), float(pharmacy.longitude))
                    distance = geodesic(user_location, pharmacy_location).km
                    if distance <= 10:
                        nearby_pharmacies.append(pharmacy)

            paginator = api_settings.DEFAULT_PAGINATION_CLASS()
            page = paginator.paginate_queryset(nearby_pharmacies, request)
            if page is not None:
                pharmacy_serializer = HospitalSerializer(page, many=True)
                return paginator.get_paginated_response(pharmacy_serializer.data)

            pharmacy_serializer = HospitalSerializer(nearby_pharmacies, many=True)
            return Response(pharmacy_serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LabGlobalPackagesAPIView(generics.ListAPIView):
    queryset = LabGlobalPackages.objects.all()
    serializer_class = LabGlobalPackagesSerializer


def get_medicines_by_category(category_id):
    clients = Client.objects.all()
    result = []

    for client in clients:
        with schema_context(client.schema_name):
            cursor = connection.cursor()
            cursor.execute("SELECT to_regclass('pro_pharmacy_pharmaitems')")
            table_exists = cursor.fetchone()[0]

            if table_exists:
                medicines = PharmaItems.objects.filter(category_id=category_id)
                if medicines.exists():
                    result.append({
                        "client": client.schema_name,
                        "medicines": PharmaItemsGetSerializer(medicines, many=True).data
                    })
    return result


class CategoryPharmaItemsViewSet(viewsets.ViewSet):
    def list(self, request):
        category_id = request.query_params.get('category_id')
        if not category_id:
            return Response({"detail": "Category ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            category_id = int(category_id)
        except ValueError:
            return Response({"detail": "Invalid Category ID"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            results = get_medicines_by_category(category_id)
            response_data = {
                'medicines': results
            }
            return Response(response_data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DepartmentsListAPIView(generics.ListAPIView):
    serializer_class = LabDepartmentsSerializer

    def get_queryset(self):
        b_id = self.request.query_params.get('b_id', None)
        try:
            business = BusinessProfiles.objects.get(pk=b_id)
            business_name = business.organization_name
            client = Client.objects.get(name=business_name)
        except (BusinessProfiles.DoesNotExist, Client.DoesNotExist) as e:
            return LabDepartments.objects.none()

        connection.set_schema(client.schema_name)
        queryset = LabDepartments.objects.all()
        return queryset


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class DoctorsByHospitalListAPIView(generics.ListAPIView):
    serializer_class = DoctorSerializer

    def get_queryset(self):
        hospital_id = self.request.query_params.get('hospital_id')
        specialization = self.request.query_params.get('specialization')
        return ProDoctor.objects.filter(
            Q(professional_details__specialization__id=specialization) & Q(consultation__hospital=hospital_id))
