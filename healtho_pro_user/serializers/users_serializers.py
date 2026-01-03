import time

from django.contrib.auth.models import Permission, Group
from django.db import transaction, connection
from geopy import Nominatim
from rest_framework import serializers, status
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from healtho_pro_user.models.business_models import BusinessProfiles, BusinessAddresses, BusinessModules
from healtho_pro_user.models.universal_models import HealthcareRegistryType, Country, State, City, ProDoctor, \
    ProDoctorLanguageSpoken, ProDoctorProfessionalDetails
from healtho_pro_user.models.users_models import HealthOProUser, ULoginSliders, Client, Domain, UserTenant, \
    HealthOProMessagingUser
from pro_laboratory.models.global_models import LabStaff, LabStaffRole, LabMenuAccess
import re

User = get_user_model()


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'name']


class GroupSerializer(serializers.ModelSerializer):
    permissions = serializers.PrimaryKeyRelatedField(many=True, queryset=Permission.objects.all())

    class Meta:
        model = Group
        fields = ['id', 'name', 'permissions']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['permissions'] = PermissionSerializer(instance.permissions.all(), many=True).data
        return representation


import logging

logger = logging.getLogger(__name__)


def create_schema_name(name):
    # Remove invalid characters
    name = re.sub('[^0-9a-zA-Z_]', '', name)
    # Ensure it starts with a letter or underscore
    if not re.match('^[a-zA-Z_]', name):
        name = f"tenant_{name}"
    return name


class ProDoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProDoctor
        exclude = ['pro_user_id']


class ProDoctorProfessionalDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProDoctorProfessionalDetails
        exclude = ['pro_doctor']


class UserSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(write_only=True, required=False)
    doctor_details = ProDoctorSerializer(required=False)
    doctor_professional_details = ProDoctorProfessionalDetailsSerializer(required=False)

    class Meta:
        model = User
        fields = ['id', 'phone_number', 'user_type', 'country', 'city', 'state', 'organization_name',
                  'HealthcareRegistryType', 'full_name', 'latitude', 'longitude', 'doctor_details',
                  'doctor_professional_details']

    def create(self, validated_data):
        organization_name = validated_data.pop('organization_name', None)
        full_name = validated_data.get('full_name', None)
        user_type = validated_data.get('user_type', None)

        with transaction.atomic():
            try:
                str_time = time.time()
                if user_type and user_type.id == 3:
                    schema_name = create_schema_name(organization_name)
                    logger.info(f"Generated schema name: {schema_name}")

                    # Switch back to the public schema if necessary
                    connection.set_schema_to_public()

                    # Get or create a tenant, rely on auto_create_schema to handle schema creation
                    client, created = Client.objects.get_or_create(
                        name=organization_name,
                        defaults={'schema_name': schema_name}
                    )
                    print(client, 'client')
                    # validated_data['client'] = client
                    user = HealthOProUser.objects.create(**validated_data)
                    print(user, ' **user')
                    UserTenant.objects.create(
                        user=user,
                        client=client,
                        is_superadmin=True,
                        is_active=True
                    )

                    # Switch to the tenant's schema
                    connection.set_schema(client.schema_name)

                    healthcare_registry_type_instance = HealthcareRegistryType.objects.get(
                        id=user.HealthcareRegistryType_id)
                    country_instance = Country.objects.get(id=user.country_id)
                    state_instance = State.objects.get(id=user.state_id)
                    # city_instance = City.objects.get(id=user.city_id)

                    business_profile = BusinessProfiles.objects.create(
                        pro_user_id=user,
                        organization_name=organization_name if organization_name else user.full_name,
                        phone_number=user.phone_number,
                        provider_type=healthcare_registry_type_instance,
                        country=country_instance,
                        state=state_instance,
                        latitude=user.latitude,
                        longitude=user.longitude
                        # city=city_instance
                    )
                    print(business_profile, 'business profile')
                    if business_profile.latitude and business_profile.longitude:
                        user_location = (business_profile.latitude, business_profile.longitude)
                        # print('location', user_location)
                        geolocator = Nominatim(user_agent="HealthOPro")

                        address = geolocator.reverse(user_location, exactly_one=True)
                        b_address = address.raw.get('address', {})
                        # print('b_address', b_address)
                        address_parts = [
                            b_address.get('road', ''),
                            b_address.get('city', ''),
                            b_address.get('state', ''),
                            b_address.get('postcode', ''),
                            b_address.get('country', ''),
                        ]
                        full_address = ', '.join(part for part in address_parts if part)
                        BusinessAddresses.objects.create(
                            b_id=business_profile,
                            address=full_address
                        )

                    # Create lab_staff_role and lab_staff after the tenant's schema is created
                    lab_staff_role = LabStaffRole.objects.create(name="SuperAdmin")
                    marketing_role = LabStaffRole.objects.create(name="MarketingExecutive")
                    lab_staff = LabStaff.objects.create(
                        name=full_name,
                        mobile_number=user.phone_number,
                        is_superadmin=True,
                        role=lab_staff_role,
                        is_login_access=True
                    )
                    print(lab_staff, '**lab_staff')
                    business_modules = BusinessModules.objects.get(business=business_profile)
                    business_menus = business_modules.modules.all()
                    menu_access = LabMenuAccess.objects.create(lab_staff=lab_staff)
                    menu_access.lab_menu.set(business_menus)

                    menu_access.save()
                    print(menu_access, '****...menu access')
                    # Switch back to the public schema if necessary
                    connection.set_schema_to_public()

                if user_type and user_type.id == 1:
                    doctor_details_data = validated_data.pop('doctor_details', {})
                    professional_details_data = validated_data.pop('doctor_professional_details', {})
                    languages_spoken_data = professional_details_data.pop('languages_spoken', [])
                    awards_and_recognitions_data = professional_details_data.pop('awards_and_recognitions', [])
                    research_and_publications_data = professional_details_data.pop('research_and_publications', [])

                    user = HealthOProUser.objects.create(**validated_data)
                    # if doctor_details_data:
                    doctor = ProDoctor.objects.create(pro_user_id=user, latitude=user.latitude, longitude=user.longitude,
                                                      **doctor_details_data)
                    doctor_professional_details = ProDoctorProfessionalDetails.objects.create(pro_doctor=doctor,
                                                                                              **professional_details_data)
                    if languages_spoken_data:
                        doctor_professional_details.languages_spoken.set(languages_spoken_data)
                    if awards_and_recognitions_data:
                        doctor_professional_details.awards_and_recognitions.set(awards_and_recognitions_data)
                    if research_and_publications_data:
                        doctor_professional_details.research_and_publications.set(research_and_publications_data)
                if user_type and user_type.id == 2:
                    user = HealthOProUser.objects.create(**validated_data)
            except Exception as error:
                raise ValidationError({"Error":f"{error}"})

        return user


