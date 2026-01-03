from django.core.cache import cache
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, viewsets
from pro_laboratory.models.bulk_messaging_models import BusinessMessagesCredits
from pro_laboratory.models.client_based_settings_models import BusinessMessageSettings
from pro_laboratory.views.messaging_views import SendPDFWhatsAppSMSViewSet
from pro_universal_data.filters import DoctorSharedReportFilter
from pro_universal_data.models import ULabStaffGender, ULabPatientAction, ULabReportType, ULabPatientTitles, \
    ULabPatientAttenderTitles, ULabTestStatus, ULabPaymentModeType, \
    ULabPatientAge, ULabPatientGender, PrintTemplateType, DashBoardOptions, DoctorSharedReport, \
    DepartmentFlowType, UserPermissions, TimeDurationTypes, ULabRelations, ULabFonts, ULabReportsGender, \
    MarketingVisitTypes, \
    UniversalFuelTypes, UniversalVehicleTypes, UniversalBloodGroups, UniversalMaritalStatus, LabEmploymentType, \
    MarketingVisitStatus, MarketingTargetDurations, MarketingTargetTypes, LabStaffAttendanceStatus, \
    MarketingPaymentType, SalaryPaymentModes, LeaveStatus, LeaveTypes, UniversalActionType, PrivilegeCardBenefits, \
    AvailabilityPeriod, ConsultationType, TimeCategory, SourcingLabType, DoctorSalaryPaymentTypes, \
    DoctorTransactionTypes, TaxType, PharmaItemOperationType, SupplierType, UniversalAilments, UniversalDayTimePeriod, \
    UniversalFoodIntake, PatientType
from pro_universal_data.serializers import ULabMenusSerializer, ULabPatientActionSerializer, \
    ULabReportTypeSerializer, ULabPatientTitlesSerializer, ULabPatientAttenderTitlesSerializer, \
    ULabTestStatusSerializer, ULabPaymentModeTypeSerializer, \
    ULabPatientAgeSerializer, ULabPatientGenderSerializer, ULabStaffGenderSerializer, \
    PrintTemplateTypeSerializer, TemplateTagsGetSerializer, DashBoardOptionSerializer, DoctorSharedReportSerializer, \
    DepartmentFlowTypeSerializer, UserPermissionsSerializer, TimeDurationTypesSerializer, \
    ULabRelationsSerializer, ULabFontsSerializer, ULabReportsGenderSerializer, MarketingVisitTypesSerializer, \
    UniversalFuelTypesSerializer, UniversalVehicleTypesSerializer, UniversalBloodGroupsSerializer, \
    UniversalMaritalStatusSerializer, LabEmploymentTypeSerializer, MarketingVisitStatusSerializer, \
    MarketingTargetDurationsSerializer, MarketingTargetTypesSerializer, LabStaffAttendanceStatusSerializer, \
    MarketingPaymentTypeSerializer, SalaryPaymentModesSerializer, LeaveStatusSerializer, LeaveTypesSerializer, \
    UniversalActionTypeSerializer, PrivilegeCardBenefitsSerializer, AvailabilityPeriodSerializer, \
    ConsultationTypeSerializer, TimeCategorySerializer, SourcingLabTypeSerializer, DoctorSalaryPaymentTypesSerializer, \
    DoctorTransactionTypesSerializer, TaxTypeSerializer, PharmaItemOperationTypeSerializer, SupplierTypeSerializer, \
    UniversalAilmentsSerializer, UniversalDayTimePeriodSerializer, UniversalFoodIntakeSerializer, PatientTypeSerializer


class ULabMenusListView(generics.ListAPIView):
    # queryset = ULabMenus.objects.filter(is_active=True)
    serializer_class = ULabMenusSerializer

    def get_queryset(self):
        try:
            client = self.request.client
            cache_key = f'ulab_menu_list_{client}'
            cache_data = cache.get(cache_key)
            if cache_data:
                return cache_data

            business = BusinessProfiles.objects.get(organization_name=client.name)
            obj = BusinessModules.objects.get(business=business)
            queryset = obj.modules.all()
            cache.set(cache_key, queryset)

            return queryset
        except Exception as error:
            print(error)
            business = BusinessProfiles.objects.get(organization_name=self.request.client.name)
            obj = BusinessModules.objects.get(business=business)
            queryset = obj.modules.all()
            return queryset


