from rest_framework import serializers

from interoperability.models import LabTpaSecretKeys


class LabTpaSecretKeysSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabTpaSecretKeys
        fields = "__all__"


class LabTpaSecretKeysIntegrationSerializer(serializers.ModelSerializer):
    client = serializers.SerializerMethodField()
    lab_tpa_type = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()

    def get_client(self, obj):
        return obj.client.name if obj.client else None

    def get_lab_tpa_type(self, obj):
        return obj.lab_tpa_type.name if obj.lab_tpa_type else None

    def get_is_active(self, obj):
        return "ACTIVE" if obj.is_active else "INACTIVE"

    class Meta:
        model = LabTpaSecretKeys
        # fields = "__all__"
        fields = ['client', 'lab_tpa_type', 'is_active','secret_key']
