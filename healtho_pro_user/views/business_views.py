from django.db.models import Q, Count
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, generics
import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView
from geopy.distance import geodesic
from rest_framework.views import APIView

from healtho_pro_user.models.business_models import BusinessType, BusinessProfiles, BContacts, \
    BContactFor, BExecutive, BusinessTimings, BusinessAddresses
from healtho_pro_user.models.users_models import Client, UserTenant
from healtho_pro_user.serializers.business_serializers import BusinessTypeSerializer, BusinessProfilesSerializer, \
    GetNearestSerializer, BContactsSerializer, BContactForSerializer, BExecutiveSerializer, \
    BusinessTimingsSerializer, BusinessAddressesSerializer
from healtho_pro_user.views.users_views import blacklist_user_tokens

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BusinessTypeViewSet(viewsets.ModelViewSet):
    queryset = BusinessType.objects.all()
    serializer_class = BusinessTypeSerializer


class BusinessAddressesViewSet(viewsets.ModelViewSet):
    queryset = BusinessAddresses.objects.all()
    serializer_class = BusinessAddressesSerializer


class BusinessProfilesViewSet(viewsets.ModelViewSet):
    queryset = BusinessProfiles.objects.all()
    serializer_class = BusinessProfilesSerializer

    def get_queryset(self):
        client_id = self.request.query_params.get('client_id', None)
        queryset = BusinessProfiles.objects.all().order_by('id')
        if client_id is not None:
            client = Client.objects.get(pk=client_id)

            queryset = BusinessProfiles.objects.filter(organization_name=client.name)

        return queryset


class BusinesstimingsViewset(viewsets.ModelViewSet):
    queryset = BusinessTimings.objects.all()
    serializer_class = BusinessTimingsSerializer


class BExecutiveViewset(viewsets.ModelViewSet):
    queryset = BExecutive.objects.all()
    serializer_class = BExecutiveSerializer


class BContactForViewset(viewsets.ModelViewSet):
    queryset = BContactFor.objects.all()
    serializer_class = BContactForSerializer


class BContactsViewset(viewsets.ModelViewSet):
    queryset = BContacts.objects.all()
    serializer_class = BContactsSerializer


class GetNearestView(CreateAPIView):
    serializer_class = GetNearestSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer_data = serializer.data
        latitude = serializer_data['latitude']
        longitude = serializer_data['longitude']
        searching_for = serializer_data['searching_for']
        print(latitude, longitude, searching_for)

        if searching_for == 'Doctors':
            search_items = BusinessProfiles.objects.filter(provider_type=BusinessType.objects.get(type_name='Doctors'))
        elif searching_for == 'Hospitals':
            search_items = BusinessProfiles.objects.filter(
                provider_type=BusinessType.objects.get(type_name='Hospitals'))
        elif searching_for == 'Labs':
            search_items = BusinessProfiles.objects.filter(provider_type=BusinessType.objects.get(type_name='Labs'))
        else:
            print("The value of searching_for should be within 'Doctors','Hospitals','Labs'")

        user_location = (latitude, longitude)

        min_distance = 10000
        nearest = None
        place = None

        for search_item in search_items:
            search_item_location = (search_item.latitude, search_item.longitude)
            distance = geodesic(user_location, search_item_location).kilometers
            print(search_item_location, search_item.organization_name, distance, search_item.address)
            if distance < min_distance:
                min_distance = distance
                nearest = search_item.organization_name
                place = search_item.address

        return Response(
            {'Status': f'The nearest {searching_for} is {nearest} at {min_distance:.1f} km. The address is {place}'},
            status=status.HTTP_200_OK)


def get_business_from_client_id(client_id):
    client = Client.objects.get(pk=client_id)
    business = BusinessProfiles.objects.get(organization_name=client.name)
    return business


def get_business_from_client(client):
    business = BusinessProfiles.objects.get(organization_name=client.name)
    return business


def get_client_from_business_id(business_id):
    business = BusinessProfiles.objects.get(pk=business_id)
    client = Client.objects.get(name=business.organization_name)
    return client


def get_client_from_business(business):
    client = Client.objects.get(name=business.organization_name)
    return client