class ULabPatientGenderViewSet(viewsets.ModelViewSet):
    queryset = ULabPatientGender.objects.all()
    serializer_class = ULabPatientGenderSerializer

    def get_queryset(self):
        try:
            cache_key = 'ulab_patient_gender_list'
            cached_data = cache.get(cache_key)
            if cached_data:
                print(cached_data)
                return cached_data
            queryset = super().get_queryset().order_by('id')
            cache.set(cache_key, queryset)
            print(queryset, '****queryset data****')
            return queryset
        except Exception as e:
            queryset = super().get_queryset()
            return queryset


class ULabReportsGenderViewSet(viewsets.ModelViewSet):
    queryset = ULabReportsGender.objects.all()
    serializer_class = ULabReportsGenderSerializer


class ULabStaffGenderViewSet(viewsets.ModelViewSet):
    queryset = ULabStaffGender.objects.all()
    serializer_class = ULabStaffGenderSerializer


class ULabPatientActionViewSet(viewsets.ModelViewSet):
    queryset = ULabPatientAction.objects.all()
    serializer_class = ULabPatientActionSerializer


class ULabReportTypeListView(generics.ListAPIView):
    queryset = ULabReportType.objects.all()
    serializer_class = ULabReportTypeSerializer


class ULabPatientTitlesViewSet(viewsets.ModelViewSet):
    queryset = ULabPatientTitles.objects.all()
    serializer_class = ULabPatientTitlesSerializer

    def get_queryset(self):
        try:
            cache_key = 'ulab_patient_titles_list'
            cached_data = cache.get(cache_key)
            if cached_data:
                return cached_data
            queryset = super().get_queryset().order_by('id')
            cache.set(cache_key, queryset)
            return queryset
        except Exception as e:
            queryset = super().get_queryset()
            return queryset


class ULabPatientAttenderTitlesViewSet(viewsets.ModelViewSet):
    queryset = ULabPatientAttenderTitles.objects.all()
    serializer_class = ULabPatientAttenderTitlesSerializer

    def get_queryset(self):
        try:
            cache_key = 'ulab_patient_attender_titles_list'
            cached_data = cache.get(cache_key)
            if cached_data:
                return cached_data
            queryset = super().get_queryset().order_by('id')
            cache.set(cache_key, queryset)
            return queryset
        except Exception as e:
            queryset = super().get_queryset()
            return queryset


class ULabTestStatusViewSet(viewsets.ModelViewSet):
    queryset = ULabTestStatus.objects.all()
    serializer_class = ULabTestStatusSerializer


class ULabPaymentModeTypeViewSet(viewsets.ModelViewSet):
    queryset = ULabPaymentModeType.objects.all()
    serializer_class = ULabPaymentModeTypeSerializer

    def get_queryset(self):
        try:
            cache_key = 'ulab_payment_mode_type_list'
            cached_data = cache.get(cache_key)

            if cached_data:
                print(cached_data)
                return cached_data
            queryset = super().get_queryset().order_by('id')
            cache.set(cache_key, queryset)
            return queryset
        except Exception as e:
            queryset = super().get_queryset()
            return queryset


class ULabPatientAgeViewset(viewsets.ModelViewSet):
    queryset = ULabPatientAge.objects.all()
    serializer_class = ULabPatientAgeSerializer

    def get_queryset(self):
        try:
            cache_key = 'ulab_patient_age_list'
            cached_data = cache.get(cache_key)
            if cached_data:
                return cached_data
            queryset = super().get_queryset().order_by('id')
            cache.set(cache_key, queryset)
            return queryset
        except Exception as e:
            queryset = super().get_queryset()
            return queryset


class PrivilegeCardBenefitsViewset(viewsets.ModelViewSet):
    queryset = PrivilegeCardBenefits.objects.filter(is_active=True)
    serializer_class = PrivilegeCardBenefitsSerializer


class AvailabilityPeriodViewset(viewsets.ModelViewSet):
    queryset = AvailabilityPeriod.objects.all()
    serializer_class = AvailabilityPeriodSerializer


