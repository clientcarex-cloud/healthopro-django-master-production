import os
import re

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.settings import api_settings
from datetime import datetime
import requests
from rest_framework import generics, viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView

from healtho_pro_user.models.business_models import BusinessProfiles, GlobalMessagingSettings
from healtho_pro_user.models.users_models import Client
from pro_laboratory.filters import BulkMessagingHistoryFilter
from pro_laboratory.models.bulk_messaging_models import BulkMessagingLogs, BulkSendSMSData, \
    BulkSendAndSaveWhatsAppSMSData, BulkWhatsAppMessagingLogs, BulkMessagingTemplates, \
    BusinessMessagesCredits, BulkMessagingHistory
from pro_laboratory.models.client_based_settings_models import BusinessMessageSettings, ClientWiseMessagingTemplates
from pro_laboratory.models.doctors_models import LabDoctors
from pro_laboratory.models.global_models import LabStaff
from pro_laboratory.models.patient_models import Patient, LabPatientInvoice, LabPatientTests
from pro_laboratory.serializers.bulk_messaging_serializers import BulkMessagingSerializer, BulkMessagingLogsSerializer, \
    BulkSendSMSDataSerializer, BulkSendAndSaveWhatsAppSMSDataSerializer, BulkMessagingTemplatesSerializer, \
    BusinessMessagesCreditsSerializer, BulkMessagingHistorySerializer
from pro_universal_data.models import MessagingSendType, Tag, MessagingVendors, MessagingServiceTypes
from pro_universal_data.template_data import template_data
from pro_universal_data.views import FAST2SMS_KEY
from rest_framework.exceptions import ValidationError


class BulkMessagingTemplatesViewSet(viewsets.ModelViewSet):
    queryset = BulkMessagingTemplates.objects.all()
    serializer_class = BulkMessagingTemplatesSerializer

    def get_queryset(self):
        queryset = BulkMessagingTemplates.objects.all()
        type = self.request.query_params.get('type')
        if type is not None:
            queryset = queryset.filter(messaging_service_types=type)
        return queryset

    def perform_create(self, serializer):
        instance = serializer.save()

        client_wise_templates = ClientWiseMessagingTemplates.objects.first()
        client_wise_templates.bulk_templates.add(instance)

        return Response(serializer.data)



class BulkWhatsAppMessagingLogsViewSet(viewsets.ModelViewSet):
    queryset = BulkWhatsAppMessagingLogs.objects.all()
    serializer_class = BulkMessagingLogsSerializer

    def create(self, sms_id=None, response=None, *args, **kwargs):
        response_json = response.json()
        response_code = response.status_code
        if response_code == 200:
            response_message = response_json['messages'][0]['message_status']
        else:
            error_msg = str(response_json['error']['message'])
            response_message = error_msg

        # print(response_code, response_message)

        sms = BulkSendAndSaveWhatsAppSMSData.objects.get(pk=sms_id)
        messaging_vendor = MessagingVendors.objects.get(name='Meta WhatsApp')
        status = f"{response_code}, {response_message}"
        message = sms.message
        businessid = sms.mwa_template.sender_id
        messaging_send_type = sms.messaging_send_type
        numbers = sms.numbers
        sent_on = sms.sent_on

        try:
            messaging_logs = BulkWhatsAppMessagingLogs(sms=sms, messaging_vendor=messaging_vendor, status=status,
                                                       message=message, response_code=response_code,
                                                       businessid=businessid, messaging_send_type=messaging_send_type,
                                                       numbers=numbers, sent_on=sent_on)
            messaging_logs.save()
        except Exception as error:
            print(error)




META_WHATSAPP_KEY = os.environ.get('META_WHATSAPP_KEY')
META_WHATSAPP_PHONE_ID = os.environ.get('META_WHATSAPP_PHONE_ID')
META_WHATSAPP_BUSINESS_ID = os.environ.get('META_WHATSAPP_BUSINESS_ID')


