from logging import raiseExceptions

from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from pro_hospital.models.universal_models import CaseType, GlobalServices, RoomType, Floor, GlobalRoom, \
    DoctorConsultationDetails, GlobalPackages, GlobalRoomBeds
from pro_hospital.serializers.universal_serializers import CaseTypeSerializer, \
    GlobalServicesSerializer, RoomTypeSerializer, FloorSerializer, GlobalRoomSerializer, \
    DoctorConsultationDetailsSerializer, GlobalPackagesSerializer, DoctorConsultationDetailsForPatientsSerializer
from pro_laboratory.models.global_models import LabGlobalTests, LabGlobalPackages
from pro_laboratory.serializers.global_serializers import LabGlobalTestsSerializer, LabGlobalPackagesSerializer


class CaseTypeViewSet(viewsets.ModelViewSet):
    queryset = CaseType.objects.all()
    serializer_class = CaseTypeSerializer

    def get_queryset(self):
        queryset =  CaseType.objects.all()

        if queryset:
            pass
        else:
            for case in ['First Visit', 'Follow Up', 'Emergency']:
                CaseType.objects.get_or_create(name=case)

        return queryset


class DoctorConsultationDetailsViewSet(viewsets.ModelViewSet):
    queryset = DoctorConsultationDetails.objects.all()
    serializer_class = DoctorConsultationDetailsSerializer


class GlobalServicesViewSet(viewsets.ModelViewSet):
    queryset = GlobalServices.objects.all()
    serializer_class = GlobalServicesSerializer

    def get_queryset(self):
        queryset = GlobalServices.objects.all()
        query = self.request.query_params.get('q', None)
        departments_details = self.request.query_params.get('departments', [])

        if query is not None:
            search_query = Q(name__icontains=query) | Q(short_code__icontains=query) | Q(department__name__icontains=query)
            queryset = queryset.filter(search_query)

        if departments_details:
            departments = [department.strip() for department in departments_details.split(',') if
                           department.strip()]
            department_query = Q(department__id__in=departments)
            queryset = queryset.filter(department_query)
        return queryset

class RoomTypeViewSet(viewsets.ModelViewSet):
    queryset = RoomType.objects.all()
    serializer_class = RoomTypeSerializer

class FloorViewSet(viewsets.ModelViewSet):
    queryset = Floor.objects.all()
    serializer_class = FloorSerializer


class GlobalRoomViewSet(viewsets.ModelViewSet):
    serializer_class = GlobalRoomSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        global_room = serializer.save()
        total_beds = serializer.validated_data.get('total_beds')
        if total_beds:
            GlobalRoomBeds.objects.bulk_create(
                [
                    GlobalRoomBeds(global_room=global_room, bed_number=i)
                    for i in range(1, total_beds + 1)
                ]
            )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        global_room = serializer.save()
        total_beds = serializer.validated_data.get('total_beds')
        if total_beds is not None:
            GlobalRoomBeds.objects.filter(global_room=global_room).delete()

            GlobalRoomBeds.objects.bulk_create(
                [
                    GlobalRoomBeds(global_room=global_room, bed_number=i)
                    for i in range(1, total_beds + 1)
                ]
            )

        return Response(serializer.data)

    def get_queryset(self):
        queryset = GlobalRoom.objects.all()
        floor = self.request.query_params.get('floor')
        query = self.request.query_params.get('q')
        if query:
            queryset = queryset.filter(name__icontains=query)
        if floor:
            queryset = queryset.filter(floor__id=floor)
        queryset = queryset.order_by('name','room_number')
        return queryset


class GlobalPackagesViewSet(viewsets.ModelViewSet):
    queryset = GlobalPackages.objects.all()
    serializer_class = GlobalPackagesSerializer




@api_view(['GET'])
def master_search_for_entities(request):
    query = request.query_params.get('q', '')

    client_id = request.client

    if not client_id:
        return Response({"error": "client_id is required"}, status=400)


    lab_tests = LabGlobalTests.objects.filter(
        (Q(name__icontains=query) | Q(short_code__icontains=query)) &
        Q(is_active=True) &
        Q(department__is_active=True)
    )

    packages = GlobalPackages.objects.filter(
        Q(name__icontains=query) &
        Q(is_active=True)
    )
    doctor_consultation = DoctorConsultationDetails.objects.filter(Q(labdoctors__name__icontains=query) & Q(is_active=True))
    service = GlobalServices.objects.filter(Q(name__icontains=query) &
        Q(is_active=True)
    )
    rooms = GlobalRoom.objects.filter(Q(name__icontains=query) | Q(room_type__name__icontains=query) | Q(room_number__icontains=query) | Q(floor__name__icontains=query) &
        Q(is_active=True))

    lab_test_serializer = LabGlobalTestsSerializer(lab_tests, many=True, context={"request": request})
    packages_serializer = GlobalPackagesSerializer(packages, many=True, context={"request": request})
    doctor_consultation_serializer = DoctorConsultationDetailsForPatientsSerializer(doctor_consultation, many=True)
    services_serializer = GlobalServicesSerializer(service, many=True)
    rooms_serializer = GlobalRoomSerializer(rooms, many=True)

    response_data = {
        'lab_tests': lab_test_serializer.data,
        'packages': packages_serializer.data,
        'doctor_consultations': doctor_consultation_serializer.data,
        'services': services_serializer.data,
        'rooms': rooms_serializer.data
    }

    # # Cache the response data
    # cache.set(cache_key, response_data)

    return Response(response_data)
