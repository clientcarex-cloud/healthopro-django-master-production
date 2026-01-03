import os
from datetime import datetime
import re
from http.client import HTTPResponse

from django.core.cache import cache
from django.db import connection
from django.db.models import Count
from django.forms import model_to_dict
from django.http import HttpResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from django_tenants.utils import schema_context
from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from copy_biz_data import copy_biz_data
from healtho_pro_user.models.business_models import BusinessProfiles, GlobalBusinessSettings
from healtho_pro_user.models.users_models import Client
from healtho_pro_user.views.business_views import get_business_from_client
from pro_laboratory.filters import WhatsappMessagingStatisticsFilter, MessagingStatisticsFilter
from pro_laboratory.models.bulk_messaging_models import BulkMessagingTemplates
from pro_laboratory.models.client_based_settings_models import LetterHeadSettings, BusinessDataStatus, \
    CopiedLabDepartmentsData, BusinessDiscountSettings, BusinessPaidAmountSettings, BusinessPNDTDetails, \
    PrintReportSettings, PrintDueReports, PNDTRegistrationNumber, BusinessMessageSettings, \
    BusinessReferralDoctorSettings, PrintTestReportSettings, LabStaffPrintSettings,  \
    ClientWiseMessagingTemplates, OtherBusinessSettings, BusinessEmailDetails, ReportFontSizes, PharmacyPricingConfig
from pro_laboratory.models.global_models import LabDepartments, LabStaff, LabGlobalTests, LabGlobalPackages
from pro_laboratory.models.messaging_models import MessagingLogs, WhatsAppMessagingLogs
from pro_laboratory.models.universal_models import PrintTemplate, PrintDataTemplate
from pro_laboratory.serializers.client_based_settings_serializers import LetterHeadSettingsSerializer, \
    CopyBasicBusinessDataSerializer, BusinessDataStatusSerializer, CopiedLabDepartmentsDataSerializer, \
    BusinessDiscountSettingsSerializer, BusinessPaidAmountSettingsSerializer, BusinessPNDTDetailsSerializer, \
    PrintReportSettingsSerializer, PrintDueReportsSerializer, PNDTRegistrationNumberSerializer, \
    BusinessMessageSettingsSerializer, BusinessReferralDoctorSettingsSerializer, PrintTestReportSettingsSerializer, \
    LabStaffPrintSettingsSerializer, ClientWiseMessagingTemplatesSerializer, \
    OtherBusinessSettingsSerializer, BusinessEmailDetailsSerializer, ReportFontSizesSerializer, \
    GenerateQuotationSerializer, PharmacyPricingConfigSerializer
from pro_laboratory.serializers.global_serializers import LabDepartmentsSerializer
from pro_pharmacy.models import PharmaItems
from pro_universal_data.models import MessagingTemplates, DepartmentFlowType, ULabFonts, PrintTemplateType, Tag


class LetterHeadSettingsViewSet(viewsets.ModelViewSet):
    serializer_class = LetterHeadSettingsSerializer

    def get_queryset(self):
        client_id = self.request.query_params.get('client_id')
        if client_id is None:
            return LetterHeadSettings.objects.none()
        try:
            cache_key = f'letterhead_settings_{client_id}'
            cache_data = cache.get(cache_key)
            if cache_data:
                return cache_data
            queryset = LetterHeadSettings.objects.filter(client__id=client_id)
            cache.set(cache_key, queryset)
            return queryset
        except Exception as e:
            queryset = LetterHeadSettings.objects.filter(client__id=client_id)
            return queryset

    def perform_create(self, serializer):
        super().perform_create(serializer)
        self.invalidate_cache()

    def perform_update(self, serializer):
        super().perform_update(serializer)
        self.invalidate_cache()

    def perform_destroy(self, instance):
        super().perform_destroy(instance)
        self.invalidate_cache()

    def invalidate_cache(self):
        client_id = self.request.query_params.get('client_id')
        if client_id:
            cache_key = f'letterhead_settings_{client_id}'
            try:
                # Try to delete and refresh the cache
                cache.delete(cache_key)
                print(f"Deleted cache key: {cache_key}")
                queryset = LetterHeadSettings.objects.filter(client__id=client_id)
                cache.set(cache_key, queryset)
                print(f"Refreshed cache with new data for key: {cache_key}")
            except Exception as e:
                # Log the error if cache operations fail
                print(f"Cache invalidation failed: {e}")