class ULabRelationsViewset(viewsets.ModelViewSet):
    queryset = ULabRelations.objects.all()
    serializer_class = ULabRelationsSerializer


class TimeDurationTypesViewset(viewsets.ModelViewSet):
    queryset = TimeDurationTypes.objects.all()
    serializer_class = TimeDurationTypesSerializer


class UniversalVehicleTypesViewset(viewsets.ModelViewSet):
    queryset = UniversalVehicleTypes.objects.all()
    serializer_class = UniversalVehicleTypesSerializer


class UniversalFuelTypesViewset(viewsets.ModelViewSet):
    queryset = UniversalFuelTypes.objects.all()
    serializer_class = UniversalFuelTypesSerializer


class MarketingVisitTypesViewset(viewsets.ModelViewSet):
    queryset = MarketingVisitTypes.objects.all()
    serializer_class = MarketingVisitTypesSerializer


class MarketingVisitStatusViewset(viewsets.ModelViewSet):
    queryset = MarketingVisitStatus.objects.all()
    serializer_class = MarketingVisitStatusSerializer


class UniversalBloodGroupsViewset(viewsets.ModelViewSet):
    queryset = UniversalBloodGroups.objects.all()
    serializer_class = UniversalBloodGroupsSerializer


class UniversalMaritalStatusViewset(viewsets.ModelViewSet):
    queryset = UniversalMaritalStatus.objects.all()
    serializer_class = UniversalMaritalStatusSerializer


class UniversalActionTypeViewset(viewsets.ModelViewSet):
    queryset = UniversalActionType.objects.all()
    serializer_class = UniversalActionTypeSerializer


class PharmaItemOperationTypeViewSet(viewsets.ModelViewSet):
    queryset = PharmaItemOperationType.objects.all().order_by('id')
    serializer_class = PharmaItemOperationTypeSerializer



class ConsultationTypeViewSet(viewsets.ModelViewSet):
    queryset = ConsultationType.objects.all()
    serializer_class = ConsultationTypeSerializer



class SourcingLabTypeViewSet(viewsets.ModelViewSet):
    queryset = SourcingLabType.objects.filter(is_active=True)
    serializer_class = SourcingLabTypeSerializer


class UniversalAilmentsViewSet(viewsets.ModelViewSet):
    queryset = UniversalAilments.objects.filter(is_active=True)
    serializer_class = UniversalAilmentsSerializer


class UniversalDayTimePeriodViewSet(viewsets.ModelViewSet):
    queryset = UniversalDayTimePeriod.objects.filter(is_active=True)
    serializer_class = UniversalDayTimePeriodSerializer


class UniversalFoodIntakeViewSet(viewsets.ModelViewSet):
    queryset = UniversalFoodIntake.objects.filter(is_active=True)
    serializer_class = UniversalFoodIntakeSerializer




# thirdparty apis
import logging
import os
import re
from datetime import datetime
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
from healtho_pro_user.models.business_models import BusinessProfiles, GlobalMessagingSettings, BusinessModules
from pro_universal_data.models import (MessagingServiceTypes, MessagingVendors, MessagingSendType,
                                       MessagingCategory, MessagingTemplates, MessagingFor, Tag)
from pro_universal_data.serializers import (MessagingServiceTypesSerializer, MessagingVendorsSerializer,
                                            MessagingSendTypeSerializer,
                                            MessagingCategorySerializer,
                                            MessagingTemplatesSerializer,
                                            MessagingForSerializer, TagSerializer,
                                            InitiatePaymentSerializer
                                            )

import requests
import json
from paytmchecksum import PaytmChecksum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Create your views here.
def send_webbased_whatsapp_message(mobile_no, otp_code):
    WA_WEB_SECRET_KEY = '5fcfa485601c097cbf2b9050c51cd2be63b64b1f'
    WA_WEB_ACCOUNT_ID = 2
    WA_WEB_URL = 'https://connect2chat.com/api/send/whatsapp'

    # print(f"Secret Key: {WA_WEB_SECRET_KEY}, Account ID: {WA_WEB_ACCOUNT_ID}, URL: {WA_WEB_URL}")

    chat = {
        'secret': WA_WEB_SECRET_KEY,
        'account': WA_WEB_ACCOUNT_ID,
        'recipient': f'+91{mobile_no}',
        'type': 'text',
        'message': f'Hello, your OTP for login is: {otp_code}'
    }
    try:
        r = requests.post(url=WA_WEB_URL, params=chat)
        # print(r.json())
        logger.info(f'WhatsApp message response: {r.text}')
        return r.json()
    except Exception as e:
        # print(e)
        logger.error(f'Error sending WhatsApp message: {e}')
        return None


