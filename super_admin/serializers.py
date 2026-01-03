from django_tenants.utils import schema_context
from rest_framework import serializers

from healtho_pro_user.models.business_models import BusinessProfiles, BusinessAddresses, GlobalBusinessSettings, \
    BusinessModules, DeletedBusinessProfiles
from healtho_pro_user.models.subscription_models import BusinessSubscriptionPlans, OverallBusinessSubscriptionStatus
from healtho_pro_user.models.users_models import HealthOProUser, Client
from healtho_pro_user.serializers.business_serializers import BusinessAddressesSerializer, \
    GlobalBusinessSettingsSerializer
from healtho_pro_user.serializers.subscription_serializers import BusinessSubscriptionTypeSerializer, \
    BusinessBillCalculationTypeSerializer, OverallBusinessSubscriptionStatusSerializer
from pro_laboratory.models.client_based_settings_models import BusinessControls
from pro_laboratory.models.universal_models import ActivityLogs
from pro_laboratory.serializers.client_based_settings_serializers import BusinessControlsSerializer
from pro_universal_data.serializers import ULabMenusSerializer
from super_admin.models import HealthOProSuperAdmin


class HealthOProSuperAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthOProSuperAdmin
        fields = ['user', 'is_active']

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        user = instance.user

        representation['user'] = {
            "id": instance.user.id,
            "full_name": instance.user.full_name,
            "phone_number": instance.user.phone_number,
        }

        return representation


class BusinessProfilesForAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessProfiles
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['addresses']=[]
        try:
            addresses = BusinessAddresses.objects.filter(b_id=instance)
            representation['addresses'] = BusinessAddressesSerializer(addresses, many=True).data if addresses else []
        except Exception as error:
            print(error)

        representation['owner'] = instance.organization_name
        try:
            owner = HealthOProUser.objects.filter(phone_number=instance.phone_number).first()

            representation['owner'] = owner.full_name if owner else instance.organization_name
        except Exception as error:
            print(error)

        representation['business_settings'] = []
        try:
            business_settings, created = GlobalBusinessSettings.objects.get_or_create(business=instance)
            representation['business_settings'] = GlobalBusinessSettingsSerializer(
                business_settings).data if business_settings else []
        except Exception as error:
            print(error)

        representation['subscription_status'] = None
        try:
            obj = OverallBusinessSubscriptionStatus.objects.filter(b_id=instance).first()

            representation['subscription_status'] = OverallBusinessSubscriptionStatusSerializer(
                obj).data if obj is not None else None

        except Exception as error:
            print(error)

        representation['last_activity_at'] = None
        representation['multiple_branches'] = []

        try:
            client = Client.objects.filter(name=instance.organization_name).first()
            if client is not None:
                with schema_context(client.schema_name):
                    activity = ActivityLogs.objects.last()
                    last_activity_at = activity.timestamp if activity else None

                    representation['last_activity_at'] = last_activity_at

                    multiple_branches = BusinessControls.objects.first()

                    if multiple_branches:
                        pass
                    else:
                        multiple_branches = BusinessControls.objects.create(multiple_branches=False)

                    multiple_branches = BusinessControlsSerializer(multiple_branches).data

                    representation['multiple_branches'] = multiple_branches


        except Exception as error:
            print(error)


        return representation

class BusinessProfilesDeletionForAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessProfiles
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['addresses']=[]
        try:
            addresses = BusinessAddresses.objects.filter(b_id=instance)
            representation['addresses'] = BusinessAddressesSerializer(addresses, many=True).data if addresses else []
        except Exception as error:
            print(error)

        representation['owner'] = instance.organization_name
        try:
            owner = HealthOProUser.objects.filter(phone_number=instance.phone_number).first()

            representation['owner'] = owner.full_name if owner else instance.organization_name
        except Exception as error:
            print(error)

        representation['business_settings'] = []
        try:
            business_settings, created = GlobalBusinessSettings.objects.get_or_create(business=instance)
            representation['business_settings'] = GlobalBusinessSettingsSerializer(
                business_settings).data if business_settings else []
        except Exception as error:
            print(error)

        representation['subscription_status'] = None
        try:
            obj = OverallBusinessSubscriptionStatus.objects.filter(b_id=instance).first()

            representation['subscription_status'] = OverallBusinessSubscriptionStatusSerializer(
                obj).data if obj is not None else None

        except Exception as error:
            print(error)

        representation['last_activity_at'] = None
        representation['multiple_branches'] = []

        try:
            client = Client.objects.filter(name=instance.organization_name).first()
            if client is not None:
                with schema_context(client.schema_name):
                    activity = ActivityLogs.objects.last()
                    last_activity_at = activity.timestamp if activity else None

                    representation['last_activity_at'] = last_activity_at

                    multiple_branches = BusinessControls.objects.first()

                    if multiple_branches:
                        pass
                    else:
                        multiple_branches = BusinessControls.objects.create(multiple_branches=False)

                    multiple_branches = BusinessControlsSerializer(multiple_branches).data

                    representation['multiple_branches'] = multiple_branches


        except Exception as error:
            print(error)


        return representation



class BusinessLoginAccessControlSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessProfiles
        fields = ['id', 'organization_name', 'phone_number', 'state', 'country', 'is_account_disabled', 'added_on']


class BusinessModulesSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessModules
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        last_updated_by = instance.last_updated_by
        if last_updated_by:
            representation['last_updated_by'] = {
                "id": last_updated_by.id,
                "last_updated_by": last_updated_by.full_name
            }

        return representation


class BusinessSubscriptionPlansSerializer(serializers.ModelSerializer):
    created_by=serializers.PrimaryKeyRelatedField(read_only=True)
    last_updated_by=serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = BusinessSubscriptionPlans
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        subscription_type = instance.subscription_type
        calculation_type = instance.calculation_type

        if subscription_type:
            representation['subscription_type'] = BusinessSubscriptionTypeSerializer(subscription_type).data

        if calculation_type:
            representation['calculation_type'] = BusinessBillCalculationTypeSerializer(calculation_type).data

        created_by = instance.created_by
        last_updated_by = instance.last_updated_by

        if created_by:
            representation['created_by'] = {
                "id": created_by.id,
                "last_updated_by": created_by.full_name
            }

        if last_updated_by:
            representation['last_updated_by'] = {
                "id": last_updated_by.id,
                "last_updated_by": last_updated_by.full_name
            }

        if instance.modules:
            representation['modules']=ULabMenusSerializer(instance.modules.all(), many=True).data

        return representation


class DeletedBusinessProfilesSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeletedBusinessProfiles
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        deleted_by = instance.deleted_by

        representation['deleted_by'] = {
            "id": deleted_by.id,
            "full_name": deleted_by.user.full_name
        }

        return representation
