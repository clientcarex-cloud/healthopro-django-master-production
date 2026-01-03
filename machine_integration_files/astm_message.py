from pro_laboratory.models.labtechnicians_models import LabPatientFixedReportTemplate, LabTechnicians
from pro_laboratory.models.phlebotomists_models import LabPhlebotomist
from pro_laboratory.views.labtechnicians_views import LabPatientTestReportGenerationViewset
from pro_laboratory.views.machine_integration_views import process_parameter_value
from pro_laboratory.views.universal_views import logger


def astm_to_dictionary(astm_data):
    """
    Parse ASTM message into a structured dictionary with field names as per the ASTM standard.
    """
    print('parsing started')
    logger.error(f"MCIT - Error: parsing started", exc_info=True)
    logger.info(f"MCIT - Error: parsing started", exc_info=True)
    parsed_data = {
        "header": {},
        "patient": {},
        "order": {},
        "results": [],
        "terminator": {}
    }

    # Split the message into lines and remove empty lines
    lines = [line.strip() for line in astm_data.split('\r') if line.strip()]

    for line in lines:
        # Skip lines that are too short or don't start with a digit
        if len(line) <= 3:
            continue

        line = line[1:] if line[0].isdigit() else line

        # Extract the record type and fields
        record_type = line[0]
        fields = line.split('|')

        if record_type == 'H':  # Header Record
            parsed_data["header"] = {
                "record_type_id": fields[0] if len(fields) > 0 else "",
                "delimiters": fields[1] if len(fields) > 1 else "",
                "sender_name_or_id": fields[2] if len(fields) > 2 else "",
                "receiver_id": fields[3] if len(fields) > 3 else "",
                "processing_id": fields[4] if len(fields) > 4 else "",
                "version_number": fields[5] if len(fields) > 5 else "",
                "reserved_field_1": fields[6] if len(fields) > 6 else "",
                "reserved_field_2": fields[7] if len(fields) > 7 else "",
                "reserved_field_3": fields[8] if len(fields) > 8 else "",
                "reserved_field_4": fields[9] if len(fields) > 9 else "",
                "reserved_field_5": fields[10] if len(fields) > 10 else "",
                "reserved_field_6": fields[11] if len(fields) > 11 else "",
                "reserved_field_7": fields[12] if len(fields) > 12 else "",
                "date_time_of_message": fields[13] if len(fields) > 13 else ""
            }

        elif record_type == 'P':  # Patient Record
            parsed_data["patient"] = {
                "record_type_id": fields[0] if len(fields) > 0 else "",
                "sequence_number": fields[1] if len(fields) > 1 else ""
            }

        elif record_type == 'O':  # Order Record
            parsed_data["order"] = {
                "record_type_id": fields[0] if len(fields) > 0 else "",
                "sequence_number": fields[1] if len(fields) > 1 else "",
                "specimen_id": fields[2] if len(fields) > 2 else "",
                "instrument_specimen_id": fields[3] if len(fields) > 3 else "",
                "universal_test_id": fields[4] if len(fields) > 4 else "",
                "priority": fields[5] if len(fields) > 5 else "",
                "requested_ordered_date_time": fields[6] if len(fields) > 6 else "",
                "specimen_collection_date_time": fields[7] if len(fields) > 7 else "",
                "collection_end_time": fields[8] if len(fields) > 8 else "",
                "collection_volume": fields[9] if len(fields) > 9 else "",
                "collector_id": fields[10] if len(fields) > 10 else "",
                "action_code": fields[11] if len(fields) > 11 else "",
                "danger_code": fields[12] if len(fields) > 12 else "",
                "relevant_clinical_info": fields[13] if len(fields) > 13 else "",
                "specimen_received_date_time": fields[14] if len(fields) > 14 else "",
                "specimen_descriptor": fields[15] if len(fields) > 15 else "",
                "ordering_physician": fields[16] if len(fields) > 16 else "",
                "physician_telephone_number": fields[17] if len(fields) > 17 else "",
                "user_field_1": fields[18] if len(fields) > 18 else "",
                "user_field_2": fields[19] if len(fields) > 19 else "",
                "laboratory_field_1": fields[20] if len(fields) > 20 else "",
                "laboratory_field_2": fields[21] if len(fields) > 21 else "",
                "date_time_results_reported": fields[22] if len(fields) > 22 else "",
                "instrument_charge_to_computer": fields[23] if len(fields) > 23 else "",
                "instrument_section_id": fields[24] if len(fields) > 24 else "",
                "report_type": fields[25] if len(fields) > 25 else "",
                "reserved_field_1": fields[26] if len(fields) > 26 else "",
                "reserved_field_2": fields[27] if len(fields) > 27 else "",
                "location_or_ward_of_specimen": fields[28] if len(fields) > 28 else "",
                "nosocomial_infection_flag": fields[29] if len(fields) > 29 else "",
                "specimen_service": fields[30] if len(fields) > 30 else "",
                "specimen_institution": fields[31] if len(fields) > 31 else "",
                "status": fields[32] if len(fields) > 32 else ""
            }

        elif record_type == 'R':  # Result Record
            result = {
                "record_type_id": fields[0] if len(fields) > 0 else "",
                "sequence_number": fields[1] if len(fields) > 1 else "",
                "universal_test_id": fields[2] if len(fields) > 2 else "",
                "data_or_measurement_value": fields[3] if len(fields) > 3 else "",
                "units": fields[4] if len(fields) > 4 else "",
                "reference_ranges": fields[5] if len(fields) > 5 else "",
                "result_abnormal_flags": fields[6] if len(fields) > 6 else "",
                "nature_of_abnormal_test": fields[7] if len(fields) > 7 else "",
                "result_status": fields[8] if len(fields) > 8 else "",
                "date_of_change_in_instrument_test_status": fields[9] if len(fields) > 9 else "",
                "operator_identification": fields[10] if len(fields) > 10 else "",
                "date_time_test_started": fields[11] if len(fields) > 11 else "",
                "date_time_test_completed": fields[12] if len(fields) > 12 else ""
            }
            parsed_data["results"].append(result)

        elif record_type == 'L':  # Terminator Record
            parsed_data["terminator"] = {
                "record_type_id": fields[0] if len(fields) > 0 else "",
                "sequence_number": fields[1] if len(fields) > 1 else "",
                "termination_code": fields[2] if len(fields) > 2 else ""
            }


    logger.error(f"MCIT - Error: parsing data {parsed_data}", exc_info=True)
    return parsed_data