class UserListSerializer(serializers.ModelSerializer):
    pro_user = serializers.SerializerMethodField()

    class Meta:
        model = HealthOProMessagingUser
        fields = ('id', 'dp', 'pro_user', 'username', 'is_active')

    def validate(self, attrs):
        if not attrs['username']:
            raise serializers.ValidationError("please enter username")
        else:
            return attrs

    def get_pro_user(self, obj):
        # Define which fields to include in the reduced pro_user representation
        reduced_fields = ['id', 'user_type', 'HealthcareRegistryType', 'full_name']
        # Create an instance of the original serializer with the reduced fields
        user_serializer = UserSerializer(obj.pro_user, context=self.context)
        # Get the serialized data and include only the specified fields
        data = user_serializer.data
        reduced_data = {field: data[field] for field in reduced_fields}

        return reduced_data


class UserUpdateSerializer(serializers.ModelSerializer):
    user_permissions = serializers.PrimaryKeyRelatedField(many=True, queryset=Permission.objects.all())
    groups = serializers.PrimaryKeyRelatedField(many=True, queryset=Group.objects.all())

    class Meta:
        model = HealthOProUser
        fields = ['phone_number', 'full_name', 'latitude', 'longitude', 'user_permissions',
                  'groups', 'country', 'city', 'state', ]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['user_permissions'] = PermissionSerializer(instance.user_permissions.all(), many=True).data
        groups = instance.groups.all()
        representation['groups'] = []

        # Iterate over each group and retrieve permissions associated with it
        for group in groups:
            group_data = {
                'id': group.id,
                'name': group.name,
                'permissions': PermissionSerializer(group.permissions.all(), many=True).data
            }
            representation['groups'].append(group_data)

        return representation


class UserAllPermissionsSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)

    class Meta:
        model = HealthOProUser
        fields = ['full_name', 'permissions']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        user_permissions = instance.user_permissions.all()
        group_permissions = Permission.objects.filter(group__user=instance)
        all_permissions = (user_permissions | group_permissions).distinct()  # Combine user and group permissions
        representation['permissions'] = PermissionSerializer(all_permissions, many=True).data
        return representation


class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthOProUser
        fields = ['id', 'username', 'phone_number', 'HealthcareRegistryType', 'user_type', 'full_name', 'email',
                  'is_staff', 'is_active']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        user = HealthOProUser.objects.create_user(**validated_data)
        return user

    def update(self, instance, validated_data):
        instance.username = validated_data.get('username', instance.username)
        instance.phone_number = validated_data.get('phone_number', instance.phone_number)
        instance.user_type = validated_data.get('user_type', instance.user_type)
        instance.email = validated_data.get('email', instance.email)
        instance.is_staff = validated_data.get('is_staff', instance.is_staff)
        instance.is_active = validated_data.get('is_active', instance.is_active)
        if 'password' in validated_data:
            instance.set_password(validated_data['password'])
        instance.save()
        return instance


class ULoginSlidersSerializer(serializers.ModelSerializer):
    class Meta:
        model = ULoginSliders
        fields = '__all__'


class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthOProUser
        fields = ['id', 'full_name', 'phone_number', 'email']