# FAST2SMS_KEY='mZuxt2he7oG8MdbS9LEgYpFJkXayTcrKB153vOfNwWqRUHsil4S7jUzkcvI9quTQ6RYFo8t4KanxLr23'
FAST2SMS_KEY = os.environ.get('FAST2SMS_KEY')


def send_sms(numbers, variables_values):
    secret_key = FAST2SMS_KEY
    url = "https://www.fast2sms.com/dev/bulkV2"
    querystring = {
        "authorization": secret_key,
        "route": "dlt",
        "sender_id": "incras",
        "message": 163952,
        "variables_values": variables_values,
        "numbers": numbers,
    }

    headers = {
        'cache-control': "no-cache"
    }
    response = requests.request("GET", url, headers=headers, params=querystring)
    print(response.json())
    return response.json()


class MessagingServiceTypesViewSet(viewsets.ModelViewSet):
    queryset = MessagingServiceTypes.objects.all()
    serializer_class = MessagingServiceTypesSerializer


class MessagingVendorsViewSet(viewsets.ModelViewSet):
    queryset = MessagingVendors.objects.all()
    serializer_class = MessagingVendorsSerializer


class MessagingSendTypeViewSet(viewsets.ModelViewSet):
    queryset = MessagingSendType.objects.all()
    serializer_class = MessagingSendTypeSerializer


class MessagingCategoryViewSet(viewsets.ModelViewSet):
    queryset = MessagingCategory.objects.all()
    serializer_class = MessagingCategorySerializer


class MessagingTemplatesViewSet(viewsets.ModelViewSet):
    queryset = MessagingTemplates.objects.all()
    serializer_class = MessagingTemplatesSerializer


class MessagingForViewSet(viewsets.ModelViewSet):
    queryset = MessagingFor.objects.all()
    serializer_class = MessagingForSerializer


class TagsViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        templates = request.data.get('templates')
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        tag = Tag.objects.create(**validated_data)
        if templates:
            for template in templates:
                tag.templates.add(template)
                tag.save()
        serializer = TagSerializer(tag)
        return Response(serializer.data)

    def update(self, request, pk=None, *args, **kwargs):
        instance = self.get_object()
        instance.id = pk
        serializer = self.get_serializer(instance, data=request.data)

        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Update lab tests if provided
        templates = request.data.get('templates')
        if templates:
            for template in templates:
                instance.templates.add(template)
                instance.save()

        serializer = TagSerializer(instance)
        return Response(serializer.data)




