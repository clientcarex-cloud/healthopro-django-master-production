from datetime import datetime

import requests
from rest_framework import viewsets, status
from rest_framework.response import Response

from healtho_pro_user.models.business_models import BusinessProfiles
from pro_laboratory.models.client_based_settings_models import BusinessMessageSettings
from pro_laboratory.models.doctors_models import LabDoctors
from pro_laboratory.models.messaging_models import MessagingLogs, SendSMSData, WhatsAppMessagingLogs, \
    SendAndSaveWhatsAppSMSData, WhatsappConfigurations
from pro_laboratory.models.patient_models import Patient, LabPatientInvoice, LabPatientTests
from pro_laboratory.serializers.messaging_serializers import MessagingLogsSerializer, SendSMSDataSerializer, \
    SendAndSaveWhatsAppSMSDataSerializer, WhatsappConfigurationsSerializer
from pro_universal_data.models import MessagingVendors, Tag
import os
import re

from pro_universal_data.template_data import template_data

FAST2SMS_KEY = os.environ.get('FAST2SMS_KEY')
META_WHATSAPP_KEY = os.environ.get('META_WHATSAPP_KEY')
META_WHATSAPP_PHONE_ID = os.environ.get('META_WHATSAPP_PHONE_ID')


# Message to save the logs of SendSMSData messages
class MessagingLogsViewSet(viewsets.ModelViewSet):
    queryset = MessagingLogs.objects.all()
    serializer_class = MessagingLogsSerializer

    def create(self, sms_id=None, response=None, *args, **kwargs):
        response_json = response.json()
        try:
            response_code = response_json['status_code']
        except:
            response_code = response.status_code

        response_message = response_json['message']

        sms = SendSMSData.objects.get(pk=sms_id)
        messaging_vendor = MessagingVendors.objects.get(name='Fast2SMS')
        status = f"{response_code}, {response_message}"
        message = sms.message
        businessid = sms.sms_template.sender_id
        messaging_send_type = sms.messaging_send_type
        numbers = sms.numbers
        sent_on = sms.sent_on
        messaging_logs = MessagingLogs(sms=sms, messaging_vendor=messaging_vendor, response_code=response_code,
                                       status=status, message=message,
                                       businessid=businessid, messaging_send_type=messaging_send_type,
                                       numbers=numbers, sent_on=sent_on)
        messaging_logs.save()


