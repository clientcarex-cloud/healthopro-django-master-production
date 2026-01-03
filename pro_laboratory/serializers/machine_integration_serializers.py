
from rest_framework import serializers

from pro_laboratory.models.machine_integration_models import ProcessingMachine, DataFromProcessingMachine


class ProcessingMachineSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessingMachine
        fields = '__all__'


class DataFromProcessingMachineSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataFromProcessingMachine
        fields = '__all__'


class ProcessingMachineInputDataSerializer(serializers.Serializer):
    machine = serializers.IntegerField()
    input_data = serializers.CharField()
    secret_key = serializers.CharField()
    compliance = serializers.CharField()

    class Meta:
        fields = '__all__'