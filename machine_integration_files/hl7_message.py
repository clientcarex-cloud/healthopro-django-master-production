from pro_laboratory.models.labtechnicians_models import LabPatientFixedReportTemplate, LabTechnicians
from pro_laboratory.models.phlebotomists_models import LabPhlebotomist
from pro_laboratory.views.labtechnicians_views import LabPatientTestReportGenerationViewset
from pro_laboratory.views.machine_integration_views import process_parameter_value

from pro_laboratory.views.universal_views import logger


def hl7_to_dictionary(hl7_message):
    """
    Parse HL7 message into a structured dictionary with snake_case field names.
    """

    logger.error(f"MCIT - Error: Parsing started", exc_info=True)
    parsed_data = {}
    segments = hl7_message.strip().split('\r')

    for segment in segments:
        fields = segment.split('|')
        segment_name = fields[0].strip()

        if segment_name == 'MSH':
            # Correctly extract the field separator
            segment_data = {
                "field_separator": segment[3],  # First character after 'MSH'
                "encoding_characters": fields[1],
                "sending_application": fields[2],
                "sending_facility": fields[3],
                "receiving_application": fields[4],
                "receiving_facility": fields[5],
                "date_time_of_message": fields[6],
                "security": fields[7],
                "message_type": fields[8],
                "message_control_id": fields[9],
                "processing_id": fields[10],
                "version_id": fields[11],
                "sequence_number": fields[12] if len(fields) > 12 else "",
                "continuation_pointer": fields[13] if len(fields) > 13 else "",
                "accept_acknowledgment_type": fields[14] if len(fields) > 14 else "",
                "application_acknowledgment_type": fields[15] if len(fields) > 15 else "",
                "country_code": fields[16] if len(fields) > 16 else "",
                "character_set": fields[17] if len(fields) > 17 else "",
                "principal_language_of_message": fields[18] if len(fields) > 18 else ""
            }

        elif segment_name == 'PID':
            segment_data = {
                "set_id": fields[1] if len(fields) > 1 else "",
                "patient_id": fields[2] if len(fields) > 2 else "",
                "patient_identifier_list": fields[3] if len(fields) > 3 else "",
                "alternate_patient_id": fields[4] if len(fields) > 4 else "",
                "patient_name": fields[5] if len(fields) > 5 else "",
                "mothers_maiden_name": fields[6] if len(fields) > 6 else "",
                "date_time_of_birth": fields[7] if len(fields) > 7 else "",
                "administrative_sex": fields[8] if len(fields) > 8 else "",
                "patient_alias": fields[9] if len(fields) > 9 else "",
                "race": fields[10] if len(fields) > 10 else "",
                "patient_address": fields[11] if len(fields) > 11 else "",
                "county_code": fields[12] if len(fields) > 12 else "",
                "phone_number_home": fields[13] if len(fields) > 13 else "",
                "phone_number_business": fields[14] if len(fields) > 14 else "",
                "primary_language": fields[15] if len(fields) > 15 else "",
                "marital_status": fields[16] if len(fields) > 16 else "",
                "religion": fields[17] if len(fields) > 17 else "",
                "patient_account_number": fields[18] if len(fields) > 18 else "",
                "ssn_number": fields[19] if len(fields) > 19 else "",
                "drivers_license_number": fields[20] if len(fields) > 20 else "",
                "mothers_identifier": fields[21] if len(fields) > 21 else "",
                "ethnic_group": fields[22] if len(fields) > 22 else "",
                "birth_place": fields[23] if len(fields) > 23 else "",
                "multiple_birth_indicator": fields[24] if len(fields) > 24 else "",
                "birth_order": fields[25] if len(fields) > 25 else "",
                "citizenship": fields[26] if len(fields) > 26 else "",
                "veterans_military_status": fields[27] if len(fields) > 27 else "",
                "nationality": fields[28] if len(fields) > 28 else "",
                "patient_death_date_time": fields[29] if len(fields) > 29 else "",
                "patient_death_indicator": fields[30] if len(fields) > 30 else ""
            }

        elif segment_name == 'OBR':
            segment_data = {
                "set_id": fields[1] if len(fields) > 1 else "",
                "placer_order_number": fields[2] if len(fields) > 2 else "",
                "filler_order_number": fields[3] if len(fields) > 3 else "",
                "universal_service_identifier": fields[4] if len(fields) > 4 else "",
                "priority": fields[5] if len(fields) > 5 else "",
                "requested_date_time": fields[6] if len(fields) > 6 else "",
                "observation_date_time": fields[7] if len(fields) > 7 else "",
                "observation_end_date_time": fields[8] if len(fields) > 8 else "",
                "collection_volume": fields[9] if len(fields) > 9 else "",
                "collector_identifier": fields[10] if len(fields) > 10 else "",
                "specimen_action_code": fields[11] if len(fields) > 11 else "",
                "danger_code": fields[12] if len(fields) > 12 else "",
                "relevant_clinical_info": fields[13] if len(fields) > 13 else "",
                "specimen_received_date_time": fields[14] if len(fields) > 14 else "",
                "specimen_source": fields[15] if len(fields) > 15 else "",
                "ordering_provider": fields[16] if len(fields) > 16 else "",
                "order_callback_phone_number": fields[17] if len(fields) > 17 else "",
                "placer_field_1": fields[18] if len(fields) > 18 else "",
                "placer_field_2": fields[19] if len(fields) > 19 else "",
                "filler_field_1": fields[20] if len(fields) > 20 else "",
                "filler_field_2": fields[21] if len(fields) > 21 else "",
                "results_rpt_status_change_date_time": fields[22] if len(fields) > 22 else "",
                "charge_to_practice": fields[23] if len(fields) > 23 else "",
                "diagnostic_serv_sect_id": fields[24] if len(fields) > 24 else "",
                "result_status": fields[25] if len(fields) > 25 else "",
                "parent_result": fields[26] if len(fields) > 26 else "",
                "quantity_timing": fields[27] if len(fields) > 27 else "",
                "result_copies_to": fields[28] if len(fields) > 28 else "",
                "parent": fields[29] if len(fields) > 29 else "",
                "transportation_mode": fields[30] if len(fields) > 30 else "",
                "reason_for_study": fields[31] if len(fields) > 31 else "",
                "principal_result_interpreter": fields[32] if len(fields) > 32 else "",
                "assistant_result_interpreter": fields[33] if len(fields) > 33 else "",
                "technician": fields[34] if len(fields) > 34 else "",
                "transcriptionist": fields[35] if len(fields) > 35 else "",
                "scheduled_date_time": fields[36] if len(fields) > 36 else "",
                "number_of_sample_containers": fields[37] if len(fields) > 37 else "",
                "transport_logistics": fields[38] if len(fields) > 38 else "",
                "collectors_comment": fields[39] if len(fields) > 39 else "",
                "transport_arrangement_responsibility": fields[40] if len(fields) > 40 else "",
                "transport_arranged": fields[41] if len(fields) > 41 else "",
                "escort_required": fields[42] if len(fields) > 42 else "",
                "planned_patient_transport_comment": fields[43] if len(fields) > 43 else ""
            }

        elif segment_name == 'OBX':
            segment_data = {
                "set_id": fields[1] if len(fields) > 1 else "",
                "value_type": fields[2] if len(fields) > 2 else "",
                "observation_identifier": fields[3] if len(fields) > 3 else "",
                "observation_sub_id": fields[4] if len(fields) > 4 else "",
                "observation_value": fields[5] if len(fields) > 5 else "",
                "units": fields[6] if len(fields) > 6 else "",
                "references_range": fields[7] if len(fields) > 7 else "",
                "abnormal_flags": fields[8] if len(fields) > 8 else "",
                "probability": fields[9] if len(fields) > 9 else "",
                "nature_of_abnormal_test": fields[10] if len(fields) > 10 else "",
                "observation_result_status": fields[11] if len(fields) > 11 else "",
                "effective_date_reference_range": fields[12] if len(fields) > 12 else "",
                "user_defined_access_checks": fields[13] if len(fields) > 13 else "",
                "date_time_of_observation": fields[14] if len(fields) > 14 else "",
                "producers_id": fields[15] if len(fields) > 15 else "",
                "responsible_observer": fields[16] if len(fields) > 16 else "",
                "observation_method": fields[17] if len(fields) > 17 else "",
                "equipment_instance_identifier": fields[18] if len(fields) > 18 else "",
                "date_time_of_analysis": fields[19] if len(fields) > 19 else ""
            }

        else:
            # Handle other segments generically
            segment_data = {f"field_{i}": field for i, field in enumerate(fields[1:], 1)}

        # Handle multiple occurrences of the same segment
        if segment_name in parsed_data:
            if isinstance(parsed_data[segment_name], list):
                parsed_data[segment_name].append(segment_data)
            else:
                parsed_data[segment_name] = [parsed_data[segment_name], segment_data]
        else:
            parsed_data[segment_name] = segment_data

    logger.error(f"MCIT - Error: Decode message at the end: \n {parsed_data}", exc_info=True)
    return parsed_data