# Viewset to send SMS and save the data into db(From API endpoint and from direct call by function)
class SendAndSaveSMSDataViewset(viewsets.ModelViewSet):
    queryset = (SendSMSData.objects.all())
    serializer_class = SendSMSDataSerializer
    secret_key = FAST2SMS_KEY
    url = "https://www.fast2sms.com/dev/bulkV2"

    def create(self, request=None, search_id=None, numbers=None, sms_template=None, messaging_send_type=None,
               client=None,
               from_date=None, to_date=None, *args, **kwargs):
        if request:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer_data = serializer.validated_data
            search_id = serializer_data['search_id']
            numbers = serializer_data['numbers']
            sms_template = serializer_data['sms_template']
            messaging_send_type = serializer_data['messaging_send_type']
            from_date = serializer_data.get('from_date')
            to_date = serializer_data.get('to_date')
            client = serializer_data.get('client')

            serializer_data['sent_on'] = datetime.now()
            # print(f"This is from request: {search_id}, {numbers}, {sms_template}, {messaging_send_type}, {client}")

        else:
            print(f"This is from kwargs: {search_id}, {numbers}, {sms_template}, {messaging_send_type}, {client}")

        if search_id and numbers and sms_template and messaging_send_type:
            # Collecting the data of given id and msg_type
            details = {}

            try:
                details = template_data(search_id, messaging_send_type, client)
                # print(details['labpatientinvoice'].total_paid)
            except Exception as error:
                print(f"While fetching details,-{error}")

            if messaging_send_type.name == 'Doctors' or messaging_send_type.name == 'Admin':
                if from_date and to_date:  # Dates are necessary to process Doctors/Admin related templates
                    if messaging_send_type.name == 'Doctors':
                        def calculate_total_ref_amount(search_id, from_date, to_date):
                            doctor = LabDoctors.objects.get(pk=search_id)
                            bProfile = BusinessProfiles.objects.filter(organization_name=client.name).first()

                            patients_referred = Patient.objects.filter(referral_doctor=doctor,
                                                                       added_on__range=[from_date, to_date]).count()
                            referral_amount_per_patient = bProfile.referral_amount_per_patient
                            total_ref_amount = referral_amount_per_patient * patients_referred
                            # print(bProfile, patients_referred, referral_amount_per_patient, total_ref_amount)

                            return total_ref_amount

                        details['total_ref_amount'] = calculate_total_ref_amount(search_id, from_date, to_date)

                    elif messaging_send_type.name == 'Admin':
                        bProfile = BusinessProfiles.objects.filter(organization_name=client.name).first()
                        total_patients = Patient.objects.all()
                        total_patients_count = total_patients.count()

                        total_price = 0
                        total_paid = 0

                        for patient in total_patients:
                            labpatientinvoices = LabPatientInvoice.objects.filter(patient=patient,
                                                                                  added_on__range=[from_date, to_date])
                            for labpatientinvoice in labpatientinvoices:
                                total_price += labpatientinvoice.total_price
                                total_paid += labpatientinvoice.total_paid
                                # print(labpatientinvoice, total_price, total_paid)

                        labpatienttests_count = LabPatientTests.objects.filter(added_on__range=[from_date,
                                                                                                to_date]).count()

                        analytics = {
                            'DateRange': f"{from_date.strftime('%d-%m-%y')} to {to_date.strftime('%d-%m-%y')}",
                            'TotalPatients': total_patients_count,
                            'TotalAmount': total_price,
                            'TotalCollection': total_paid,
                            'DueStatus': (total_price - total_paid),
                            'TotalSamplesCollection': labpatienttests_count
                        }
                        # print(analytics)
                        details['analytics'] = analytics
                else:
                    # print(f"'Error': 'One or more Mandatory parameters missing - from_date, to_date'")
                    return Response({"Error": "One or more Mandatory parameters missing - from_date, to_date"},
                                    status=status.HTTP_400_BAD_REQUEST)

            else:
                pass

            # Regex search to get all the values with { }
            search_pattern = r"\{(.*?)\}"
            constant_pattern = r'{Constant:\s*([^}]*)\s*}'
            template_content = sms_template.templateContent
            template_values = {}

            def replace_tag(match):
                tag_name = match.group(0)  # Gets the matched content including curly braces
                try:
                    if re.match(constant_pattern, tag_name):  # Handling {Constants}
                        tag_value = re.match(constant_pattern, tag_name).group(1)
                        template_values[tag_name] = tag_value
                        return tag_value

                    elif re.match(search_pattern, tag_name):  # Handling {variables}
                        try:
                            tag = Tag.objects.get(tag_name=tag_name)
                            if tag.tag_formula:
                                try:
                                    tag_value = str(eval(tag.tag_formula, {'details': details}))
                                    template_values[tag_name] = tag_value
                                    return tag_value
                                except Exception as error:
                                    print(f"{tag_name} - This tag has error in the formula!Please Check: {error}")
                                    tag_value = f"*{re.match(search_pattern, tag_name).group(1)}*"
                                    template_values[tag_name] = tag_value
                                    return tag_value
                            else:
                                print(f"{tag_name} - This tag does not have a formula! Please check ")
                                tag_value = f"*{re.match(search_pattern, tag_name).group(1)}*"
                                template_values[tag_name] = tag_value
                                return tag_value

                        except Tag.DoesNotExist:
                            print(f"{tag_name} - This tag does not exist! ")
                            tag_value = f"*{re.match(search_pattern, tag_name).group(1)}*"
                            template_values[tag_name] = tag_value
                            return tag_value
                except Exception as error:
                    print(f"Error occured at {tag_name} - {error}")

            # Function to replace the template_content and get the template_values dictionary
            replaced_content = None
            try:
                replaced_content = re.sub(search_pattern, replace_tag, template_content)
            except Exception as error:
                print(error)

            # Converting variable_values and keys to be passable into API
            variable_keys = list(template_values.keys())
            variable_values = list(template_values.values())

            variable_keys = '|'.join(variable_keys)
            variable_values = '|'.join(variable_values)

            # Code for FAST2SMS API
            querystring = {
                "authorization": self.secret_key,
                "route": sms_template.route,
                "sender_id": sms_template.sender_id,
                "message": sms_template.templateId,
                "variables_values": variable_values,
                "mapping": variable_keys,
                "numbers": numbers,
            }
            # print(querystring)

            headers = {
                'cache-control': "no-cache"
            }

            response = requests.request("GET", self.url, headers=headers, params=querystring)
            response_data = response.json()
            error_msg = response_data['message']

            if request:
                serializer_data['message'] = replaced_content
                serializer = serializer.save()
                sms_id = serializer.id
            else:
                sent_on = datetime.now()
                sms = SendSMSData(search_id=search_id, numbers=numbers, sms_template=sms_template,
                                  messaging_send_type=messaging_send_type, message=replaced_content,
                                  sent_on=sent_on)
                sms.save()
                sms_id = sms.id

            # Accessing the MessagingLogsViewSet to save the sms status to db
            messaging_log = MessagingLogsViewSet()
            messaging_log.create(sms_id=sms_id, response=response)

            if response.status_code == 200:
                return Response({"message": "SMS sent successfully", "response_code": 200})
            else:
                print(f"'Error': 'Failed to send SMS', 'Message': {error_msg} ")
                return Response({"Error": "Failed to send SMS", "Message": error_msg, "response_code": 400},
                                status=response.status_code)

        else:
            print(f"'Error': 'One or more Mandatory parameters missing - search_id,numbers,sms_template,"
                  f"'messaging_send_type'")
            return Response({"Error": "One or more Mandatory parameters missing - search_id,numbers,sms_template,"
                                      "messaging_send_type"}, status=status.HTTP_400_BAD_REQUEST)


