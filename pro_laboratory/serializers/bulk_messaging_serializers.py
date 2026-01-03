from tempfile import template

from rest_framework import serializers

from pro_laboratory.models.bulk_messaging_models import BulkMessagingLogs, BulkSendSMSData, \
    BulkSendAndSaveWhatsAppSMSData, BulkMessagingTemplates, BusinessMessagesCredits, BulkMessagingHistory


class BulkMessagingLogsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BulkMessagingLogs
        fields = '__all__'


class BulkMessagingTemplatesSerializer(serializers.ModelSerializer):
    class Meta:
        model = BulkMessagingTemplates
        fields = '__all__'


class BulkSendSMSDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = BulkSendSMSData
        fields = ['search_id', 'numbers', 'sms_template', 'messaging_send_type', 'from_date', 'to_date']


class BulkSendAndSaveWhatsAppSMSDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = BulkSendAndSaveWhatsAppSMSData
        fields = ['search_id', 'numbers', 'mwa_template', 'messaging_send_type']


class BulkMessagingSerializer(serializers.Serializer):
    recipient_type = serializers.IntegerField()
    recipient_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True
    )
    template_id = serializers.IntegerField()


class BusinessMessagesCreditsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessMessagesCredits
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        if instance.last_updated_by:
            representation['last_updated_by'] = {
                "id":instance.last_updated_by.id,
                "full_name":instance.last_updated_by.full_name
            }
        messaging_service_types = representation.get('messaging_service_types')
        if messaging_service_types is not None:
            messaging_service_types_name = instance.messaging_service_types.name
            representation['messaging_service_types'] = messaging_service_types_name
        return representation



class BulkMessagingHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BulkMessagingHistory
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        representation['template'] = BulkMessagingTemplatesSerializer(instance.template).data if template else None

        created_by = instance.created_by

        if created_by:
            representation['created_by']={"id":created_by.id,
                                          "name":created_by.name}

        return representation