def extract_observation_text_for_astm(observation_identifier):
    # Split the string at '^'
    components = observation_identifier.split('^')

    # Initialize an empty list to hold non-empty components
    values = []

    # Loop through the components and append non-empty ones to the list
    for component in components:
        if component:  # Check if the component is not empty
            values.append(component)

    # Join the values with a space and return
    return " ".join(values)


def check_sample_exists_and_process_astm(astm_decoded_message):
    print('checking for sample started')
    logger.error(f"MCIT - Error: checking for sample started", exc_info=True)
    sample_id = None
    saving_status = None
    if astm_decoded_message:
        print('inside astm decoded message')
        logger.error(f"MCIT - Error: inside astm decoded message", exc_info=True)
        OBR = astm_decoded_message.get('order')
        if OBR:
            sample_id = OBR.get('specimen_id')
            entered_values = astm_decoded_message.get('results')
            print('sample_id',sample_id)

            logger.error(f"MCIT - Error: 'sample_id',{sample_id}", exc_info=True)

            if sample_id and entered_values:
                phlebotomists = LabPhlebotomist.objects.filter(assession_number=sample_id, is_received=True)

                if phlebotomists:
                    print('sample_existss', phlebotomists)

                    logger.error(f"MCIT - Error: 'sample_existss', {phlebotomists}", exc_info=True)
                    lab_patient_tests = phlebotomists.values_list('LabPatientTestID', flat=True)

                    for lab_patient_test_id in lab_patient_tests:
                        generate_test_params = LabPatientTestReportGenerationViewset()
                        generate_test_params.create(lab_patient_test_id=lab_patient_test_id)
                        technician = LabTechnicians.objects.filter(LabPatientTestID__id=lab_patient_test_id).first()
                        technician.has_machine_integration=True
                        technician.save()

                    params = LabPatientFixedReportTemplate.objects.filter(LabPatientTestID__id__in=lab_patient_tests)
                    processed_params = []

                    for obj in entered_values:
                        param_name_from_machine = extract_observation_text_for_astm(obj.get('universal_test_id'))
                        param_value_from_machine = obj.get('data_or_measurement_value')
                        print('param identifier:', param_name_from_machine, 'value:', param_value_from_machine,'\n')
                        logger.error(f"MCIT - Error: ('param identifier:', {param_name_from_machine}, 'value:', {param_value_from_machine})'\n'", exc_info=True)


                        if param_name_from_machine:
                            test_parameters = params.filter(template__mcode=param_name_from_machine)
                            print('test parameter with mcode exists or not:',test_parameters)
                            logger.error(f"MCIT - Error: 'test parameter with mcode exists or not:',{test_parameters}", exc_info=True)

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

                    logger.error(f"MCIT - Error:  matching sample does not exist", exc_info=True)
                    saving_status = f'Not processed matching sample does not exist'
                    return sample_id,saving_status

            else:
                print('Error: sample id and values not available')

                logger.error(f"MCIT - Error: sample id and values not available", exc_info=True)
                saving_status = f'Not processed sample id and values not available'
                return sample_id,saving_status
        else:
            print('Error: Segment - Order not fount to get specimen id!')

            logger.error(f"MCIT - Error: Segment - Order not fount to get specimen id!", exc_info=True)
            saving_status = f'Not processed sample id and values not available'
            return sample_id, saving_status
    else:
        print('Error at ASTM message starting itself!')

        logger.error(f"MCIT - Error:Error at ASTM message starting itself!", exc_info=True)
        saving_status = f'Not processed sample id and values not available'
        return sample_id, saving_status




def process_astm_message(message=None):
    modified_msg = astm_to_dictionary(message)
    sample_id, saving_status = check_sample_exists_and_process_astm(modified_msg)
    print('machine integration process done')

    logger.error(f"MCIT - Error: machine integration process done", exc_info=True)
    return sample_id, saving_status