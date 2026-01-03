from rest_framework import serializers

from healtho_pro_user.models.business_models import BusinessProfiles
from healtho_pro_user.models.pro_doctor_models import ProDoctorConsultation, ProdoctorAppointmentSlot
from healtho_pro_user.serializers.universal_serializers import ConsultationSerializer


class BusinessProfilesSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessProfiles
        fields = ['organization_name', 'address', 'phone_number', 'latitude', 'longitude', 'b_logo']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['b_id'] = instance.id
        return representation


class ProDoctorConsultationSerializer(serializers.ModelSerializer):
    hospital = BusinessProfilesSerializer()

    class Meta:
        model = ProDoctorConsultation
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        consultation_type_id = representation.get('consultation_type')
        if consultation_type_id is not None:
            consultation_type_name = instance.consultation_type.name
            representation['consultation_type'] = consultation_type_name

        return representation


class ProdoctorAppointmentSlotSerializer(serializers.ModelSerializer):
    start_time = serializers.TimeField(write_only=True, required=False)
    end_time = serializers.TimeField(write_only=True, required=False)

    class Meta:
        model = ProdoctorAppointmentSlot
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        consultation_type_id = representation.get('consultation_type')
        if consultation_type_id is not None:
            consultation_type_name = instance.consultation_type.consultation_type.name
            representation['consultation_type'] = consultation_type_name
        return representation