class PrintTestReportSettingsViewSet(viewsets.ModelViewSet):
    queryset = PrintTestReportSettings.objects.all()
    serializer_class = PrintTestReportSettingsSerializer


class PrintReportSettingsViewSet(viewsets.ModelViewSet):
    queryset = PrintReportSettings.objects.all()
    serializer_class = PrintReportSettingsSerializer

old_schema = "LabsparkDiagnostics"



def get_default_letterhead_settings():
    try:
        with schema_context(old_schema):
            letterhead_settings = LetterHeadSettings.objects.first()

            print_report_settings = PrintReportSettings.objects.first()

            return {"letterhead_settings": model_to_dict(letterhead_settings),
                    "print_report_settings": model_to_dict(print_report_settings)}

    except Exception as error:
        print(error)
        return None


class CopiedLabDepartmentsDataView(viewsets.ModelViewSet):
    queryset = CopiedLabDepartmentsData.objects.all()
    serializer_class = CopiedLabDepartmentsDataSerializer

    def get_queryset(self):
        client_id = self.request.query_params.get('client_id')
        b_id = self.request.query_params.get('b_id')
        if client_id is not None:
            return CopiedLabDepartmentsData.objects.filter(client__id=client_id)
        elif b_id is not None:
            return CopiedLabDepartmentsData.objects.filter(b_id__id=b_id)
        else:
            return CopiedLabDepartmentsData.objects.none()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer_data = serializer.validated_data
        client = serializer_data.get('client')
        b_id = serializer_data.get('b_id')
        departments_list = serializer_data.get('departments_list')

        try:
            copy_biz_data(old_schema, client.schema_name, departments_list)
            business_data, created = CopiedLabDepartmentsData.objects.get_or_create(client=client, b_id=b_id)
            if departments_list:
                for department in departments_list:
                    department, created = LabDepartments.objects.get_or_create(name=department)
                    business_data.departments.add(department)

            serializer = CopiedLabDepartmentsDataSerializer(business_data)
            return Response(serializer.data)
        except Exception as error:
            return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)


    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer_data = serializer.validated_data
        client = serializer_data.get('client')
        b_id = serializer_data.get('b_id')
        departments_list = serializer_data.get('departments_list')

        try:
            copy_biz_data(old_schema, client.schema_name, departments_list)
            business_data, created = CopiedLabDepartmentsData.objects.get_or_create(client=client, b_id=b_id)
            if departments_list:
                for department in departments_list:
                    department, created = LabDepartments.objects.get_or_create(name=department)
                    business_data.departments.add(department)

            serializer = CopiedLabDepartmentsDataSerializer(business_data)
            return Response(serializer.data)
        except Exception as error:
            return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)


class LabDepartmentsListToCopyView(generics.ListAPIView):
    serializer_class = LabDepartmentsSerializer

    def get_queryset(self):
        client = Client.objects.get(schema_name=f"{old_schema}")
        connection.set_schema(client.schema_name)
        queryset = LabDepartments.objects.filter(is_active=True).order_by('id')
        return queryset


class BusinessDataStatusViewSet(viewsets.ModelViewSet):
    serializer_class = BusinessDataStatusSerializer

    def get_queryset(self):
        client_id = self.request.query_params.get('client_id')
        b_id = self.request.query_params.get('b_id')
        if client_id is not None:
            return BusinessDataStatus.objects.filter(client__id=client_id)

        elif b_id is not None:
            return BusinessDataStatus.objects.filter(b_id__id=b_id)

        else:
            return BusinessDataStatus.objects.none()


