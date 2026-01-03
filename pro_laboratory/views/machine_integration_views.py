from django.db import connection
from rest_framework import serializers, generics, permissions, status
from rest_framework.response import Response

from interoperability.models import LabTpaSecretKeys
from pro_laboratory.models.machine_integration_models import ProcessingMachine, DataFromProcessingMachine
from pro_laboratory.serializers.machine_integration_serializers import ProcessingMachineInputDataSerializer
from pro_laboratory.views.universal_views import logger


class ProcessingMachineSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessingMachine
        fields = '__all__'


class DataFromProcessingMachineSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataFromProcessingMachine
        fields = '__all__'



class ProcessingMachineDataSavingView(generics.CreateAPIView):
    serializer_class = ProcessingMachineInputDataSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        try:
            logger.error(f"Started the processing of machine integration API",exc_info=True)

            logger.error(f"Machine integration data posted by machine: {request.data}",exc_info=True)
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            validated_data = serializer.validated_data
            secret_key = validated_data.pop('secret_key', None)

            if secret_key is None:
                logger.error(f"MCIT - Error: Secret Key not given", exc_info=True)
                return Response({"Error": "Secret Key not given"})

            lab_tpa_secret_key = LabTpaSecretKeys.objects.get(secret_key=secret_key, is_active=True)

        except LabTpaSecretKeys.DoesNotExist:
            logger.error(f"MCIT - Error:Matching Secret Key not found", exc_info=True)
            return Response({"Error": "Matching Secret Key not found"})

        if lab_tpa_secret_key:
            try:
                input_data = validated_data.get('input_data', None)

                try:
                    client = lab_tpa_secret_key.client
                    connection.set_schema(client.schema_name)
                except Exception as error:
                    print(error)
                    pass

                machine_id = validated_data.get('machine')
                input_data = validated_data.get('input_data')
                compliance = validated_data.get('compliance')

                machine = ProcessingMachine.objects.get(pk=machine_id)

                if not machine.is_active:
                    logger.error(f"MCIT - Error: Machine is inactive", exc_info=True)
                    return Response({"Error": "Machine is inactive!"}, status=status.HTTP_400_BAD_REQUEST)


                if input_data is not None:
                    instance = DataFromProcessingMachine.objects.create(machine=machine, data=input_data)
                    print('integration obj created', instance)
                    logger.error(f"MCIT - Error: integration obj created", exc_info=True)

                    if compliance == 'HL7':
                        print('in HL7 flow')
                        logger.error(f"MCIT - Error: in HL7 flow", exc_info=True)
                        from machine_integration_files.hl7_message import process_hl7_message
                        sample_id, saving_status = process_hl7_message(message=input_data)
                        print('integration work completed')
                        logger.error(f"MCIT - Error: integration work completed", exc_info=True)
                        return Response({"sample_id": sample_id,
                                         "saving_status": saving_status,
                                         "hl7 message": input_data})
                    elif compliance == 'ASTM':
                        print('in ASTM flow')
                        logger.error(f"MCIT - Error: in ASTM flow", exc_info=True)
                        from machine_integration_files.astm_message import process_astm_message
                        sample_id, saving_status = process_astm_message(message=input_data)
                        print('integration work completed')
                        logger.error(f"MCIT - Error: integration work completed", exc_info=True)
                        return Response({"sample_id": sample_id,
                                         "saving_status": saving_status,
                                         "hl7 message": input_data})
                    else:
                        logger.error(f"MCIT - Error: Compliance Not Selected: HL7 or ASTM!", exc_info=True)
                        return Response({"Error": "Compliance Not Selected: HL7 or ASTM!"}, status=status.HTTP_400_BAD_REQUEST)

                    # return HttpResponse(input_data)
                else:

                    logger.error(f"MCIT - Error: No data is sent", exc_info=True)
                    return Response({"Error": "No data is sent"}, status=status.HTTP_400_BAD_REQUEST)

            except Exception as error:
                logger.error(f"MCIT - Error: {error}", exc_info=True)
                return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)



def process_parameter_value(parameter=None, parameter_value_from_machine =None):
    parameter_in_master_template = parameter.template
    if parameter_in_master_template.round_to_decimals is not None:
        try:
            numeric_value = float(parameter_value_from_machine)

            parameter_value_from_machine = round(numeric_value, parameter_in_master_template.round_to_decimals)
            if parameter_in_master_template.round_to_decimals == 0:
                parameter_value_from_machine = int(parameter_value_from_machine)

        except Exception as error:
                print(error)
                logger.error(f"MCIT - Error(While conversion of parameter value): {error}", exc_info=True)


    return parameter_value_from_machine