# Program to access SendSMSDataViewSet and MessagingLogsViewset
def send_and_log_sms(search_id=None, numbers=None, sms_template=None, messaging_send_type=None, client=None,
                     from_date=None,
                     to_date=None):
    messages = BusinessMessageSettings.objects.get(client=client)
    global_messages = GlobalMessagingSettings.objects.filter(type__id=1).first()

    if messages.is_sms_active and global_messages.is_active:
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
        from pro_laboratory.views.client_based_settings_views import check_template_is_active_for_business

        is_template_active = check_template_is_active_for_business(template=sms_template, client=client)

        if is_template_active:
            from pro_laboratory.views.messaging_views import SendAndSaveSMSDataViewset
            send_sms_data = SendAndSaveSMSDataViewset()
            response = send_sms_data.create(search_id=search_id, numbers=numbers, sms_template=sms_template,
                                            messaging_send_type=messaging_send_type, client=client, from_date=from_date,
                                            to_date=to_date)

            # credits.total_messages += 1
            # credits.save()

            if response.status_code == 200:
                credits.total_messages += 1
                credits.save()

                return Response({"Status": "Message sent successfully!", "response_code": 200})
            else:
                return Response({"Error": "Message sending failed", "response_code": 400},
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(
                {"Error": "Template is Inactive for the business, Pls make it Active!", "response_code": 400},
                status=status.HTTP_400_BAD_REQUEST)

    else:
        if not global_messages.is_active:
            return Response({"Error": f"{global_messages.remarks}", "response_code": 400},
                            status=status.HTTP_400_BAD_REQUEST)

        else:
            return Response({"Error": "Messaging service is inactive for this Business", "response_code": 400},
                            status=status.HTTP_400_BAD_REQUEST)


META_WHATSAPP_KEY = os.environ.get('META_WHATSAPP_KEY')
META_WHATSAPP_PHONE_ID = os.environ.get('META_WHATSAPP_PHONE_ID')
META_WHATSAPP_BUSINESS_ID = os.environ.get('META_WHATSAPP_BUSINESS_ID')


# Program to access SendSMSDataViewSet and MessagingLogsViewset
def send_and_log_whatsapp_sms(search_id=None, numbers=None, mwa_template=None, messaging_send_type=None, client=None,
                              test_id=None, test_ids=None, receipt=None, send_reports_type=None, letterhead=None, file_location=None):
    
    messages = BusinessMessageSettings.objects.get(client=client)
    global_messages = GlobalMessagingSettings.objects.filter(type__id=2).first()
    send_reports_type = send_reports_type or messages.send_reports_by.name or 'Automatic'



    if messages.is_whatsapp_active and global_messages.is_active:
        from pro_laboratory.views.client_based_settings_views import check_template_is_active_for_business
        is_template_active = check_template_is_active_for_business(template=mwa_template, client=client)

        if not is_template_active:
            return Response(
                {"Error": "Template is Inactive for the business, Pls make it Active!", "response_code": 400},
                status=status.HTTP_400_BAD_REQUEST)

        credits = BusinessMessagesCredits.objects.filter(messaging_service_types__name='WhatsApp').last()

        if send_reports_type == 'Manual':
            pass
        else:
            if not credits:
                return Response(
                    {"Error": "You don't have credits to send messages!Pls contact Admin!", "response_code": 400},
                    status=status.HTTP_400_BAD_REQUEST)

            balance = credits.new_credits - credits.total_messages

            if balance < 1:
                return Response(
                    {"Error": "You don't have credits to send messages!Pls contact Admin!", "response_code": 400},
                    status=status.HTTP_400_BAD_REQUEST)
            # credits.total_messages += 1
            # credits.save()

        from pro_laboratory.views.messaging_views import SendAndSaveWhatsAppSMSViewset

        if send_reports_type == 'Automatic':
            send_sms = SendPDFWhatsAppSMSViewSet()
            if test_ids is not None:
                mwa_template = MessagingTemplates.objects.get(pk=16)
            if receipt is not None:
                mwa_template = MessagingTemplates.objects.get(pk=17)

            response = send_sms.create(search_id=search_id, numbers=numbers, mwa_template=mwa_template,
                                       messaging_send_type=messaging_send_type, client=client, test_id=test_id,
                                       test_ids=test_ids, receipt=receipt, send_reports_type=send_reports_type,
                                       letterhead=letterhead, file_location=file_location)

        else:
            send_sms = SendAndSaveWhatsAppSMSViewset()
            response = send_sms.create(search_id=search_id, numbers=numbers, mwa_template=mwa_template,
                                       messaging_send_type=messaging_send_type, client=client, test_id=test_id,
                                       test_ids=test_ids, receipt=receipt, send_reports_type=send_reports_type,
                                       letterhead=letterhead)

        # send_sms = SendAndSaveWhatsAppSMSViewset()
        # response = send_sms.create(search_id=search_id, numbers=numbers, mwa_template=mwa_template,
        #                            messaging_send_type=messaging_send_type, client=client, test_id=test_id,
        #                            test_ids=test_ids, receipt=receipt, send_reports_type=send_reports_type, letterhead=letterhead)

        if response.status_code == 200:
            if send_reports_type == 'Manual':
                pass
            else:
                credits.total_messages += 1
                credits.save()

            return Response({"Status": "Message sent successfully!",
                             "content": response.data.get('content'),
                             "send_reports_type":send_reports_type, "response_code": 200})
        else:
            return Response({"Error": "Message sending failed", "response_code": 400},
                            status=status.HTTP_400_BAD_REQUEST)


    else:
        if not global_messages.is_active:
            return Response({"Error": f"{global_messages.remarks}", "response_code": 400},
                            status=status.HTTP_400_BAD_REQUEST)

        else:
            return Response({"Error": "Messaging service is inactive for this Business", "response_code": 400},
                            status=status.HTTP_400_BAD_REQUEST)


#Paytm code
#production
M_ID = os.environ.get('PAYTM_MID')
M_KEY = os.environ.get('PAYTM_KEY_SECRET')


@csrf_exempt
@api_view(['POST'])
def payment_callback(request):
    if request.method == 'POST':
        form = request.POST

        orderId = request.POST.get('ORDERID')
        # checksum = request.POST.get('CHECKSUMHASH')

        # initialize a dictionary
        paytmParams = dict()

        # body parameters
        paytmParams["body"] = {
            "mid": M_ID,
            "orderId": str(orderId)
        }

        # Generate checksum by parameters we have in body
        # Find your Merchant Key in your Paytm Dashboard at https://dashboard.paytm.com/next/apikeys
        checksum = PaytmChecksum.generateSignature(json.dumps(paytmParams["body"]), M_KEY)

        # head parameters
        paytmParams["head"] = {
            "signature": checksum
        }

        # prepare JSON string for request
        post_data = json.dumps(paytmParams)

        # # for Staging
        # url = "https://securegw-stage.paytm.in/v3/order/status"

        # for Production
        url = "https://securegw.paytm.in/v3/order/status"

        isVerifySignature = PaytmChecksum.verifySignature(json.dumps(paytmParams["body"]), M_KEY, checksum)

        try:
            if isVerifySignature:
                response = requests.post(url, data=post_data, headers={"Content-type": "application/json"}).json()
                return Response({'Status': response, 'callback_data': form})
        except Exception as error:
            return Response({'Status': error})


class InitiatePaymentViewset(viewsets.ModelViewSet):
    serializer_class = InitiatePaymentSerializer

    def get_queryset(self):
        return []

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer_data = serializer.validated_data
        # user_id = serializer_data.get('user_id')
        amount = serializer_data['amount']
        # orderId = serializer_data.get('orderId')

        user_id = 'USER' + str(datetime.now().strftime('%d%m%y%H%M%S'))

        orderId = 'OID' + str(datetime.now().strftime('%d%m%y%H%M%S'))

        paytmParams = dict()

        paytmParams["body"] = {
            "requestType": "Payment",
            "mid": M_ID,
            # "websiteName": "WEBSTAGING", #for staging
            "websiteName": "DEFAULT",  #for production
            "orderId": str(orderId),
            # "callbackUrl": "http://localhost:8000//tpa/payment_callback/",
            "callbackUrl": "https://labspark.azurewebsites.net/tpa/payment_callback/",
            "txnAmount": {
                "value": str(amount),
                "currency": "INR",
            },
            "userInfo": {
                "custId": str(user_id),
            },
        }

        checksum = PaytmChecksum.generateSignature(json.dumps(paytmParams["body"]), M_KEY)
        verifyChecksum = PaytmChecksum.verifySignature(json.dumps(paytmParams["body"]), M_KEY, checksum)

        paytmParams["head"] = {
            "signature": checksum,
        }

        post_data = json.dumps(paytmParams)
        print(post_data)

        # # for Staging
        # url = f"https://securegw-stage.paytm.in/theia/api//v1/initiateTransaction?mid={M_ID}&orderId={orderId}"
        # print(url)
        #
        # for Production
        url = f"https://securegw.paytm.in/theia/api/v1/initiateTransaction?mid={M_ID}&orderId={orderId}"

        try:
            response = requests.post(url, data=post_data, headers={"Content-type": "application/json"}).json()
            # return Response({'status':response})

            context = {
                # 'HOST': 'https://securegw-stage.paytm.in',  # For staging
                'HOST': 'https://securegw.paytm.in',  # For production
                'MID': M_ID,
                'txnToken': response['body']['txnToken'],
                'orderId': paytmParams['body']['orderId'],
                'amount': paytmParams['body']['txnAmount']['value']
            }

            return render(request, 'payment_gateway.html', context)

        except Exception as error:
            return Response({'status': error})


class PrintTemplateTypeViewset(viewsets.ModelViewSet):
    queryset = PrintTemplateType.objects.filter(is_active=True)
    serializer_class = PrintTemplateTypeSerializer


class TemplateTagsListAPIView(generics.ListAPIView):
    serializer_class = TemplateTagsGetSerializer

    def get_queryset(self):
        template = self.request.query_params.get('template')
        queryset = Tag.objects.all()
        if template is not None:
            return Tag.objects.filter(templates__id=template)
        else:
            return Tag.objects.none()


class DashBoardOptionsViewset(viewsets.ModelViewSet):
    queryset = DashBoardOptions.objects.all()
    serializer_class = DashBoardOptionSerializer


class DoctorSharedReportViewset(viewsets.ModelViewSet):
    queryset = DoctorSharedReport.objects.all()
    serializer_class = DoctorSharedReportSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = DoctorSharedReportFilter


class DepartmentFlowTypeViewset(viewsets.ModelViewSet):
    queryset = DepartmentFlowType.objects.all()
    serializer_class = DepartmentFlowTypeSerializer


class UserPermissionsViewset(viewsets.ModelViewSet):
    queryset = UserPermissions.objects.all()
    serializer_class = UserPermissionsSerializer


class ULabFontsViewset(viewsets.ModelViewSet):
    queryset = ULabFonts.objects.all()
    serializer_class = ULabFontsSerializer


class LabEmploymentTypeViewSet(viewsets.ModelViewSet):
    queryset = LabEmploymentType.objects.all()
    serializer_class = LabEmploymentTypeSerializer


class MarketingTargetTypesViewSet(viewsets.ModelViewSet):
    queryset = MarketingTargetTypes.objects.all()
    serializer_class = MarketingTargetTypesSerializer


class MarketingTargetDurationsViewSet(viewsets.ModelViewSet):
    queryset = MarketingTargetDurations.objects.all()
    serializer_class = MarketingTargetDurationsSerializer


class LabStaffAttendanceStatusViewSet(viewsets.ModelViewSet):
    queryset = LabStaffAttendanceStatus.objects.all()
    serializer_class = LabStaffAttendanceStatusSerializer


class MarketingPaymentTypeViewSet(viewsets.ModelViewSet):
    queryset = MarketingPaymentType.objects.all()
    serializer_class = MarketingPaymentTypeSerializer


class SalaryPaymentModesViewSet(viewsets.ModelViewSet):
    queryset = SalaryPaymentModes.objects.all()
    serializer_class = SalaryPaymentModesSerializer


class LeaveStatusViewSet(viewsets.ModelViewSet):
    queryset = LeaveStatus.objects.all()
    serializer_class = LeaveStatusSerializer


class LeaveTypesViewSet(viewsets.ModelViewSet):
    queryset = LeaveTypes.objects.all()
    serializer_class = LeaveTypesSerializer

class TimeCategoryViewSet(viewsets.ModelViewSet):
    queryset = TimeCategory.objects.all()
    serializer_class = TimeCategorySerializer

class DoctorSalaryPaymentTypesViewSet(viewsets.ModelViewSet):
    queryset = DoctorSalaryPaymentTypes.objects.all()
    serializer_class = DoctorSalaryPaymentTypesSerializer


class DoctorTransactionTypesViewSet(viewsets.ModelViewSet):
    queryset = DoctorTransactionTypes.objects.all()
    serializer_class = DoctorTransactionTypesSerializer


class TaxTypeViewSet(viewsets.ModelViewSet):
    queryset = TaxType.objects.all()
    serializer_class = TaxTypeSerializer


class SupplierTypeViewSet(viewsets.ModelViewSet):
    queryset = SupplierType.objects.all()
    serializer_class = SupplierTypeSerializer

class PatientTypeViewSet(viewsets.ModelViewSet):
    queryset = PatientType.objects.all()
    serializer_class = PatientTypeSerializer