def extract_observation_text_for_hl7(observation_identifier):
    # Split the string at '^'
    components = observation_identifier.split('^')

    # Return the second component if it exists, otherwise return the first component
    return components[1] if len(components) > 1 else components[0]


def check_sample_exists_and_process_hl7(hl7_decoded_message):
    print('checking for sample started')
    logger.error(f"MCIT - Error: checking for sample started", exc_info=True)
    sample_id = None
    saving_status = None
    if hl7_decoded_message:
        OBR = hl7_decoded_message.get('OBR')

        if OBR:
            sample_id = OBR.get('filler_order_number')
            entered_values = hl7_decoded_message.get('OBX')
            if entered_values:
                if isinstance(entered_values, dict):
                    # Wrap the dict in a list to preserve its structure
                    entered_values = [entered_values]
                elif not isinstance(entered_values, list):
                    # Wrap non-list, non-dict values in a list
                    entered_values = [entered_values]
            print('sample_id',sample_id)

            if sample_id and entered_values:
                phlebotomists = LabPhlebotomist.objects.filter(assession_number=sample_id, is_received=True)

                if phlebotomists:
                    print('sample_existss', phlebotomists)

                    logger.error(f"MCIT - Error: sample_existss", exc_info=True)
                    lab_patient_tests = phlebotomists.values_list('LabPatientTestID', flat=True)

                    for lab_patient_test_id in lab_patient_tests:
                        generate_test_params = LabPatientTestReportGenerationViewset()
                        generate_test_params.create(lab_patient_test_id=lab_patient_test_id)
                        technician = LabTechnicians.objects.filter(LabPatientTestID__id=lab_patient_test_id).first()
                        technician.has_machine_integration = True
                        technician.save()

                    params = LabPatientFixedReportTemplate.objects.filter(LabPatientTestID__id__in=lab_patient_tests)
                    processed_params = []

                    for obj in entered_values:
                        print(obj)
                        param_name_from_machine = extract_observation_text_for_hl7(obj.get('observation_identifier'))
                        param_value_from_machine = obj.get('observation_value')
                        print('param identifier:', param_name_from_machine, 'value:', param_value_from_machine, type(param_value_from_machine),'\n')

                        logger.error(f"MCIT - Error:'param identifier:', {param_name_from_machine}, 'value:', {param_value_from_machine},{type(param_value_from_machine)},'\n'", exc_info=True)

                        if param_name_from_machine:
                            test_parameters = params.filter(template__mcode=param_name_from_machine)
                            print('test parameter with mcode exists or not:',test_parameters)
                            logger.error(f"MCIT - Error: test parameter with mcode exists or not:',{test_parameters}", exc_info=True)

                            if test_parameters:
                                for test_parameter in test_parameters:
                                    param_value_from_machine = process_parameter_value(parameter=test_parameter,
                                                                                       parameter_value_from_machine=param_value_from_machine)
                                    processed_params.append(f"{test_parameter.parameter}:{param_value_from_machine}")
                                    test_parameter.value = param_value_from_machine
                                    test_parameter.save()
                    saving_status = f'Processed for {processed_params}'
                    print(saving_status)
                    logger.error(f"MCIT - Error: {saving_status}", exc_info=True)
                    return sample_id,saving_status
                else:
                    print('Error: matching sample does not exist')
                    logger.error(f"MCIT - Error:matching sample does not existd", exc_info=True)
                    saving_status = f'Not processed matching sample does not exist'
                    return sample_id,saving_status

            else:
                print('Error: sample id and values not available')
                logger.error(f"MCIT - Error: sample id and values not available", exc_info=True)
                saving_status = f'Not processed sample id and values not available'
                return sample_id,saving_status
        else:
            print(f'could not find OBR!:the message decode is this: {hl7_decoded_message}')
            logger.error(f"MCIT - Error: could not find OBR!:the message decoded is this:  \n {hl7_decoded_message}",
                         exc_info=True)
            return sample_id, saving_status
    else:
        print('error at hl7 starting itself!')
        logger.error(f"MCIT - Error: error at hl7 starting itself with the message \n {hl7_decoded_message}", exc_info=True)
        return sample_id,saving_status

def process_hl7_message(message=None):
    modified_msg = hl7_to_dictionary(message)
    sample_id, saving_status = check_sample_exists_and_process_hl7(modified_msg)
    print('machine integration process done')
    logger.error(f"MCIT - Error:machine integration process done", exc_info=True)
    return sample_id, saving_status