class WhatsAppMessagingLogsViewSet(viewsets.ModelViewSet):
    queryset = WhatsAppMessagingLogs.objects.all()
    serializer_class = MessagingLogsSerializer

    def create(self, sms_id=None, response_code=None, response_message=None, messaging_vendor=None, *args, **kwargs):
        sms = SendAndSaveWhatsAppSMSData.objects.get(pk=sms_id)
        status = f"{response_code}, {response_message}"
        message = sms.message
        businessid = sms.mwa_template.sender_id
        messaging_send_type = sms.messaging_send_type
        numbers = sms.numbers
        sent_on = sms.sent_on

        try:
            messaging_logs = WhatsAppMessagingLogs(sms=sms, messaging_vendor=messaging_vendor, status=status,
                                                   message=message, response_code=response_code,
                                                   businessid=businessid, messaging_send_type=messaging_send_type,
                                                   numbers=numbers, sent_on=sent_on)
            messaging_logs.save()
            # print('message logged')
        except Exception as error:
            print(error)


class SendAndSaveWhatsAppSMSViewset(viewsets.ModelViewSet):
    queryset = SendAndSaveWhatsAppSMSData.objects.all()
    serializer_class = SendAndSaveWhatsAppSMSDataSerializer

    def create(self, request=None, search_id=None, numbers=None, mwa_template=None, messaging_send_type=None,
               client=None, test_id=None, test_ids=None, receipt=None, send_reports_type=None,letterhead=None, *args,
               **kwargs):
        if request:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer_data = serializer.validated_data
            search_id = serializer_data['search_id']
            numbers = serializer_data['numbers']
            mwa_template = serializer_data['mwa_template']
            messaging_send_type = serializer_data['messaging_send_type']
            client = serializer_data['client']
            test_id = serializer_data['test_id']
            receipt = serializer_data['receipt']
            send_reports_type = serializer_data['send_reports_type']

            serializer_data['sent_on'] = datetime.now()
            print(f"This is from request: {search_id}, {numbers}, {mwa_template}, {messaging_send_type}, {client}")

        else:
            print(f"This is from kwargs: {search_id}, {numbers}, {mwa_template}, {messaging_send_type}, {client}")

        if search_id and numbers and mwa_template and messaging_send_type and client:
            # Collecting the data of given id and msg_type
            details = {}

            try:
                details = template_data(search_id, messaging_send_type, client, test_id, test_ids, receipt, letterhead)
            except Exception as error:
                print(f"While fetching details,-{error}")

            # Regex search to get all the values with { }
            search_pattern = r"\{(.*?)\}"
            constant_pattern = r'{Constant:\s*([^}]*)\s*}'
            template_content = mwa_template.templateContent
            template_values = {}
            # print(details)

            def replace_tag(match):
                tag_name = match.group(0)  # Gets the matched content including curly braces
                try:
                    if re.match(constant_pattern, tag_name):  # Handling {Constants}
                        tag_value = re.match(constant_pattern, tag_name).group(1)
                        template_values[tag_name] = tag_value
                        return tag_value

                    elif re.match(search_pattern, tag_name):  # Handling {variables}
                        try:
                            tag = Tag.objects.get(tag_name=tag_name)
                            if tag.tag_formula:
                                try:
                                    tag_value = str(eval(tag.tag_formula, {'details': details}))
                                    template_values[tag_name] = tag_value
                                    return tag_value
                                except Exception as error:
                                    print(f"{tag_name} - This tag has error in the formula!Please Check: {error}")
                                    tag_value = f"*{re.match(search_pattern, tag_name).group(1)}*"
                                    template_values[tag_name] = tag_value
                                    return tag_value
                            else:
                                print(f"{tag_name} - This tag does not have a formula! Please check ")
                                tag_value = f"*{re.match(search_pattern, tag_name).group(1)}*"
                                template_values[tag_name] = tag_value
                                return tag_value

                        except Tag.DoesNotExist:
                            print(f"{tag_name} - This tag does not exist! ")
                            tag_value = f"*{re.match(search_pattern, tag_name).group(1)}*"
                            template_values[tag_name] = tag_value
                            return tag_value
                except Exception as error:
                    print(f"Error occured at {tag_name} - {error}")

            # Function to replace the template_content and get the template_values dictionary
            replaced_content = None
            response_code = None
            response_message = None

            try:
                replaced_content = re.sub(search_pattern, replace_tag, template_content)
            except Exception as error:
                print(error)

            send_reports_type = send_reports_type or 'Automatic'
            messages = BusinessMessageSettings.objects.first()
            messaging_vendor = messages.whatsapp_vendor
            try:
                if send_reports_type == 'Automatic':
                    if messaging_vendor.name == 'Meta WhatsApp':
                        secret_key = META_WHATSAPP_KEY
                        phone_id = META_WHATSAPP_PHONE_ID

                        whatsapp_conf = WhatsappConfigurations.objects.first()

                        if whatsapp_conf:
                            if whatsapp_conf.is_active:
                                secret_key = whatsapp_conf.secret_key
                                phone_id = whatsapp_conf.phone_id

                        url = f'https://graph.facebook.com/v18.0/{phone_id}/messages'

                        template_values_list = []
                        # Iterating the template_values to create list of parameters required for passing variables into
                        # template(MWA)
                        for key, value in template_values.items():
                            template_values_list.append({
                                "type": "text",
                                "text": value
                            })

                        # Data and format for sending MWA sms
                        headers = {
                            'Authorization': f'Bearer {secret_key}',
                            'Content-Type': 'application/json'
                        }

                        data = {
                            'messaging_product': 'whatsapp',
                            'to': numbers,
                            'type': 'template',
                            'template': {
                                'name': mwa_template.templateId,
                                'language': {'code': 'en'},
                                "components": [{
                                    "type": "body",
                                    "parameters": template_values_list
                                }
                                ]
                            }
                        }

                        response = requests.request("POST", url, headers=headers, json=data)
                        response_json = response.json()
                        response_code = response.status_code
                        if response_code == 200:
                            response_message = response_json['messages'][0]['message_status']
                        else:
                            error_msg = str(response_json['error']['message'])
                            response_message = error_msg

                    elif messaging_vendor.name == 'Connect2chat':
                        CONNECT2CHAT_SECRET_KEY = os.environ.get('CONNECT2CHAT_SECRET_KEY')
                        CONNECT2CHAT_ACCOUNT_NO = os.environ.get('CONNECT2CHAT_ACCOUNT_NO')

                        whatsapp_conf = WhatsappConfigurations.objects.first()
                        if whatsapp_conf:
                            if whatsapp_conf.is_active:
                                CONNECT2CHAT_SECRET_KEY = whatsapp_conf.secret_key
                                CONNECT2CHAT_ACCOUNT_NO = whatsapp_conf.phone_id

                        chat = {
                            "secret": CONNECT2CHAT_SECRET_KEY,
                            "account": CONNECT2CHAT_ACCOUNT_NO,
                            "recipient": f"+91{numbers}",
                            "type": "text",
                            "message": replaced_content
                        }

                        response = requests.post(url="https://connect2chat.com/api/send/whatsapp", params=chat)
                        response_json = response.json()
                        response_code = response_json['status']
                        response_message = response_json['message']

                    elif messaging_vendor.name == 'WhatsApp Web':
                        response_code = 200
                        response_message = "Whatsapp SMS sent successfully!"

                    else:
                        pass

                else:
                    messaging_vendor = MessagingVendors.objects.get(name='WhatsApp Web')
                    response_code = 200
                    response_message = "Whatsapp SMS sent successfully!"
            except Exception as error:
                print(error)

            if request:
                serializer_data['message'] = replaced_content
                serializer_data['sent_on'] = datetime.now()
                serializer = serializer.save()
                sms_id = serializer.id
            else:
                sent_on = datetime.now()
                sms = SendAndSaveWhatsAppSMSData(search_id=search_id, numbers=numbers, mwa_template=mwa_template,
                                                 messaging_send_type=messaging_send_type, message=replaced_content,
                                                 sent_on=sent_on)
                sms.save()
                sms_id = sms.id

            # Accessing the MessagingLogsViewSet to save the sms status to db
            messaging_log = WhatsAppMessagingLogsViewSet()
            messaging_log.create(sms_id=sms_id, response_code=response_code, response_message=response_message,
                                 messaging_vendor=messaging_vendor)

            if response_code == 200:
                return Response({"message": "Whatsapp SMS sent successfully", "content": replaced_content,
                                 "response_code": response_code})
            else:
                return Response({'Error': f'Failed to send SMS - {response_message}', "response_code": response_code},
                                status=status.HTTP_400_BAD_REQUEST)

        else:
            print(f"'Error': 'One or more Mandatory parameters missing - search_id,numbers,mwa_template,"
                  f"'messaging_send_type'")
            return Response({"Error": "One or more Mandatory parameters missing - search_id,numbers,mwa_template,"
                                      "messaging_send_type"}, status=status.HTTP_400_BAD_REQUEST)