class BusinessDiscountSettingsViewset(viewsets.ModelViewSet):
    queryset = BusinessDiscountSettings.objects.all()
    serializer_class = BusinessDiscountSettingsSerializer


class BusinessPaidAmountSettingsViewset(viewsets.ModelViewSet):
    queryset = BusinessPaidAmountSettings.objects.all()
    serializer_class = BusinessPaidAmountSettingsSerializer


class OtherBusinessSettingsSerializerViewset(viewsets.ModelViewSet):
    queryset = OtherBusinessSettings.objects.all()
    serializer_class = OtherBusinessSettingsSerializer

    def get_queryset(self):
        queryset = OtherBusinessSettings.objects.all()

        if not queryset:
            obj = OtherBusinessSettings.objects.create(manual_date=False)
        return queryset


class BusinessPNDTDetailsViewset(viewsets.ModelViewSet):
    queryset = BusinessPNDTDetails.objects.all()
    serializer_class = BusinessPNDTDetailsSerializer


class PrintDueReportsViewset(viewsets.ModelViewSet):
    queryset = PrintDueReports.objects.all()
    serializer_class = PrintDueReportsSerializer


class PNDTRegistrationNumberViewset(viewsets.ModelViewSet):
    queryset = PNDTRegistrationNumber.objects.all()
    serializer_class = PNDTRegistrationNumberSerializer


class BusinessMessageSettingsViewset(viewsets.ModelViewSet):
    serializer_class = BusinessMessageSettingsSerializer

    def get_queryset(self):
        client = self.request.query_params.get('client')
        client = Client.objects.get(pk=client)
        if client is not None:
            data, created = BusinessMessageSettings.objects.get_or_create(client=client)
        queryset = BusinessMessageSettings.objects.filter(client=client)
        return queryset

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            partial = kwargs.pop('partial', False)
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            serializer_data = serializer.validated_data

            is_sms_active = serializer_data.get('is_sms_active')
            is_whatsapp_active = serializer_data.get('is_whatsapp_active')

            business = get_business_from_client(instance.client)

            global_business_settings = GlobalBusinessSettings.objects.get(business=business)

            if is_sms_active:
                if not global_business_settings.is_sms_active:
                    serializer_data['is_sms_active'] = False

            if is_whatsapp_active:
                if not global_business_settings.is_whatsapp_active:
                    serializer_data['is_whatsapp_active'] = False

            serializer.save()

            return Response(serializer.data)

        except Exception as error:
            return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)


class BusinessReferralDoctorSettingsViewset(viewsets.ModelViewSet):
    serializer_class = BusinessReferralDoctorSettingsSerializer

    def get_queryset(self):
        client = self.request.query_params.get('client')
        client = Client.objects.get(pk=client)
        if client is not None:
            data, created = BusinessReferralDoctorSettings.objects.get_or_create(client=client)
        queryset = BusinessReferralDoctorSettings.objects.filter(client=client)
        return queryset


class BusinessMessagingStatisticsView(generics.ListAPIView):
    queryset = MessagingLogs.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_class = MessagingStatisticsFilter

    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        client = self.request.query_params.get('client', None)

        if not client:
            return Response({"Error": "No business is selected!"})

        # Aggregate message counts by sms_template
        template_counts = queryset.values('sms__sms_template__templateName').annotate(
            message_count=Count('id')
        ).order_by('sms__sms_template__templateName')

        # Create a dictionary from the aggregated counts for fast lookup
        template_count_dict = {item['sms__sms_template__templateName']: item['message_count'] for item in
                               template_counts}

        # Get all templates and ensure each has a count
        all_templates = MessagingTemplates.objects.filter(messaging_service_types__name='SMS')

        # Prepare the response data
        response_data = []
        total_messages_count = 0

        for template in all_templates:
            template_name = template.templateName
            message_count = template_count_dict.get(template_name, 0)
            total_messages_count += message_count
            response_data.append({
                "id": template.id,
                "template_name": template_name,
                "messages_count": message_count,
                "template_content": template.templateContent
            })

        return Response({"total_messages_count": total_messages_count, "template_wise_count": response_data})