class BulkSendAndSaveWhatsAppSMSViewset(viewsets.ModelViewSet):
    queryset = BulkSendAndSaveWhatsAppSMSData.objects.all()
    serializer_class = BulkSendAndSaveWhatsAppSMSDataSerializer

    secret_key = META_WHATSAPP_KEY
    phone_id = META_WHATSAPP_PHONE_ID
    b_account_id = META_WHATSAPP_BUSINESS_ID

    url = f'https://graph.facebook.com/v18.0/{phone_id}/messages'

    def create(self, request=None, search_id=None, numbers=None, mwa_template=None, messaging_send_type=None,
               test_id=None, receipt=None, *args,
               **kwargs):
        if request:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer_data = serializer.validated_data
            search_id = serializer_data['search_id']
            numbers = serializer_data['numbers']
            mwa_template = serializer_data['mwa_template']
            messaging_send_type = serializer_data['messaging_send_type']
            test_id = serializer_data['test_id']
            receipt = serializer_data['receipt']

            serializer_data['sent_on'] = datetime.now()
            print(f"This is from request: {search_id}, {numbers}, {mwa_template}, {messaging_send_type}")

        else:
            print(f"This is from kwargs: {search_id}, {numbers}, {mwa_template}, {messaging_send_type}")

        if search_id and numbers and mwa_template and messaging_send_type:
            # Collecting the data of given id and msg_type
            details = {}

            try:
                details = template_data(search_id, messaging_send_type, test_id, receipt)
            except Exception as error:
                print(f"While fetching details,-{error}")

            # print(details)

            # Regex search to get all the values with { }
            search_pattern = r"\{(.*?)\}"
            constant_pattern = r'{Constant:\s*([^}]*)\s*}'
            template_content = mwa_template.templateContent
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

            template_values_list = []

            # Iterating the template_values to create list of parameters required for passing variables into template(MWA)
            for key, value in template_values.items():
                template_values_list.append({
                    "type": "text",
                    "text": value
                })

            print(template_values_list)

            # Data and format for sending MWA sms
            headers = {
                'Authorization': f'Bearer {self.secret_key}',
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

            try:
                response = requests.request("POST", self.url, headers=headers, json=data)

            except Exception as error:
                print(error)

            # print(response.json())

            if request:
                serializer_data['message'] = replaced_content
                serializer_data['sent_on'] = datetime.now()
                serializer = serializer.save()
                sms_id = serializer.id
            else:
                sent_on = datetime.now()
                sms = BulkSendAndSaveWhatsAppSMSData(search_id=search_id, numbers=numbers, mwa_template=mwa_template,
                                                     messaging_send_type=messaging_send_type, message=replaced_content,
                                                     sent_on=sent_on)
                sms.save()
                sms_id = sms.id

            # Accessing the MessagingLogsViewSet to save the sms status to db
            messaging_log = BulkWhatsAppMessagingLogsViewSet()
            messaging_log.create(sms_id=sms_id, response=response)

            if response.status_code == 200:
                # print(f"'message': 'SMS sent successfully'")
                return Response({"message": "SMS sent successfully"})
            else:
                response_json = response.json()
                error_msg = str(response_json['error']['message'])

                print(f"'Error': 'Failed to send SMS - {error_msg}'")
                return Response({'Error': f"Failed to send SMS - {error_msg}"}, status=response.status_code)

        else:
            print(f"'Error': 'One or more Mandatory parameters missing - search_id,numbers,mwa_template,"
                  f"'messaging_send_type'")
            return Response({"Error": "One or more Mandatory parameters missing - search_id,numbers,mwa_template,"
                                      "messaging_send_type"}, status=status.HTTP_400_BAD_REQUEST)


# Program to access SendSMSDataViewSet and MessagingLogsViewset
def bulk_send_and_log_whatsapp_sms(search_id=None, numbers=None, mwa_template=None, messaging_send_type=None,
                                   test_id=None, receipt=None):
    print(search_id, numbers, mwa_template, messaging_send_type, test_id, receipt)

    send_sms = BulkSendAndSaveWhatsAppSMSViewset()
    response = send_sms.create(search_id=search_id, numbers=numbers, mwa_template=mwa_template,
                               messaging_send_type=messaging_send_type, test_id=test_id,receipt=receipt)

    return Response(response.data, status=response.status_code)


class BulkMessagingLogsViewSet(viewsets.ModelViewSet):
    queryset = BulkMessagingLogs.objects.all()
    serializer_class = BulkMessagingLogsSerializer

    def create(self, sms_id=None, response=None, *args, **kwargs):
        response_json = response.json()
        try:
            response_code = response_json['status_code']
        except:
            response_code = response.status_code

        response_message = response_json['message']

        sms = BulkSendSMSData.objects.get(pk=sms_id)
        messaging_vendor = MessagingVendors.objects.get(name='Fast2SMS')
        status = f"{response_code}, {response_message}"
        message = sms.message
        businessid = sms.sms_template.sender_id
        messaging_send_type = sms.messaging_send_type
        numbers = sms.numbers
        sent_on = sms.sent_on
        messaging_logs = BulkMessagingLogs(sms=sms, messaging_vendor=messaging_vendor, response_code=response_code,
                                           status=status, message=message,
                                           businessid=businessid, messaging_send_type=messaging_send_type,
                                           numbers=numbers, sent_on=sent_on)
        messaging_logs.save()


class BulkSendAndSaveSMSDataViewset(viewsets.ModelViewSet):
    queryset = BulkSendSMSData.objects.all()
    serializer_class = BulkSendSMSDataSerializer
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

            serializer_data['sent_on'] = datetime.now()
            # print(f"This is from request: {search_id}, {numbers}, {sms_template}, {messaging_send_type}, {client}")

        else:
            print(f"This is from kwargs: {search_id}, {numbers}, {sms_template}, {messaging_send_type}, {client}")

        if search_id and numbers and sms_template and messaging_send_type:
            # Collecting the data of given id and msg_type
            details = {}

            try:
                details = template_data(search_id, messaging_send_type, client)
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
                sms = BulkSendSMSData(search_id=search_id, numbers=numbers, sms_template=sms_template,
                                      messaging_send_type=messaging_send_type, message=replaced_content,
                                      sent_on=sent_on)
                sms.save()
                sms_id = sms.id

            # Accessing the MessagingLogsViewSet to save the sms status to db
            messaging_log = BulkMessagingLogsViewSet()
            messaging_log.create(sms_id=sms_id, response=response)

            if response.status_code == 200:
                # print(f"'message': 'SMS sent successfully'")
                return Response({"message": "SMS sent successfully"})
            else:
                print(f"'Error': 'Failed to send SMS', 'Message': {error_msg} ")
                return Response({"Error": "Failed to send SMS", "Message": error_msg}, status=response.status_code)

        else:
            print(f"'Error': 'One or more Mandatory parameters missing - search_id,numbers,sms_template,"
                  f"'messaging_send_type'")
            return Response({"Error": "One or more Mandatory parameters missing - search_id,numbers,sms_template,"
                                      "messaging_send_type"}, status=status.HTTP_400_BAD_REQUEST)


def bulk_send_and_log_sms(search_id=None, numbers=None, sms_template=None, messaging_send_type=None, client=None,
                          from_date=None,
                          to_date=None):

    send_sms_data = BulkSendAndSaveSMSDataViewset()
    response = send_sms_data.create(search_id=search_id, numbers=numbers, sms_template=sms_template,
                                    messaging_send_type=messaging_send_type,from_date=from_date,
                                    to_date=to_date)

    return Response(response.data, status=response.status_code)
    # else:
    #     return Response({"Status": "Messaging service is inactive for this Business"}, status=status.HTTP_200_OK)


class BulkBusinessMessagingStatisticsView(generics.ListAPIView):
    def get(self, request=None,client=None,service_type=None, *args, **kwargs):
        if request:
            client = self.request.query_params.get('client', None)
            service_type = self.request.query_params.get('type', None)
        else:
            print(f"{client} {service_type}")

        if not client:
            return Response({"Error": "No business is selected!"})

        if service_type == '2':
            whatsapp_counter = BusinessMessagesCredits.objects.filter(messaging_service_types=service_type).last()

            remaining_messages = whatsapp_counter.new_credits - whatsapp_counter.total_messages

            return Response({"balance": whatsapp_counter.new_credits, "total_messages_sent": whatsapp_counter.total_messages,
                             "remaining_messages": remaining_messages})
        else:
            sms_counter = BusinessMessagesCredits.objects.filter(messaging_service_types=service_type).last()

            remaining_messages = sms_counter.new_credits - sms_counter.total_messages

            return Response(
                {"balance": sms_counter.new_credits, "total_messages_sent": sms_counter.total_messages,
                 "remaining_messages": remaining_messages})


class BulkSMSAPIView(generics.CreateAPIView):
    serializer_class = BulkMessagingSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        recipient_type = validated_data['recipient_type']
        recipient_ids = validated_data['recipient_ids']
        template_id = validated_data['template_id']

        sms_counter = BusinessMessagesCredits.objects.filter(messaging_service_types=1).last()
        if not sms_counter:
            raise ValidationError(f"Please buy credits to send messages.")

        recipient_type = MessagingSendType.objects.get(pk=recipient_type)
        if recipient_type.name == 'Patients':
            recipients = Patient.objects.filter(id__in=recipient_ids)
        elif recipient_type.name == 'Doctors':
            recipients = LabDoctors.objects.filter(id__in=recipient_ids)
        elif recipient_type.name == 'Staff':
            recipients = LabStaff.objects.filter(id__in=recipient_ids, is_superadmin=False)
        elif recipient_type.name == 'Admin':
            recipients = LabStaff.objects.filter(id__in=recipient_ids, is_superadmin=True)
        else:
            return Response({'detail': 'Invalid recipient type'}, status=400)

        template = BulkMessagingTemplates.objects.get(pk=template_id)
        messages = BusinessMessageSettings.objects.first()
        global_messages = GlobalMessagingSettings.objects.filter(type__id=1).first()
        client = request.client

        if messages.is_sms_active and global_messages.is_active:
            from pro_laboratory.views.client_based_settings_views import check_template_is_active_for_business

            is_template_active = check_template_is_active_for_business(template=template, client=client,
                                                                       bulk_templates=True)

            if not is_template_active:
                return Response(
                    {"Error": "Template is Inactive for the business, Pls make it Active!", "response_code": 400},

                    status=status.HTTP_400_BAD_REQUEST)

            credits = BusinessMessagesCredits.objects.filter(messaging_service_types__name='SMS').last()

            if not credits:
                return Response(
                    {"Error": "You don't have credits to send messages!Pls contact Admin!", "response_code": 400},
                    status=status.HTTP_400_BAD_REQUEST)

            balance = credits.new_credits - credits.total_messages

            if balance < 1:
                return Response(

                    {"Error": "You don't have credits to send messages!Pls contact Admin!", "response_code": 400},

                    status=status.HTTP_400_BAD_REQUEST)

            if balance < len(recipients):
                return Response(

                    {"Error": "You don't have credits. Credit Balance is Insufficient!Pls contact Admin!",
                     "response_code": 400}, status=status.HTTP_400_BAD_REQUEST)

            successful_messages=0

            for recipient in recipients:
                response = bulk_send_and_log_sms(
                    search_id=recipient.id,
                    numbers=recipient.mobile_number,
                    sms_template=BulkMessagingTemplates.objects.get(pk=template_id),
                    messaging_send_type=MessagingSendType.objects.get(name=recipient_type.name),
                    client=client
                )

                if response.status_code == 200:
                    successful_messages+=1
            credits.total_messages+=successful_messages
            credits.save()

            user = request.user
            lab_staff = LabStaff.objects.filter(mobile_number=user.phone_number).first()

            history = BulkMessagingHistory.objects.create(template=template, sent_messages=successful_messages,
                                                          created_by=lab_staff)


            return Response({'detail': f'Messages sent to {recipient_type} successfully'}, status=200)

        else:
            if not global_messages.is_active:
                return Response({"Error": f"{global_messages.remarks}", "response_code": 400},
                                status=status.HTTP_400_BAD_REQUEST)

            else:
                return Response({"Error": "Messaging service is inactive for this Business", "response_code": 400},
                                status=status.HTTP_400_BAD_REQUEST)


class BulkWhatsAppMessagingAPIView(generics.CreateAPIView):
    serializer_class = BulkMessagingSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        recipient_type = validated_data['recipient_type']
        recipient_ids = validated_data['recipient_ids']
        template_id = validated_data['template_id']

        recipient_type = MessagingSendType.objects.get(pk=recipient_type)
        if recipient_type.name == 'Patients':
            recipients = Patient.objects.filter(id__in=recipient_ids)
        elif recipient_type.name == 'Doctors':
            recipients = LabDoctors.objects.filter(id__in=recipient_ids)
        elif recipient_type.name == 'Staff':
            recipients = LabStaff.objects.filter(id__in=recipient_ids, is_superadmin=False)
        elif recipient_type.name == 'Admin':
            recipients = LabStaff.objects.filter(id__in=recipient_ids, is_superadmin=True)
        else:
            return Response({'detail': 'Invalid recipient type'}, status=400)


        template = BulkMessagingTemplates.objects.get(pk=template_id)
        messages = BusinessMessageSettings.objects.first()
        global_messages = GlobalMessagingSettings.objects.filter(type__id=2).first()
        client = request.client

        if messages.is_whatsapp_active and global_messages.is_active:
            from pro_laboratory.views.client_based_settings_views import check_template_is_active_for_business
            is_template_active = check_template_is_active_for_business(template=template, client=client,
                                                                       bulk_templates=True)

            if not is_template_active:
                return Response(
                    {"Error": "Template is Inactive for the business, Pls make it Active!", "response_code": 400},
                    status=status.HTTP_400_BAD_REQUEST)

            credits = BusinessMessagesCredits.objects.filter(messaging_service_types__name='WhatsApp').last()
            if not credits:
                return Response(
                    {"Error": "You don't have credits to send messages!Pls contact Admin!", "response_code": 400},
                    status=status.HTTP_400_BAD_REQUEST)

            balance = credits.new_credits - credits.total_messages

            if balance < 1:
                return Response(
                    {"Error": "You don't have credits to send messages!Pls contact Admin!", "response_code": 400},
                    status=status.HTTP_400_BAD_REQUEST)

            if balance < len(recipients):
                return Response(
                    {"Error": "You don't have credits. Credit Balance is Insufficient!Pls contact Admin!",
                     "response_code": 400},
                    status=status.HTTP_400_BAD_REQUEST)

            successful_messages = 0

            for recipient in recipients:
                response = bulk_send_and_log_whatsapp_sms(search_id=recipient.id, numbers=recipient.mobile_number,
                                               mwa_template=template,
                                               messaging_send_type=MessagingSendType.objects.get(name=recipient_type.name),
                                               )

                if response.status_code == 200:
                    successful_messages += 1

            credits.total_messages += successful_messages
            credits.save()

            user = request.user
            lab_staff = LabStaff.objects.filter(mobile_number=user.phone_number).first()

            history = BulkMessagingHistory.objects.create(template=template, sent_messages=successful_messages,
                                                          created_by=lab_staff)

            return Response({'detail': f'WhatsAppMessages sent to {recipient_type} successfully'}, status=200)

        else:
            if not global_messages.is_active:
                return Response({"Error": f"{global_messages.remarks}", "response_code": 400},
                                status=status.HTTP_400_BAD_REQUEST)

            else:
                return Response({"Error": "Messaging service is inactive for this Business", "response_code": 400},
                                status=status.HTTP_400_BAD_REQUEST)

class BusinessMessagesCreditsView(APIView):
    def get(self, request):
        counters = BusinessMessagesCredits.objects.all()
        service_type = self.request.query_params.get('type')

        if service_type is not None:
            counters = counters.filter(messaging_service_types=service_type)

        paginator = api_settings.DEFAULT_PAGINATION_CLASS()
        page = paginator.paginate_queryset(counters, request)
        if page is not None:
            sms_serializer = BusinessMessagesCreditsSerializer(page, many=True)
            return paginator.get_paginated_response(sms_serializer.data)

        sms_serializer = BusinessMessagesCreditsSerializer(counters, many=True)
        return Response(sms_serializer.data, status=status.HTTP_201_CREATED)

    def post(self, request):
        new_credits = request.data.get('new_credits')
        service_type = request.data.get('service_type')

        # Create a new BusinessWhatsAppCounter entry
        new_counter = BusinessMessagesCredits.objects.create(
            new_credits=new_credits,
            total_messages=0,
            messaging_service_types=MessagingServiceTypes.objects.get(id=service_type)
        )
        serializer = BusinessMessagesCreditsSerializer(new_counter)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BulkMessagingCampaignForRecipients(generics.CreateAPIView):
    queryset = BulkSendAndSaveWhatsAppSMSData.objects.all()

    secret_key = META_WHATSAPP_KEY
    phone_id = META_WHATSAPP_PHONE_ID

    url = f'https://graph.facebook.com/v18.0/{phone_id}/messages'

    def create(self, numbers=None, template=None, client=None,details=None, *args, **kwargs):
        try:
            # Regex search to get all the values with { }
            search_pattern = r"\{(.*?)\}"
            constant_pattern = r'{Constant:\s*([^}]*)\s*}'
            template_content = template.templateContent
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
                            tag_value = details.get(f'{tag_name}',"")
                            template_values[tag_name] = str(tag_value)
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
                except Exception as error:
                    print(error)

            replaced_content = None
            try:
                replaced_content = re.sub(search_pattern, replace_tag, template_content)
            except Exception as error:
                print(error)

            template_values_list=[]

            for key, value in template_values.items():
                template_values_list.append({
                    "type": "text",
                    "text": value
                })

            # Data and format for sending MWA sms
            headers = {
                'Authorization': f'Bearer {self.secret_key}',
                'Content-Type': 'application/json'
            }

            data = {
                'messaging_product': 'whatsapp',
                'to': numbers,
                'type': 'template',
                'template': {
                    'name': template.templateId,

                    'language': {'code': 'en'},
                    "components": [{
                        "type": "body",
                        "parameters": template_values_list
                    }
                    ]
                }
            }

            try:
                response = requests.request("POST", self.url, headers=headers, json=data)

            except Exception as error:
                print(error)

            messaging_send_type=MessagingSendType.objects.get(pk=1)

            sent_on = datetime.now()
            sms = BulkSendAndSaveWhatsAppSMSData(search_id=None, numbers=numbers, mwa_template=template,
                                                 messaging_send_type=messaging_send_type, message=template.content,
                                                 sent_on=sent_on)

            sms.save()
            sms_id = sms.id

            # Accessing the MessagingLogsViewSet to save the sms status to db
            messaging_log = BulkWhatsAppMessagingLogsViewSet()
            messaging_log.create(sms_id=sms_id, response=response)

            if response.status_code == 200:
                # print(f"'message': 'SMS sent successfully'")
                return Response({"message": "SMS sent successfully"})
            else:
                response_json = response.json()
                error_msg = str(response_json['error']['message'])

                print(f"'Error': 'Failed to send SMS - {error_msg}'")
                return Response({'Error': f"Failed to send SMS - {error_msg}"}, status=response.status_code)

        except Exception as error:
            print(error)
            return Response({"error":f"{error}"})




class BulkMessagingCampaignForRecipientsForSMS(generics.CreateAPIView):
    queryset = BulkSendSMSData.objects.all()
    secret_key = FAST2SMS_KEY
    url = "https://www.fast2sms.com/dev/bulkV2"


    def create(self, numbers=None, template=None, client=None,details=None, *args, **kwargs):
        try:
            # Regex search to get all the values with { }
            search_pattern = r"\{(.*?)\}"
            constant_pattern = r'{Constant:\s*([^}]*)\s*}'
            template_content = template.templateContent
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
                            tag_value = details.get(f'{tag_name}',"")
                            template_values[tag_name] = str(tag_value)
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
                except Exception as error:
                    print(error)

            replaced_content = None
            try:
                replaced_content = re.sub(search_pattern, replace_tag, template_content)
            except Exception as error:
                print(error)
            print(replaced_content)

            # Converting variable_values and keys to be passable into API
            variable_keys = list(template_values.keys())
            variable_values = list(template_values.values())

            variable_keys = '|'.join(variable_keys)
            variable_values = '|'.join(variable_values)


            # Code for FAST2SMS API
            querystring = {
                "authorization": self.secret_key,
                "route": template.route,
                "sender_id": template.sender_id,
                "message": template.templateId,
                "variables_values": variable_values,
                "mapping": variable_keys,
                "numbers": numbers,
            }

            headers = {
                'cache-control': "no-cache"
            }

            response = requests.request("GET", self.url, headers=headers, params=querystring)
            response_data = response.json()
            error_msg = response_data['message']

            messaging_send_type = MessagingSendType.objects.get(pk=1)
            sent_on = datetime.now()
            sms = BulkSendSMSData(search_id=None, numbers=numbers, sms_template=template,
                                  messaging_send_type=messaging_send_type, message=template.templateContent,
                                  sent_on=sent_on)
            sms.save()
            sms_id = sms.id

            # Accessing the MessagingLogsViewSet to save the sms status to db
            messaging_log = BulkMessagingLogsViewSet()
            messaging_log.create(sms_id=sms_id, response=response)

            return Response({"message": "SMS sent successfully"})

        except Exception as error:
            print(error)
            return Response({"error":f"{error}"})

#
# Program to access SendSMSDataViewSet and MessagingLogsViewset
class SendAndLogCampaignMessagesView(generics.CreateAPIView):
    def post(self, request, *args, **kwargs):
        data = request.data
        template_id=data.get('template_id')
        message_send_type=data.get('message_send_type')
        recipients = data.get('recipients')
        client=request.client
        messages = BusinessMessageSettings.objects.get(client=client)

        template = BulkMessagingTemplates.objects.get(pk=template_id)

        messaging_service_types = template.messaging_service_types.name

        if messaging_service_types == 'WhatsApp':
            global_messages = GlobalMessagingSettings.objects.filter(type__id=2).first()

            if messages.is_whatsapp_active and global_messages.is_active:
                from pro_laboratory.views.client_based_settings_views import check_template_is_active_for_business
                is_template_active = check_template_is_active_for_business(template=template, client=client, bulk_templates=True)

                if not is_template_active:
                    return Response(
                        {"Error": "Template is Inactive for the business, Pls make it Active!", "response_code": 400},
                        status=status.HTTP_400_BAD_REQUEST)


                credits = BusinessMessagesCredits.objects.filter(messaging_service_types__name='WhatsApp').last()
                if not credits:
                    return Response(
                        {"Error": "You don't have credits to send messages!Pls contact Admin!", "response_code": 400},
                        status=status.HTTP_400_BAD_REQUEST)

                balance = credits.new_credits - credits.total_messages

                if balance < 1:
                    return Response(
                        {"Error": "You don't have credits to send messages!Pls contact Admin!", "response_code": 400},
                        status=status.HTTP_400_BAD_REQUEST)

                if balance < len(recipients):
                    return Response(
                        {"Error": "You don't have credits. Credit Balance is Insufficient!Pls contact Admin!", "response_code": 400},
                        status=status.HTTP_400_BAD_REQUEST)

                send_sms =BulkMessagingCampaignForRecipients()

                successful_messages = 0
                for recipient in recipients:
                    try:
                        # Add `{}` around each key
                        formatted_details = {f"{{{key}}}": value for key, value in recipient.items()}
                        response = send_sms.create(numbers=recipient['mobile_number'],details=formatted_details, template=template, client=request.client)

                        if response.status_code == 200:
                            successful_messages+=1
                    except Exception as error:
                        print(error)

                credits.total_messages += successful_messages
                credits.save()

                user=request.user
                lab_staff = LabStaff.objects.filter(mobile_number=user.phone_number).first()

                history =  BulkMessagingHistory.objects.create(template=template,sent_messages=successful_messages,
                    created_by=lab_staff)

                return Response({"Status": "Message sent successfully!",
                                  "response_code": 200})


            else:
                if not global_messages.is_active:
                    return Response({"Error": f"{global_messages.remarks}", "response_code": 400},
                                    status=status.HTTP_400_BAD_REQUEST)

                else:
                    return Response({"Error": "Messaging service is inactive for this Business", "response_code": 400},
                                    status=status.HTTP_400_BAD_REQUEST)

        elif messaging_service_types == 'SMS':
            global_messages = GlobalMessagingSettings.objects.filter(type__id=1).first()

            if messages.is_sms_active and global_messages.is_active:
                from pro_laboratory.views.client_based_settings_views import check_template_is_active_for_business

                is_template_active = check_template_is_active_for_business(template=template, client=client,
                                                                           bulk_templates=True)

                if not is_template_active:
                    return Response({"Error": "Template is Inactive for the business, Pls make it Active!", "response_code": 400},

                        status=status.HTTP_400_BAD_REQUEST)

                credits = BusinessMessagesCredits.objects.filter(messaging_service_types__name='SMS').last()

                if not credits:
                    return Response(
                        {"Error": "You don't have credits to send messages!Pls contact Admin!", "response_code": 400},
                        status=status.HTTP_400_BAD_REQUEST)

                balance = credits.new_credits - credits.total_messages

                if balance < 1:
                    return Response(

                        {"Error": "You don't have credits to send messages!Pls contact Admin!", "response_code": 400},

                        status=status.HTTP_400_BAD_REQUEST)

                if balance < len(recipients):
                    return Response(

                        {"Error": "You don't have credits. Credit Balance is Insufficient!Pls contact Admin!",
                         "response_code": 400}, status=status.HTTP_400_BAD_REQUEST)

                send_sms = BulkMessagingCampaignForRecipientsForSMS()

                successful_messages=0

                for recipient in recipients:
                    try:
                        formatted_details = {f"{{{key}}}": value for key, value in recipient.items()}
                        response = send_sms.create(numbers=recipient['mobile_number'],details=formatted_details, template=template,
                                                   client=request.client)

                        if response.status_code == 200:
                            successful_messages+=1
                    except Exception as error:
                        print(error)

                credits.total_messages += successful_messages
                credits.save()

                user = request.user
                lab_staff = LabStaff.objects.filter(mobile_number=user.phone_number).first()

                history = BulkMessagingHistory.objects.create(template=template, sent_messages=successful_messages,
                                                              created_by=lab_staff)

                return Response({"Status": "Message sent successfully!", "response_code": 200})

            else:
                if not global_messages.is_active:
                    return Response({"Error": f"{global_messages.remarks}", "response_code": 400},
                                    status=status.HTTP_400_BAD_REQUEST)

                else:
                    return Response({"Error": "Messaging service is inactive for this Business", "response_code": 400},
                                    status=status.HTTP_400_BAD_REQUEST)



class BulkMessagingHistoryView(generics.ListAPIView):
    queryset = BulkMessagingHistory.objects.all()
    serializer_class = BulkMessagingHistorySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = BulkMessagingHistoryFilter




