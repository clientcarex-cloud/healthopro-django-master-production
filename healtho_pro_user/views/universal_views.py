from datetime import datetime

from rest_framework import viewsets, permissions, status
from rest_framework import generics
from rest_framework.response import Response

from healtho_pro_user.models.universal_models import UserType, Country, State, City, SupportInfoTutorials, \
    HealthcareRegistryType, UProDoctorSpecializations, ProDoctorLanguageSpoken, Shift, Consultation, \
    ProDoctor, ProDoctorProfessionalDetails
from healtho_pro_user.serializers.universal_serializers import UserTypeSerializer, CountrySerializer, StateSerializer, \
    CitySerializer, SupportInfoTutorialsSerializer, HealthcareRegistryTypeSerializer, \
    UProDoctorSpecializationsSerializer, ProDoctorLanguageSpokenSerializer, ShiftSerializer, ConsultationSerializer, \
    ProDoctorSerializer, ProDoctorProfessionalDetailsSerializer

from healtho_pro_user import scheduled_tasks  #To run scheduled tasks


class UserTypeViewSet(viewsets.ModelViewSet):
    queryset = UserType.objects.all()
    serializer_class = UserTypeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class SupportInfoTutorialsListAPIView(generics.ListAPIView):
    queryset = SupportInfoTutorials.objects.all()
    serializer_class = SupportInfoTutorialsSerializer


class CountryViewSet(viewsets.ModelViewSet):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class StateViewSet(viewsets.ModelViewSet):
    queryset = State.objects.all()
    serializer_class = StateSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        query = self.request.query_params.get('country')
        if query is not None:
            return State.objects.filter(country=query)
        else:

            return State.objects.all()


class CityViewSet(viewsets.ModelViewSet):
    queryset = City.objects.all()
    serializer_class = CitySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        query = self.request.query_params.get('state')
        if query is not None:
            return City.objects.filter(state=query)
        else:

            return City.objects.all()


class HealthcareRegistryTypeAPIView(generics.ListAPIView):
    queryset = HealthcareRegistryType.objects.all()
    serializer_class = HealthcareRegistryTypeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = HealthcareRegistryType.objects.filter(is_active=True)
        return queryset


class UniversalProDoctorSpecializationsViewSet(viewsets.ModelViewSet):
    queryset = UProDoctorSpecializations.objects.all()
    serializer_class = UProDoctorSpecializationsSerializer


class ProDoctorLanguageSpokenViewSet(viewsets.ModelViewSet):
    queryset = ProDoctorLanguageSpoken.objects.all()
    serializer_class = ProDoctorLanguageSpokenSerializer


class ShiftViewSet(viewsets.ModelViewSet):
    queryset = Shift.objects.all()
    serializer_class = ShiftSerializer


class ConsultationViewSet(viewsets.ModelViewSet):
    queryset = Consultation.objects.all()
    serializer_class = ConsultationSerializer


class ProDoctorViewSet(viewsets.ModelViewSet):
    queryset = ProDoctor.objects.all()
    serializer_class = ProDoctorSerializer


class ProDoctorProfessionalDetailsViewSet(viewsets.ModelViewSet):
    queryset = ProDoctorProfessionalDetails.objects.all()
    serializer_class = ProDoctorProfessionalDetailsSerializer