class BusinessWhatsappMessagingStatisticsView(generics.ListAPIView):
    queryset = WhatsAppMessagingLogs.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_class = WhatsappMessagingStatisticsFilter

    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        client = self.request.query_params.get('client', None)

        if not client:
            return Response({"Error": "No business is selected!"})

        # Aggregate message counts by sms_template
        template_counts = queryset.values('sms__mwa_template__templateName').annotate(
            message_count=Count('id')
        ).order_by('sms__mwa_template__templateName')

        # Create a dictionary from the aggregated counts for fast lookup
        template_count_dict = {item['sms__mwa_template__templateName']: item['message_count'] for item in
                               template_counts}

        # Get all templates and ensure each has a count
        all_templates = MessagingTemplates.objects.filter(messaging_service_types__name='WhatsApp')

        # Prepare the response data
        response_data = []
        total_messages_count = 0

        for template in all_templates:
            template_name = template.templateName
            message_count = template_count_dict.get(template_name, 0)
            total_messages_count += message_count
            response_data.append({
                "id": template.id,
                "template_name": template_name,
                "messages_count": message_count,
                "template_content": template.templateContent
            })

        return Response({"total_messages_count": total_messages_count, "template_wise_count": response_data})


class LabStaffPrintSettingsViewSet(viewsets.ModelViewSet):
    queryset = LabStaffPrintSettings.objects.all()
    serializer_class = LabStaffPrintSettingsSerializer

    def get_queryset(self):
        lab_staff_id = self.request.query_params.get('lab_staff_id', None)

        try:
            if lab_staff_id:
                lab_staff = LabStaff.objects.get(pk=lab_staff_id)
                settings, created = LabStaffPrintSettings.objects.get_or_create(lab_staff=lab_staff)
                queryset = LabStaffPrintSettings.objects.filter(lab_staff=lab_staff)
            else:
                queryset = LabStaffPrintSettings.objects.none()

            return queryset
        except Exception as error:
            return LabStaffPrintSettings.objects.none()


class ClientWiseMessagingTemplatesViewSet(viewsets.ModelViewSet):
    queryset = ClientWiseMessagingTemplates.objects.all()
    serializer_class = ClientWiseMessagingTemplatesSerializer

    def get_queryset(self):
        try:
            queryset = ClientWiseMessagingTemplates.objects.filter(client=self.request.client)

            if not queryset.exists():
                obj = ClientWiseMessagingTemplates.objects.create(client=self.request.client)

                templates = MessagingTemplates.objects.all()
                bulk_templates = BulkMessagingTemplates.objects.all()

                obj.templates.set(templates)
                obj.bulk_templates.set(bulk_templates)

                obj.save()

            return queryset

        except Exception as error:
            return ClientWiseMessagingTemplates.objects.none()


def check_template_is_active_for_business(template=None, client=None, bulk_templates=None):
    messages_obj = ClientWiseMessagingTemplates.objects.filter(client=client).first()

    if messages_obj is None:
        messages_obj = ClientWiseMessagingTemplates.objects.create(client=client)

        templates = MessagingTemplates.objects.all()
        messages_obj.templates.set(templates)
        messages_obj.save()
        bulk_templates = BulkMessagingTemplates.objects.all()
        messages_obj.bulk_templates.set(bulk_templates)
        messages_obj.save()

    messaging_templates = messages_obj.templates.all()
    bulk_messaging_templates = messages_obj.bulk_templates.all()

    if bulk_templates is None:
        if template in messaging_templates:
            return True
        else:
            return False

    else:
        if template in bulk_messaging_templates:
            return True
        else:
            return False