class SendPDFWhatsAppSMSViewSet(viewsets.ModelViewSet):
    queryset = SendAndSaveWhatsAppSMSData.objects.all()
    serializer_class = SendAndSaveWhatsAppSMSDataSerializer

    # Testing by Wasay
    def upload_local_file(self, file_path, access_token, phone_number_id):
        url = f"https://graph.facebook.com/v18.0/{phone_number_id}/media"
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        with open(file_path, 'rb') as file_data:
            files = {
                'file': (file_path, file_data, 'application/pdf')
            }
            data = {
                'messaging_product': 'whatsapp',
                'type': 'document'
            }
            response = requests.post(url, headers=headers, files=files, data=data)
        if response.status_code == 200:
            return response.json().get('id')
        else:
            print("Error uploading file:", response.json())
            return None
    
    def create(self, request=None, search_id=None, numbers=None, mwa_template=None, messaging_send_type=None,
               client=None, test_id=None, test_ids=None, receipt=None, send_reports_type=None,letterhead=None,file_location=None, *args,
               **kwargs):
        if request:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer_data = serializer.validated_data
            search_id = serializer_data['search_id']
            numbers = serializer_data['numbers']
            mwa_template = serializer_data['mwa_template']
            messaging_send_type = serializer_data['messaging_send_type']
            client = serializer_data['client']
            test_id = serializer_data['test_id']
            receipt = serializer_data['receipt']
            send_reports_type = serializer_data['send_reports_type']
            file_location = serializer_data['file_location']

            serializer_data['sent_on'] = datetime.now()
            print(f"This is from request: {search_id}, {numbers}, {mwa_template}, {messaging_send_type}, {client}")

        else:
            print(f"This is from kwargs: {search_id}, {numbers}, {mwa_template}, {messaging_send_type}, {client}")

        if search_id and numbers and mwa_template and messaging_send_type and client:
            # Collecting the data of given id and msg_type
            details = {}

            try:
                details = template_data(search_id, messaging_send_type, client, test_id, test_ids, receipt, letterhead)
            except Exception as error:
                print(f"While fetching details,-{error}")

            # Regex search to get all the values with { }
            search_pattern = r"\{(.*?)\}"
            constant_pattern = r'{Constant:\s*([^}]*)\s*}'
            template_content = mwa_template.templateContent
            template_values = {}
            # print(details)
            print(template_content, 'template content')

            def replace_tag(match):
                tag_name = match.group(0)  # Gets the matched content including curly braces
                try:
                    if re.match(constant_pattern, tag_name):  # Handling {Constants}
                        tag_value = re.match(constant_pattern, tag_name).group(1)
                        template_values[tag_name] = tag_value
                        return tag_value

                    elif re.match(search_pattern, tag_name):  # Handling {variables}
                        try:
                            tag = Tag.objects.get(tag_name=tag_name)
                            print('here')
                            if tag.tag_formula:
                                try:
                                    tag_value = str(eval(tag.tag_formula, {'details': details}))
                                    template_values[tag_name] = tag_value
                                    return tag_value
                                except Exception as error:
                                    print(f"{tag_name} - This tag has error in the formula!Please Check: {error}")
                                    tag_value = f"*{re.match(search_pattern, tag_name).group(1)}*"
                                    template_values[tag_name] = tag_value
                                    return tag_value
                            else:
                                print(f"{tag_name} - This tag does not have a formula! Please check ")
                                tag_value = f"*{re.match(search_pattern, tag_name).group(1)}*"
                                template_values[tag_name] = tag_value
                                return tag_value

                        except Tag.DoesNotExist:
                            print(f"{tag_name} - This tag does not exist! ")
                            tag_value = f"*{re.match(search_pattern, tag_name).group(1)}*"
                            template_values[tag_name] = tag_value
                            return tag_value
                except Exception as error:
                    print(f"Error occured at {tag_name} - {error}")
            # Function to replace the template_content and get the template_values dictionary
            replaced_content = None
            response_code = None
            response_message = None

            try:
                replaced_content = re.sub(search_pattern, replace_tag, template_content)
            except Exception as error:
                print(error)

            send_reports_type = send_reports_type or 'Automatic'
            messages = BusinessMessageSettings.objects.first()
            messaging_vendor = messages.whatsapp_vendor
            # print(file_location, 'file location')
            try:
                if send_reports_type == 'Automatic':
                    if messaging_vendor.name == 'Meta WhatsApp':
                        secret_key = META_WHATSAPP_KEY
                        phone_id = META_WHATSAPP_PHONE_ID

                        whatsapp_conf = WhatsappConfigurations.objects.first()

                        if whatsapp_conf:
                            if whatsapp_conf.is_active:
                                secret_key = whatsapp_conf.secret_key
                                phone_id = whatsapp_conf.phone_id

                        url = f'https://graph.facebook.com/v18.0/{phone_id}/messages'

                        template_values_list = []
                        # Iterating the template_values to create list of parameters required for passing variables into
                        # template(MWA)
                        for key, value in template_values.items():
                            template_values_list.append({
                                "type": "text",
                                "text": value
                            })

                        # Data and format for sending MWA sms
                        headers = {
                            'Authorization': f'Bearer {secret_key}',
                            'Content-Type': 'application/json'
                        }

                        media_id = self.upload_local_file(file_location, search_id, phone_id)

                        if media_id:
                            print("Upload successful. Media ID:", media_id)
                        else:
                            print("Upload failed. No media_id received.")
                            return None

                        data = {
                            'messaging_product': 'whatsapp',
                            'to': numbers,
                            'type': 'template',
                            'template': {
                                'name': mwa_template.templateId,
                                'language': {'code': 'en'},
                                "components": [
                                    {
                                        "type": "header",
                                        "parameters": [
                                            {"type": "document", "document": {
                                                "id": media_id,
                                                "filename": "test_report.pdf"},
                                             }
                                        ]
                                    },
                                    {
                                    "type": "body",
                                    "parameters": template_values_list
                                }
                                ]
                            }
                        }

                        
                        
                        
                        response = requests.request("POST", url, headers=headers, json=data)
                        response_json = response.json()
                        print(response, 'response')
                        print(response_json, 'response json data')
                        response_code = response.status_code
                        if response_code == 200:
                            response_message = response_json['messages'][0]['message_status']
                        else:
                            error_msg = str(response_json['error']['message'])
                            response_message = error_msg

                else:
                    messaging_vendor = MessagingVendors.objects.get(name='WhatsApp Web')
                    response_code = 200
                    response_message = "Whatsapp SMS sent successfully!"
            except Exception as error:
                print(error)

            if request:
                serializer_data['message'] = replaced_content
                serializer_data['sent_on'] = datetime.now()
                serializer = serializer.save()
                sms_id = serializer.id
            else:
                sent_on = datetime.now()
                sms = SendAndSaveWhatsAppSMSData(search_id=search_id, numbers=numbers, mwa_template=mwa_template,
                                                 messaging_send_type=messaging_send_type, message=replaced_content,
                                                 sent_on=sent_on)
                sms.save()
                sms_id = sms.id

                # Accessing the MessagingLogsViewSet to save the sms status to db
            messaging_log = WhatsAppMessagingLogsViewSet()
            messaging_log.create(sms_id=sms_id, response_code=response_code, response_message=response_message,
                                 messaging_vendor=messaging_vendor)

            if response_code == 200:
                return Response({"message": "Whatsapp SMS sent successfully", "content": replaced_content,
                                 "response_code": response_code})
            else:
                return Response({'Error': f'Failed to send SMS - {response_message}', "response_code": response_code},
                                status=status.HTTP_400_BAD_REQUEST)

        else:
            print(f"'Error': 'One or more Mandatory parameters missing - search_id,numbers,mwa_template,"
              f"'messaging_send_type'")
        return Response({"Error": "One or more Mandatory parameters missing - search_id,numbers,mwa_template,"
                                  "messaging_send_type"}, status=status.HTTP_400_BAD_REQUEST)





