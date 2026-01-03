from rest_framework import serializers
from healtho_pro_user.models.business_models import BusinessType, BusinessProfiles, \
    BusinessWorkingDays, BusinessTimings, BExecutive, BContacts, BContactFor, BusinessAddresses, \
    GlobalMessagingSettings, GlobalBusinessSettings
from pro_laboratory.models.client_based_settings_models import BusinessDataStatus, BusinessControls
from pro_laboratory.serializers.client_based_settings_serializers import BusinessDataStatusSerializer
from pro_universal_data.serializers import MessagingServiceTypesSerializer


class BusinessTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessType
        fields = '__all__'


class BusinessAddressesSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessAddresses
        fields = '__all__'


class BusinessProfilesSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessProfiles
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Add business data status representation
        addresses = BusinessAddresses.objects.filter(b_id=instance)
        representation['addresses'] = BusinessAddressesSerializer(addresses, many=True).data if addresses else []
        business_data_status = BusinessDataStatus.objects.filter(client__name=instance.organization_name).first()
        representation['business_data_status'] = BusinessDataStatusSerializer(
            business_data_status).data if business_data_status else {}

        business_controls = BusinessControls.objects.first()
        multiple_branches = business_controls.multiple_branches if business_controls else False

        representation['multiple_branches'] = multiple_branches


        return representation


class GetNearestSerializer(serializers.Serializer):
    latitude = serializers.CharField(max_length=30)
    longitude = serializers.CharField(max_length=30)
    searching_for = serializers.ChoiceField(choices=[('Doctors', 'Doctors'),
                                                     ('Hospitals', 'Hospitals'),
                                                     ('Labs', 'Labs')])


class BusinessWorkingDaysSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessWorkingDays
        fields = '__all__'


class BusinessTimingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessTimings
        fields = '__all__'


class BExecutiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = BExecutive
        fields = '__all__'


class BContactForSerializer(serializers.ModelSerializer):
    class Meta:
        model = BContactFor
        fields = '__all__'


class BContactsSerializer(serializers.ModelSerializer):
    contact_for = BContactForSerializer(write_only=True)

    class Meta:
        model = BContacts
        fields = '__all__'

    def create(self, validated_data):
        contact_for_data = validated_data.pop('contact_for')
        contact_for_instance = BContactFor.objects.create(**contact_for_data)
        bcontacts_instance = BContacts.objects.create(contact_for=contact_for_instance, **validated_data)
        return bcontacts_instance


class GlobalMessagingSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalMessagingSettings
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        last_updated_by = instance.last_updated_by
        type = instance.type

        if last_updated_by:
            representation['last_updated_by'] = {
                "id": last_updated_by.id,
                "last_updated_by": last_updated_by.full_name
            }

        if type:
            representation['type'] = MessagingServiceTypesSerializer(type).data
        return representation


class GlobalBusinessSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalBusinessSettings
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