class BusinessEmailDetailsViewSet(viewsets.ModelViewSet):
    queryset = BusinessEmailDetails.objects.all()
    serializer_class = BusinessEmailDetailsSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if not queryset.exists():
            new_business_email_detail = BusinessEmailDetails()
            new_business_email_detail.save()
            queryset = BusinessEmailDetails.objects.filter(
                id=new_business_email_detail.id)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CurrentTimingsAPIView(APIView):
    def get(self, request):
        current_date = timezone.now()
        formatted_date = current_date.strftime("%d-%m-%Y")
        formatted_time = current_date.strftime('%I:%M %p')
        response ={"Date": formatted_date, "Time": formatted_time, "TimeStamp": current_date}
        return Response(response)

class ReportFontSizesViewSet(viewsets.ModelViewSet):
    queryset = ReportFontSizes.objects.all()
    serializer_class = ReportFontSizesSerializer

    def get_queryset(self):
        # Check if any objects exist
        if not ReportFontSizes.objects.exists():
            default_data = {
                "dept_name_size": 16.00,
                "test_name_size": 14.00,
                "report_head_size": 14.00,
                "parameter_size": 12.00,
                "parameter_weight": 400.00,
                "result_size": 12.00,
                "unit_size": 12.00,
                "ref_range_size": 12.00,
                "method_size": 10.00,
                "method_weight": 300.00,
                "group_name_size": 14.00,
                "group_name_weight": 600.00,
                "test_display_name": "Test Name",
                "result_display_name": "Result",
                "unit_display_name": "Unit",
                "ref_ranges_display_name": "Bio.Ref.Range",
                "method_display_name": "METHOD:",
                "method_is_italic": True
            }

            ReportFontSizes.objects.create(**default_data)

        return ReportFontSizes.objects.all()





