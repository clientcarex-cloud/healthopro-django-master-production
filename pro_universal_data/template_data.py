import base64
import os
from datetime import datetime

from pytz import timezone
from healtho_pro_user.models.business_models import BContacts, BExecutive, BusinessProfiles, BusinessAddresses
from healtho_pro_user.models.users_models import Domain
from pro_laboratory.models.doctors_models import LabDoctors
from pro_laboratory.models.lab_appointment_of_patient_models import LabAppointmentForPatient
from pro_laboratory.models.patient_models import Patient, LabPatientInvoice, LabPatientTests



def encode_id(value):
    encoded_bytes = base64.urlsafe_b64encode(str(value).encode('utf-8'))
    return encoded_bytes.decode('utf-8')


def generate_tests_report_url(test_ids, client, mobile_number, lh):
    hashed_test_ids = ','.join(encode_id(test_id) for test_id in test_ids)
    hashed_client_id = encode_id(client)
    hashed_mobile_number = encode_id(mobile_number)
    domain_obj = Domain.objects.first()
    domain_url = domain_obj.url
    qr_data = f"{domain_url}/patient_report/?t={hashed_test_ids}&c={hashed_client_id}&m={hashed_mobile_number}&lh={lh}"

    return qr_data


def generate_test_report_url(test_id, client, mobile_number, lh):
    hashed_test_id = encode_id(test_id)
    hashed_client_id = encode_id(client)
    hashed_mobile_number = encode_id(mobile_number)
    domain_obj = Domain.objects.first()
    domain_url = domain_obj.url
    qr_data = f"{domain_url}/patient_report/?t={hashed_test_id}&c={hashed_client_id}&m={hashed_mobile_number}&lh={lh}"

    return qr_data


def generate_patient_receipt_url(client, patient, receipt):
    hashed_client_id = encode_id(client)
    hashed_patient_id = encode_id(patient)
    hashed_receipt = encode_id(receipt)
    domain_obj = Domain.objects.first()
    domain_url = domain_obj.url
    receipt_data = f"{domain_url}/download_patient_receipt/?c={hashed_client_id}&p={hashed_patient_id}&r={hashed_receipt}"

    return receipt_data


def template_data(search_id, messaging_send_type, client, test_id=None,test_ids=None, receipt=None, letterhead=None):
    from pro_laboratory.views.universal_views import get_age_details,get_age_details_in_short_form
    details = {}

    report_printed_on = datetime.now().strftime('%d-%m-%y %I:%M %p')
    details['report_printed_on'] = report_printed_on

    if messaging_send_type.name == 'Patients':
        try:
            patient = Patient.objects.get(pk=search_id)
            bProfile = BusinessProfiles.objects.filter(organization_name=client.name).first()
            contacts = BContacts.objects.filter(b_id=bProfile, is_primary=True).first()
            labpatientinvoice = LabPatientInvoice.objects.filter(patient=patient).first()

            indian_timezone = timezone('Asia/Kolkata')
            if patient:
                patient.added_on = patient.added_on.astimezone(indian_timezone)

            indian_timezone = timezone('Asia/Kolkata')
            if labpatientinvoice:
                labpatientinvoice.added_on = labpatientinvoice.added_on.astimezone(indian_timezone)

            # Assign fetched values to details dict
            details['patient'] = patient
            details['age']=get_age_details(patient)
            details['age_short_form']=get_age_details_in_short_form(patient)
            details['bProfile'] = bProfile
            details['contacts'] = contacts
            details['labpatientinvoice'] = labpatientinvoice
            details['patient_receipt_url'] = generate_patient_receipt_url(client.id, patient.id, receipt)
            if test_id:
                details['test_report_url'] = generate_test_report_url(test_id, client.id, patient.mobile_number, letterhead)
            if test_ids:
                details['tests_report_url'] = generate_tests_report_url(test_ids, client.id, patient.mobile_number,letterhead)

            print(details.get('test_report_url'), details.get('tests_report_url'))
        except Exception as error:
            print(f"Error occurred: {error}")
        return details

    elif messaging_send_type.name == 'Doctors':
        try:
            doctor = LabDoctors.objects.get(pk=search_id)
            bProfile = BusinessProfiles.objects.filter(organization_name=client.name).first()
            contacts = BContacts.objects.filter(b_id=bProfile, is_primary=True).first()
            executive = BExecutive.objects.filter(b_id=bProfile, is_primary=True).first()
            patients = Patient.objects.filter(referral_doctor=doctor)
            patient_count = patients.count()

            details['doctor'] = doctor
            details['bProfile'] = bProfile
            details['contacts'] = contacts
            details['executive'] = executive
            details['patient_count'] = patient_count

        except Exception as error:
            print(f"Error occurred: {error}")

        return details

    elif messaging_send_type.name == 'Admin':
        try:
            bProfile = BusinessProfiles.objects.filter(organization_name=client.name).first()
            contacts = BContacts.objects.filter(b_id=bProfile, is_primary=True).first()
            details['contacts'] = contacts
            details['bProfile'] = bProfile

        except Exception as error:
            print(f"Error occurred: {error}")

        return details
    elif messaging_send_type.name == 'Appointment':
        try:
            print(messaging_send_type.name, messaging_send_type.name=='Appointment')

            appointments = LabAppointmentForPatient.objects.get(pk=search_id)
            bProfile = BusinessProfiles.objects.filter(organization_name=client.name).first()
            b_address = BusinessAddresses.objects.filter(b_id=bProfile.id).first()

            details['appointments'] = appointments
            details['bProfile'] = bProfile
            details['b_address'] = b_address
        except Exception as error:
            print(f"Error occurred: {error}")

        return details
