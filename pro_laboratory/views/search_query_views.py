from glob import magic_check_bytes
from hashlib import md5

from django.core.cache import cache
from django.db.models import Q
from django.views.decorators.cache import cache_page
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from logging_middleware import logger
from pro_hospital.models.universal_models import DoctorConsultationDetails, GlobalServices, GlobalRoom
from pro_hospital.serializers.universal_serializers import DoctorConsultationDetailsForPatientsSerializer, \
    GlobalServicesSerializer, GlobalRoomSerializer
from pro_laboratory.models.doctors_models import LabDoctors
from pro_laboratory.models.global_models import LabGlobalTests, LabGlobalPackages
from pro_laboratory.models.patient_models import Patient
from pro_laboratory.serializers.global_serializers import LabGlobalTestsSerializer, LabGlobalPackagesSerializer
from pro_laboratory.serializers.doctors_serializers import LabDoctorsSerializer, SearchLabDoctorsSerializer
from pro_laboratory.serializers.patient_serializers import PatientSerializer
from rest_framework import status


@api_view(['GET'])
def search_doctors(request):
    query = request.query_params.get('q', '')
    doctors = LabDoctors.objects.filter(name__icontains=query)
    serializer = SearchLabDoctorsSerializer(doctors, many=True)  # Use the serializer with many=True
    return Response(serializer.data)


@api_view(['GET'])
def search_labTests(request):
    query = request.query_params.get('q', '')
    labTests = LabGlobalTests.objects.filter(name__icontains=query)
    serializer = LabGlobalTestsSerializer(labTests, many=True)  # Use the serializer with many=True
    return Response(serializer.data)


@api_view(['GET'])
def master_search(request):
    query = request.query_params.get('q', '')
    doctors = LabDoctors.objects.filter(name__icontains=query)
    patients = Patient.objects.filter(
        Q(name__icontains=query) | Q(mobile_number__icontains=query) | Q(mr_no__icontains=query) | Q(
            visit_id__icontains=query))
    lab_tests = LabGlobalTests.objects.filter(name__icontains=query)

    doctor_serializer = LabDoctorsSerializer(doctors, many=True)
    patient_serializer = PatientSerializer(patients, many=True)
    lab_test_serializer = LabGlobalTestsSerializer(lab_tests, many=True)

    response_data = {
        'doctors': doctor_serializer.data,
        'patients': patient_serializer.data,
        'lab_tests': lab_test_serializer.data

    }

    return Response(response_data)


@api_view(['GET'])
def master_search_for_tests(request):
    query = request.query_params.get('q', '')
    referral_lab = request.query_params.get('show_ref_lab', True)
    client_id = request.client

    if not client_id:
        return Response({"error": "client_id is required"}, status=400)

    # Generate a unique cache key per client and query
    cache_key = f'master_search_for_tests_{client_id}_{query}_ref_lab_{referral_lab}'

    try:
        # Try to fetch from cache
        cached_response = cache.get(cache_key)
        if cached_response:
            return Response(cached_response)

        # Fetch from the database if no cache is found
        lab_tests = LabGlobalTests.objects.filter(
            (Q(name__icontains=query) | Q(short_code__icontains=query)) &
            Q(is_active=True) &
            Q(department__is_active=True)
        )
        lab_packages = LabGlobalPackages.objects.filter(
            Q(name__icontains=query) &
            Q(is_active=True)
        )

        if not referral_lab:
            lab_tests = lab_tests.filter(sourcing_lab__isnull=True)

        # Serialize the data
        lab_test_serializer = LabGlobalTestsSerializer(lab_tests, many=True, context={"request": request})
        lab_packages_serializer = LabGlobalPackagesSerializer(lab_packages, many=True, context={"request": request})
        response_data = {
            'lab_tests': lab_test_serializer.data,
            'lab_packages': lab_packages_serializer.data
        }

        # Cache the response data
        cache.set(cache_key, response_data)

        return Response(response_data)

    except Exception as e:
        lab_tests = LabGlobalTests.objects.filter(
            (Q(name__icontains=query) | Q(short_code__icontains=query)) &
            Q(is_active=True) &
            Q(department__is_active=True)
        )
        lab_packages = LabGlobalPackages.objects.filter(
            Q(name__icontains=query) &
            Q(is_active=True)
        )


        if not referral_lab:
            lab_tests = lab_tests.filter(sourcing_lab__isnull=True)

        # Serialize the data
        lab_test_serializer = LabGlobalTestsSerializer(lab_tests, many=True)
        lab_packages_serializer = LabGlobalPackagesSerializer(lab_packages, many=True)
        response_data = {
            'lab_tests': lab_test_serializer.data,
            'lab_packages': lab_packages_serializer.data
        }

        return Response(response_data)


