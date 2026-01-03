from rest_framework import serializers
from healtho_pro_user.models.universal_models import UserType, Country, State, City, SupportInfoTutorials, \
    HealthcareRegistryType, UProDoctorSpecializations, ProDoctorLanguageSpoken, Shift, Consultation, \
    ProDoctor, ProDoctorProfessionalDetails


class UserTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserType
        fields = '__all__'


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = '__all__'


class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = '__all__'


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = '__all__'


class SupportInfoTutorialsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportInfoTutorials
        fields = '__all__'


class HealthcareRegistryTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthcareRegistryType
        fields = "__all__"


class UProDoctorSpecializationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UProDoctorSpecializations
        fields = '__all__'


class ProDoctorLanguageSpokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProDoctorLanguageSpoken
        fields = '__all__'


class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = "__all__"


class ConsultationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consultation
        fields = '__all__'


class ProDoctorSerializer(serializers.ModelSerializer):
    profile_image_url = serializers.URLField(write_only=True, required=False)

    class Meta:
        model = ProDoctor
        fields = '__all__'


class ProDoctorProfessionalDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProDoctorProfessionalDetails
        fields = '__all__'

