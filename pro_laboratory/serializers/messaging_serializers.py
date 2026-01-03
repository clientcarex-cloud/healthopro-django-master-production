from rest_framework import serializers

from pro_laboratory.models.messaging_models import MessagingLogs, SendSMSData, SendAndSaveWhatsAppSMSData, \
    WhatsappConfigurations


class MessagingLogsSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessagingLogs
        fields = '__all__'


class SendSMSDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = SendSMSData
        fields = ['search_id', 'numbers', 'sms_template', 'messaging_send_type', 'from_date', 'to_date']


class SendAndSaveWhatsAppSMSDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = SendAndSaveWhatsAppSMSData
        fields = ['search_id', 'numbers', 'mwa_template', 'messaging_send_type']


class WhatsappConfigurationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsappConfigurations
        fields = '__all__'