class GenerateQuotationViewSet(viewsets.ModelViewSet):
    serializer_class = GenerateQuotationSerializer

    def get_queryset(self):
        return []

    def create(self, request=None, test_ids=None,client_id=None,package_ids=None,printed_by=None, *args, **kwargs):
        if request:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer_data = serializer.validated_data
            test_ids = serializer_data.get('test_ids')
            package_ids = serializer_data.get('package_ids')
            printed_by = serializer_data.get('printed_by')
            client_id = request.client.id
            print(client_id, 'id')
            print(test_ids, package_ids, client_id)
        else:
            print(test_ids, package_ids)

        try:
            tests = None
            packages = None
            if test_ids:
                tests = LabGlobalTests.objects.filter(id__in=test_ids)
            if package_ids:
                packages = LabGlobalPackages.objects.filter(id__in=package_ids)
            client = Client.objects.get(pk=client_id)
            lab_staff = LabStaff.objects.get(pk=printed_by)
            bProfile = BusinessProfiles.objects.filter(organization_name=client.name).first()
            template_type = PrintTemplateType.objects.get(name='Quotation')
            print_template = PrintTemplate.objects.get(print_template_type=template_type, is_default=True)
            template = PrintDataTemplate.objects.get(print_template=print_template)

            report_printed_on = datetime.now().strftime('%d-%m-%y %I:%M %p')

            details = {
                "tests": tests,
                "packages":packages,
                'bProfile': bProfile,
                "lab_staff": lab_staff,
                "report_printed_on": report_printed_on
            }
        except Exception as error:
            print(error)
            return Response(f"Error fetching details: {error}", status=400)

        search_pattern = r"\{(.*?)\}"
        expression_pattern = r"\[\[(.*?)\]\]"
        tag_totals = {}

        def accumulate_tag_totals(tag_name, value):
            if tag_name in tag_totals:
                tag_totals[tag_name] += value
            else:
                tag_totals[tag_name] = value

        # Function to replace tags found by regex search
        def replace_tag(match):
            tag_name = match.group(1)  # Capture the content without braces

            try:
                # Fetch the tag by its name
                tag = Tag.objects.get(tag_name='{' + tag_name + '}')
                # Check if the tag requires fetching a collection of items
                if tag.is_collection:
                    if tag_name == 'QuotationTestSNo':
                        tests_details = details['tests']
                        packages = details['packages']
                        test_snos = []
                        test_count = 0
                        if packages:
                            for package in packages:
                                test_count += 1
                                test_snos.append(test_count)
                                tests = package.lab_tests.all()
                                for test in tests:
                                    test_snos.append(f"<br>")
                        if tests_details:
                            for obj in tests_details:
                                test_count += 1
                                test_snos.append(test_count)
                            return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in test_snos)

                    if tag_name == 'QuotationTotalTests':
                        packages_details = details['packages']
                        tests_details = details['tests']
                        test_names_data = []

                        if packages_details:
                            for package in packages_details:
                                test_names_data.append(f"<strong>{package.name}</strong>")
                                tests = package.lab_tests.all()
                                if tests.exists():
                                    for test in tests:
                                        test_names_data.append(f"{test.name}")
                                test_names_data.append("<p style='margin: 10px 0;'></p>")

                        if tests_details:
                            for test in tests_details:
                                test_names_data.append(f"{test.name}")
                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in test_names_data)

                    if tag_name == 'QuotationTestsPrices':
                        packages_details = details['packages']
                        tests_details = details['tests']
                        test_prices_data = []

                        if packages_details:
                            for package in packages_details:
                                test_prices_data.append(f"<strong>{package.offer_price}</strong>")
                                tests = package.lab_tests.all()
                                for test in tests:
                                    test_prices_data.append(f"<br>")
                        if tests_details:
                            for test in tests_details:
                                test_prices_data.append(f"{test.price}")

                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in test_prices_data)

                    if tag_name == 'QuotationTotalTestsPrice':
                        packages_details = details['packages']
                        tests_details = details['tests']
                        total_test_prices = 0

                        if packages_details:
                            for package in packages_details:
                                total_test_prices += package.offer_price
                        if tests_details:
                            for test in tests_details:
                                total_test_prices += test.price
                        return "".join(f'<p style="margin: 3px 5px;">{total_test_prices}</p>')
                else:
                    if tag.tag_formula:
                        try:
                            tag_value = str(eval(tag.tag_formula, {'details': details}))
                            return tag_value
                        except Exception as eval_error:
                            print(f"{tag_name} - Error in formula evaluation: {eval_error}")
                            return " "  # If null
                    else:
                        # If no formula, return a placeholder or a default value
                        return f"No formula for {tag_name}"

            except Tag.DoesNotExist:
                return f"{tag_name} not found!"

        def evaluate_expression(match):
            expression = match.group(1)  # Capture the content without double brackets
            try:
                # Ensure you sanitize or validate the expression if using eval() directly poses a security risk
                result = str(eval(expression, {'__builtins__': None}, {'details': details}))
                return result
            except Exception as eval_error:
                print(f"Error in expression evaluation: {eval_error}")
                return "[Error]"

        html_content = template.data
        template_content = html_content
        intermediate_content = re.sub(search_pattern, replace_tag, template_content)

        modified_content = re.sub(expression_pattern, evaluate_expression, intermediate_content)

        def replace_total(match):
            tag_name = match.group(1)  # Extract the tag name
            total_value = tag_totals.get(tag_name, 0)  # Get the total value from tag_totals
            return str(total_value)  # Return the total value as a string
        final_content = re.sub(expression_pattern, replace_total, modified_content)

        return Response({'html_content': final_content})
        # return HttpResponse(final_content)


class PharmacyPricingConfigViewSet(viewsets.ModelViewSet):
    queryset = PharmacyPricingConfig.objects.all()
    serializer_class = PharmacyPricingConfigSerializer

    def get_queryset(self):
        queryset = PharmacyPricingConfig.objects.all()
        if not queryset:
            queryset = PharmacyPricingConfig.objects.create(tax_percentage=0, discount_percentage=0)
        return queryset

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        discount_percentage = serializer.validated_data.get('discount_percentage', instance.discount_percentage)
        tax_percentage = serializer.validated_data.get('tax_percentage', instance.tax_percentage)
        PharmaItems.objects.update(discount=discount_percentage, tax=tax_percentage)

        return Response(serializer.data, status=status.HTTP_200_OK)
