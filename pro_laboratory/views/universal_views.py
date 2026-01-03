import base64
from datetime import datetime, timedelta, time
import re
from decimal import Decimal, ROUND_HALF_UP
import barcode
import qrcode
from dateutil.relativedelta import relativedelta
from django.db import connection
from django.db.models import Q, Case, When, Count, Sum
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from django_tenants.utils import schema_context
from num2words import num2words
from pypdf import PdfWriter, PdfReader
from rest_framework import status
from rest_framework import viewsets, generics, permissions
from weasyprint import HTML

from accounts.models import LabExpenses
from healtho_pro_user.models.business_models import BContacts, BusinessProfiles, BusinessAddresses
from healtho_pro_user.models.users_models import HealthOProUser, Client, Domain
from interoperability.models import LabTpaSecretKeys
from pro_laboratory.filters import TpaUltraSoundFilter, ActivityLogsFilter
from pro_laboratory.models.client_based_settings_models import LetterHeadSettings, BusinessReferralDoctorSettings, \
    PrintTestReportSettings, PrintReportSettings, BusinessEmailDetails, ReportFontSizes
from pro_laboratory.models.doctors_models import ReferralAmountForDoctor, DefaultsForDepartments
from pro_laboratory.models.global_models import LabStaff, LabStaffDefaultBranch, LabGlobalTests, LabGlobalPackages
from pro_laboratory.models.labtechnicians_models import (LabPatientFixedReportTemplate, LabTechnicians, \
                                                         LabPatientWordReportTemplate, LabTechnicianRemarks)
from pro_laboratory.models.patient_appointment_models import AppointmentDetails
from pro_laboratory.models.patient_models import Patient, LabPatientInvoice, LabPatientTests, LabPatientReceipts, \
    LabPatientRefund, LabPatientPayments, LabPatientPackages
from pro_laboratory.models.phlebotomists_models import LabPhlebotomist
from pro_laboratory.models.privilege_card_models import PrivilegeCardMemberships, PrivilegeCardsLabDepartmentsBenefits, PrivilegeCardsLabTestBenefits, PrivilegeCardsMembershipApplicableBenefits
from pro_laboratory.models.sourcing_lab_models import SourcingLabLetterHeadSettings
from pro_laboratory.models.universal_models import PrintTemplate, PrintDataTemplate, ChangesInModels
from pro_laboratory.models.universal_models import TpaUltrasoundConfig, TpaUltrasound, TpaUltrasoundImages, \
    ActivityLogs
from pro_laboratory.serializers.client_based_settings_serializers import LetterHeadSettingsSerializer
from pro_laboratory.serializers.global_serializers import LabGlobalTestsSerializer, LabGlobalPackagesGetSerializer
from pro_laboratory.serializers.sourcing_lab_serializers import SourcingLabLetterHeadSettingsSerializer
from pro_laboratory.serializers.universal_serializers import GenerateReceiptSerializer, GenerateTestReportSerializer, GeneratePatientReceiptSerializer, \
    GeneratePatientInvoiceSerializer, GeneratePatientTestReportSerializer, TpaUltrasoundSerializer, \
    TpaUltrasoundConfigSerializer, TpaUltrasoundIntegrationSerializer, PrintReceptionistReportSerializer, \
    TpaUltrasoundImagesSerializer, ReferralDoctorReportSerializer, \
    TpaUltrasoundMetaInfoListViewSerializer, ActivityLogsSerializer, GeneratePatientRefundSerializer, \
    DoctorSharedTestReportSerializer, GetPrivilegeCardSerializer, \
    GeneratePatientMedicalCertificateSerializer, GenerateBarcodePDFTrailSerializer
from pro_laboratory.serializers.universal_serializers import PrintTemplateSerializer, PrintDataTemplateSerializer
from pro_pharmacy.views import GeneratePatientPharmacyBillingViewSet
from pro_universal_data.models import Tag, PrintTemplateType, DoctorSharedReport, ULabPaymentModeType

barcode.base.Barcode.default_writer_options['write_text'] = False
from barcode import Code128
from barcode.writer import ImageWriter

from rest_framework.views import APIView
from sib_api_v3_sdk import Configuration, ApiClient, TransactionalEmailsApi, SendSmtpEmailAttachment
from sib_api_v3_sdk.models import SendSmtpEmail
from django.conf import settings

from django.http import HttpResponse
from io import BytesIO
import logging

# Set root logger to DEBUG level to see all log messages
logging.basicConfig(level=logging.DEBUG)

# Setup a logger for this module
logger = logging.getLogger(__name__)

# try:
#     from weasyprint import HTML
# except ImportError as import_error:
#     HTML = None
#     print(import_error)
#     logger.error(f"Error importing HTML module from weasyprint, please do handle it!", exc_info=True)


# Suppress loggers related to WeasyPrint and GTK
weasyprint_loggers = [
    'weasyprint',
    'weasyprint.progress',
    'comtypes',
    'fontTools',
    'fontTools.ttLib',
    'fontTools.misc.configTools',
    'fontTools.misc',
    'fontTools.misc.roundTools',
    'fontTools.misc.fixedTools',
    'fontTools.ttLib.sfnt',
    'fontTools.ttLib.ttFont',
    'fontTools.ttLib.ttCollection',
    'fontTools.ttLib.tables.ttProgram',
    'fontTools.ttLib.tables',
    'fontTools.ttLib.tables._g_l_y_f',
    'fontTools.ttLib.woff2',
    'fontTools.ttLib.tables._l_o_c_a',
    'fontTools.ttLib.tables._h_m_t_x',
    'fontTools.ttLib.tables.otBase',
    'fontTools.ttLib.tables.otTables',
    'fontTools.ttLib.tables.otConverters',
    'fontTools.misc.psCharStrings',
    'fontTools.cffLib',
    'fontTools.ttLib.tables.S_V_G_',
    'fontTools.ttLib.tables.TupleVariation',
    'fontTools.ttLib.tables._n_a_m_e',
    'fontTools.otlLib.optimize.gpos',
    'fontTools.otlLib.optimize',
    'fontTools.otlLib',
    'fontTools.otlLib.builder',
    'fontTools.varLib.merger',
    'fontTools.varLib',
    'fontTools.designspaceLib.statNames',
    'fontTools.designspaceLib',
    'fontTools.designspaceLib.split',
    'fontTools.subset',
    'fontTools.subset.timer',
    'fontTools.ttLib.tables.BitmapGlyphMetrics',
    'fontTools.ttLib.tables.E_B_L_C_',
    'fontTools.ttLib.tables.E_B_D_T_',
    'fontTools.ttLib.tables._k_e_r_n',
    'fontTools.ttLib.tables._g_v_a_r',
    'fontTools.ttLib.tables._p_o_s_t',
    'fontTools.ttLib.tables._c_m_a_p',
    'fontTools.ttLib.tables._h_e_a_d',
    'fontTools.varlib.mutator'
]

try:
    # Set level to ERROR and add NullHandler for each logger
    for logger_name in weasyprint_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.ERROR)
        logger.addHandler(logging.NullHandler())
except Exception as error:
    print(error)

#
#
# # List all active loggers
# loggers = logging.root.manager.loggerDict
# for logger_name in loggers:
#     print(logger_name)

from rest_framework.response import Response


def get_pdf_content(test_ids, client_id, letterhead=None, water_mark=None):

    try:
        if isinstance(test_ids, str):
            test_ids = test_ids.split(',')
        elif not isinstance(test_ids, list):
            test_ids = [test_ids]

        download_api = DownloadTestReportViewset()
        download_response = download_api.list(
            test_ids=','.join([encode_id(test_id) for test_id in test_ids]),
            client_id=encode_id(client_id),
            letterhead=letterhead,
            water_mark='true' if water_mark else 'false'
        )
        print(download_response.data) 
        base64_pdf = download_response.data.get('pdf_base64', None)
        return base64_pdf
    except Exception as e:
        raise Exception(f"PDF generation failed: {str(e)}")


class ActivityLogsListView(generics.ListAPIView):
    queryset = ActivityLogs.objects.all()
    serializer_class = ActivityLogsSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ActivityLogsFilter

    def get_queryset(self):
        queryset = ActivityLogs.objects.all()
        query = self.request.query_params.get('q', None)
        sort = self.request.query_params.get('sort', None)
        if query is not None:
            search_query = Q(model__icontains=query)
            queryset = queryset.filter(search_query)
        if sort == '-added_on':
            queryset = queryset.order_by('-timestamp')
        if sort == 'added_on':
            queryset = queryset.order_by('timestamp')

        return queryset


class GenerateBarcodePDFViewset(viewsets.ModelViewSet):
    serializer_class = GenerateBarcodePDFTrailSerializer

    def get_queryset(self):
        return []

    def create(self=None, request=None, phlebotomist=None, *args, **kwargs):
        if request:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer_data = serializer.validated_data
            phlebotomist = serializer_data.get('phlebotomist')
            print(phlebotomist)
        else:
            print(phlebotomist)

        try:
            patient = phlebotomist.LabPatientTestID.patient
            lab_patient_test = phlebotomist.LabPatientTestID

            report_printed_on = datetime.now().strftime('%d-%m-%y %I:%M %p')

            details = {
                "patient": patient,
                "age": get_age_details(patient),
                "age_short_form": get_age_details_in_short_form(patient),
                "lab_patient_test": lab_patient_test,
                "lab_phlebotomist": phlebotomist,
                "customised_barcode_image": "",
                "report_printed_on": report_printed_on
            }

            # Function to replace tags found by regex search
            def replace_tag(match):
                tag_name = match.group(0)  # Capture the content without braces

                try:
                    # Fetch the tag by its name
                    tag = Tag.objects.get(tag_name=f'{tag_name}')

                    # Check if the tag requires fetching a collection of items
                    if tag.tag_formula:
                        try:
                            tag_value = str(eval(tag.tag_formula, {'details': details}))
                            return tag_value
                        except Exception as eval_error:
                            print(f"{tag_name} - Error in formula evaluation: {eval_error}")
                            return ""
                    else:
                        # If no formula, return a placeholder or a default value
                        return f""

                except Tag.DoesNotExist:
                    # If the tag doesn't exist, return a placeholder indicating so
                    return f""

            # Use regular expressions to find all patterns in curly braces, including the braces
            pattern = r'\{.*?\}'

            try:
                template_type = PrintTemplateType.objects.get(name='Barcode')
                print_template = PrintTemplate.objects.get(print_template_type=template_type, is_default=True)
                template = PrintDataTemplate.objects.get(print_template=print_template)
            except Exception as error:
                template = None

            show_customised_image = True

            if template:
                html_content = template.data
                matches = re.findall(pattern, html_content)

                # Check if {BarcodeGenerate} exists and remove it
                if '{CustomisedBarCodeImage}' in matches:
                    matches.remove('{CustomisedBarCodeImage}')
                    barcode_string = "|".join(matches)

                else:
                    barcode_string = f"{phlebotomist.assession_number}"

            else:
                barcode_string = "{SampleNo} | {MrNo} | {SampleCollectedTime}"

            # First, replace tags with their values
            barcode_content = re.sub(pattern, replace_tag, barcode_string)

            code = Code128(barcode_content, writer=ImageWriter())
            buffer = BytesIO()
            code.write(buffer)
            image = buffer.getvalue()
            barcode_image = base64.b64encode(image).decode('utf-8')
            barcode_alignments = PrintReportSettings.objects.first()

            barcode_image = f'''<img style="height:{barcode_alignments.barcode_height}px;width:{barcode_alignments.barcode_width}px;" src="data:image/png;base64,{barcode_image}" alt="Barcode Image">'''

            details['customised_barcode_image'] = barcode_image

            details['sample_no_barcode_image'] = barcode_image

            if template:
                html_content = template.data
            else:
                html_content = f"""
                                <!DOCTYPE html>
                                <html lang="en">
                                <head>
                                    <meta charset="UTF-8">
                                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                                    <title>Document</title>
                                </head>
                                <body>
                                    {barcode_image}
                                    <h4 style="width: 400px;margin:0px">{barcode_string}</h4>
                                </body>
                                </html>
                                """

                # First, replace tags with their values
            final_content = re.sub(pattern, replace_tag, html_content)

            return Response({'html_content': final_content})
            # return HttpResponse(final_content)
        except Exception as error:
            return Response({"Error": f"{error}"})


def encode_id(value):
    encoded_bytes = base64.urlsafe_b64encode(str(value).encode('utf-8'))
    return encoded_bytes.decode('utf-8')


def decode_id(value):
    decoded_bytes = base64.urlsafe_b64decode(value.encode('utf-8'))
    return decoded_bytes.decode('utf-8')


def generate_barcode_pdf(sample_id, mr_no, date_time):
    viewset = GenerateBarcodePDFViewset
    response = viewset.create(sample_id=sample_id, mr_no=mr_no, date_time=date_time)


def generate_barcode_image(barcode_no):  # For invoice no
    try:
        barcode_number = f"{barcode_no}"
        # Generate barcode with the custom options
        # code = Code128(barcode_number, writer=ImageWriter(), writer_options=options)
        code = Code128(
            barcode_number,
            writer=ImageWriter())
        buffer = BytesIO()
        code.write(buffer)
        image = buffer.getvalue()
        barcode_image = base64.b64encode(image).decode('utf-8')

        html_img_src = f"data:image/png;base64,{barcode_image}"

        return html_img_src
    except Exception as e:
        print(f"Error generating barcode image: {str(e)}")
        return None


def get_branch_address_of_lab_staff(lab_staff=None):
    try:
        branch_obj = LabStaffDefaultBranch.objects.filter(lab_staff=lab_staff).first()

        branches = branch_obj.default_branch.all()

        branch_addresses = []
        for branch in branches:
            branch_addresses.append(f"{branch.address}")
        return "\n".join(branch_addresses)
    except Exception as error:
        print(error)
        return ""




class GeneratePatientInvoiceViewset(viewsets.ModelViewSet):
    serializer_class = GeneratePatientInvoiceSerializer

    def get_queryset(self):
        return []

    def create(self, request=None, patient_id=None, client_id=None, printed_by=None, *args, **kwargs):
        if request:
            patient_id = self.request.query_params.get('patient_id', None)
            client_id = self.request.query_params.get('client_id', None)
            printed_by = self.request.query_params.get('printed_by', None)

            if patient_id and client_id:
                pass
            else:
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer_data = serializer.validated_data
                patient_id = serializer_data.get('patient_id')
                client_id = serializer_data.get('client_id')
                printed_by = serializer_data.get('printed_by')
            print(patient_id, client_id, printed_by)
        else:
            print(patient_id, client_id, printed_by)

        try:
            details = get_lab_patient_details(patient_id=patient_id, client_id=client_id, printed_by_id=printed_by)
            if details is None:
                return Response({"error": "Failed to retrieve lab patient details."}, status=400)
            labpatientinvoice = details['labpatientinvoice']

            template_type = PrintTemplateType.objects.get(name='Invoice')
            print_template = PrintTemplate.objects.get(print_template_type=template_type, is_default=True)
            template = PrintDataTemplate.objects.get(print_template=print_template)

        except Exception as error:
            print(error)
            return Response(f"Error fetching details: {error}", status=400)

        # print(f"details : {details}")

        search_pattern = r"\{(.*?)\}"
        expression_pattern = r"\[\[(.*?)\]\]"

        # Dictionary to hold totals for tags dynamically
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
                    # Handle fetching and formatting of all related data

                    if tag_name == "LabTestSNo":
                        related_objects = LabPatientTests.objects.filter(patient=details['patient'],
                                                                         is_package_test=False)
                        test_snos = []
                        test_count = 0
                        for obj in related_objects:
                            test_count += 1
                            test_snos.append(test_count)
                        packages = LabPatientPackages.objects.filter(patient=details['patient'])
                        for package in packages:
                            test_count += 1
                            test_snos.append(test_count)
                            tests = package.lab_tests.all()
                            for test in tests:
                                test_snos.append(f"<br>")

                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in test_snos)

                    if tag_name == "LabTestNames":
                        related_objects = LabPatientTests.objects.filter(patient=details['patient'],
                                                                         is_package_test=False)
                        test_names = []
                        for obj in related_objects:
                            if obj.status_id.name == 'Cancelled':
                                test_names.append(f"{obj.name} ({obj.status_id.name})")
                            else:
                                test_names.append(obj.name)
                        packages = LabPatientPackages.objects.filter(patient=details['patient'])
                        for package in packages:
                            test_names.append(f"<strong>{package.name}</strong>")
                            tests = package.lab_tests.all()
                            for test in tests:
                                test_names.append(f"{test.name}")

                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in test_names)

                    if tag_name == "LabTestPrice":
                        related_objects = LabPatientTests.objects.filter(patient=details['patient'],
                                                                         is_package_test=False)
                        test_prices = []
                        for obj in related_objects:
                            test_prices.append(obj.price)
                        packages = LabPatientPackages.objects.filter(patient=details['patient'])
                        for package in packages:
                            test_prices.append(package.offer_price)
                            tests = package.lab_tests.all()
                            for test in tests:
                                test_prices.append(f"<br>")

                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in test_prices)

                    if tag_name == "TotalLabTestPrice":  # Fetching and formatting test prices
                        related_objects = LabPatientTests.objects.filter(patient=details['patient'],
                                                                         is_package_test=False)
                        total_value = sum(getattr(obj, 'price', 0) for obj in related_objects)
                        package_objects = LabPatientPackages.objects.filter(patient=details['patient'])
                        total_value += sum(getattr(obj, 'offer_price', 0) for obj in package_objects)
                        accumulate_tag_totals(tag_name, total_value)
                        return str(total_value)

                    if tag_name == "ReceiptNo":
                        related_objects = LabPatientReceipts.objects.filter(invoiceid=details['labpatientinvoice'])
                        receipt_ids = [
                            obj.Receipt_id
                            for obj in related_objects
                            for _ in range(obj.payments.count())
                        ]
                        return "".join(f'<p style="margin: 3px 0px;">{receipt_id}</p>' for receipt_id in receipt_ids)

                    if tag_name == "PaymentMode":
                        related_objects = LabPatientReceipts.objects.filter(invoiceid=details['labpatientinvoice'])
                        payment_modes = [payment.pay_mode.name for obj in related_objects for payment in
                                         obj.payments.all()]
                        return "".join(f'<p style="margin: 3px 0px;">{mode}</p>' for mode in payment_modes)

                    if tag_name == "PaymentDate":
                        related_objects = LabPatientReceipts.objects.filter(invoiceid=details['labpatientinvoice'])
                        payment_dates = [
                            obj.added_on.strftime('%d-%m-%y, %I:%M %p')
                            for obj in related_objects
                            for _ in range(obj.payments.count())
                        ]
                        return "".join(f'<p style="margin: 3px 0px;">{date}</p>' for date in payment_dates)

                    if tag_name == "PaymentAmount":
                        related_objects = LabPatientReceipts.objects.filter(invoiceid=details['labpatientinvoice'])
                        payment_amounts = [
                            sum(payment.paid_amount for payment in obj.payments.filter(pay_mode=mode))
                            for obj in related_objects
                            for mode in obj.payments.values_list('pay_mode', flat=True).distinct()
                        ]
                        return "".join(f'<p style="margin: 3px 0px;">{amount}</p>' for amount in payment_amounts)

                    if tag_name == "PaymentRemark":
                        related_objects = LabPatientReceipts.objects.filter(invoiceid=details['labpatientinvoice'])
                        payment_remarks = [
                            obj.remarks
                            for obj in related_objects
                            for _ in range(obj.payments.count())
                        ]
                        return "".join(
                            f'<p style="margin: 3px 0px;">{payment_remark}</p>' for payment_remark in payment_remarks)

                    if tag_name == "TotalPaymentAmount":
                        related_objects = LabPatientInvoice.objects.filter(patient=details['patient'])
                        total_payment_amount = sum(obj.total_paid for obj in related_objects)
                        if total_payment_amount:
                            return f'₹ {total_payment_amount}'
                        else:
                            return ''

                    if tag_name == "PaymentAmountInWords":
                        # related_objects = LabPatientReceipts.objects.filter(invoiceid=details['labpatientinvoice'])
                        # total_paid_amount = sum(
                        #     payment.paid_amount for obj in related_objects for payment in obj.payments.all())
                        total_paid_amount = labpatientinvoice.total_paid
                        if total_paid_amount:
                            amount_in_words = num2words(total_paid_amount, lang='en_IN').title()
                            return f'({amount_in_words} Rupees only)'
                        else:
                            return ''

                    refund_objects = LabPatientRefund.objects.filter(patient=details['patient'])

                    if refund_objects.exists():
                        if tag_name == "RefundNo":
                            related_objects = LabPatientRefund.objects.filter(patient=details['patient'])
                            return "".join(
                                f'<p style="margin: 3px 0px;">{obj.refund_id}</p>' for obj in related_objects)

                        if tag_name == "RefundMode":
                            related_objects = LabPatientRefund.objects.filter(patient=details['patient'])

                            return "".join(
                                f'<p style="margin: 3px 0px;">{obj.refund_mode.name}</p>'
                                for obj in related_objects)

                        if tag_name == "RefundDate":
                            related_objects = LabPatientRefund.objects.filter(patient=details['patient'])

                            return "".join(
                                f'<p style="margin: 3px 0px;">{obj.added_on.strftime('%d-%m-%y, %I:%M %p')}</p>' for obj
                                in
                                related_objects)

                        if tag_name == "RefundRemark":
                            related_objects = LabPatientRefund.objects.filter(patient=details['patient'])

                            return "".join(f'<p style="margin: 3px 0px;">{obj.remarks}</p>' for obj in related_objects)

                        if tag_name == "RefundAmountInWords":
                            related_objects = LabPatientRefund.objects.filter(patient=details['patient'])
                            total_refund_amount = sum(obj.refund for obj in related_objects)
                            amount_in_words = num2words(total_refund_amount, lang='en_IN').title()
                            return f'({amount_in_words} Rupees only)'

                        if tag_name == "RefundAmount":
                            related_objects = LabPatientRefund.objects.filter(patient=details['patient'])
                            return "".join(
                                f'<p style="margin: 3px 0px;">₹ {obj.refund}</p>' for obj in related_objects)

                        if tag_name == "TotalRefundAmount":
                            related_objects = LabPatientRefund.objects.filter(patient=details['patient'])
                            total_refund_amount = sum(obj.refund for obj in related_objects)
                            return f'₹ {total_refund_amount}'
                    else:
                        # Exclude refund tags if no refund objects exist
                        return ""
                else:
                    # Handle single item fetch and formula evaluation as before
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
                # If the tag doesn't exist, return a placeholder indicating so
                return f"{tag_name} not found!"

                # New function to evaluate and replace expressions

        def evaluate_expression(match):
            expression = match.group(1)  # Capture the content without double brackets
            try:
                # Ensure you sanitize or validate the expression if using eval() directly poses a security risk
                result = str(eval(expression, {'__builtins__': None}, {'details': details}))
                return result
            except Exception as eval_error:
                print(f"Error in expression evaluation: {eval_error}")
                return "[Error]"  # Placeholder for any evaluation error

                # Now, add the new snippet here to replace total placeholders with actual total values

        def replace_total(match):
            tag_name = match.group(1)  # Extract the tag name
            total_value = tag_totals.get(tag_name, 0)  # Get the total value from tag_totals
            return str(total_value)  # Return the total value as a string

        template_content = template.data
        # First, replace tags with their values
        intermediate_content = re.sub(search_pattern, replace_tag, template_content)

        # Then, evaluate and replace expressions
        modified_content = re.sub(expression_pattern, evaluate_expression, intermediate_content)

        # Use the regular expression to find and replace total placeholders
        final_content = re.sub(expression_pattern, replace_total, modified_content)

        # Header
        template_header_content = template.header if template.header else ""
        intermediate_header_content = re.sub(search_pattern, replace_tag, template_header_content)
        modified_header_content = re.sub(expression_pattern, evaluate_expression, intermediate_header_content)
        final_header_content = re.sub(expression_pattern, replace_total, modified_header_content)

        letterhead_settings = details['letterhead_settings']
        letter_head_settings_content = LetterHeadSettingsSerializer(letterhead_settings).data

        # Footer
        template_footer_content = template.footer if template.footer else ""
        intermediate_footer_content = re.sub(search_pattern, replace_tag, template_footer_content)
        modified_footer_content = re.sub(expression_pattern, evaluate_expression, intermediate_footer_content)
        final_footer_content = re.sub(expression_pattern, replace_total, modified_footer_content)

        final_content = f'<div style="font-family:{letterhead_settings.default_font.value}">{final_content}</div>'
        return Response({'html_content': final_content,
                         "header": final_header_content,
                         "footer": final_footer_content})

        # return HttpResponse(final_header_content+final_content+final_footer_content)


class GeneratePatientReceiptViewSet(viewsets.ModelViewSet):
    serializer_class = GeneratePatientReceiptSerializer

    def get_queryset(self):
        return []

    def create(self, request=None, patient_id=None, client_id=None, receipt_id=None, printed_by_id=None, *args,
               **kwargs):
        if request:
            patient_id = self.request.query_params.get('patient_id', None)
            client_id = self.request.query_params.get('client_id', None)
            receipt_id = self.request.query_params.get('receipt_id', None)
            printed_by_id = self.request.query_params.get('printed_by', None)

            if client_id and (patient_id or receipt_id):
                pass

            else:
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer_data = serializer.validated_data
                patient_id = serializer_data.get('patient_id')
                client_id = serializer_data.get('client_id')
                receipt_id = serializer_data.get('receipt_id')
                printed_by_id = serializer_data.get('printed_by')

        else:
            pass

        try:
            details = get_lab_patient_details(patient_id=patient_id, client_id=client_id, receipt_id=receipt_id,
                                              printed_by_id=printed_by_id)
            if details is None:
                return Response({"error": "Failed to retrieve lab patient details."}, status=400)

            patient = details['patient']
            template = details['template']
            receipt = details['receipt']
            if receipt.payment_for.name == 'Medicines':
                try:
                    patient_receipt = GeneratePatientPharmacyBillingViewSet()


                    patient_receipt = patient_receipt.create(patient_id=patient.id, client_id=client_id, printed_by_id=printed_by_id, receipt_id=receipt_id)
                    return patient_receipt

                except Exception as error:
                    return Response(f"Error fetching details: {error}", status=400)


            receipts = LabPatientReceipts.objects.filter(patient=patient)
            invoice = LabPatientInvoice.objects.filter(patient=patient).first()


            tests_related_receipts = receipts.filter(payment_for__name='Lab Tests')
            consultations_related_receipts = receipts.filter(payment_for__name='Doctor Consultation')
            rooms_related_receipts = receipts.filter(payment_for__name='Rooms')
            services_related_receipts = receipts.filter(payment_for__name='Services')
            packages_related_receipts = receipts.filter(payment_for__name='Packages')

            if receipt.tests.exists() or receipt.packages.exists() or receipt.consultations.exists() or receipt.services.exists() or receipt.rooms.exists():
                concerned_receipts = LabPatientReceipts.objects.filter(id=receipt.id)
            else:
                payment_for = receipt.payment_for.name
                if payment_for == 'Doctor Consultation':
                    concerned_receipts = consultations_related_receipts
                elif payment_for == 'Services':
                    concerned_receipts = services_related_receipts
                elif payment_for == 'Rooms':
                    concerned_receipts = rooms_related_receipts
                elif payment_for == 'Lab Tests':
                    concerned_receipts = tests_related_receipts
                else:
                    concerned_receipts = LabPatientReceipts.objects.filter(id=receipt.id)

            all_tests_in_receipts = []
            all_packages_in_receipts = []
            all_payments_in_receipts = []
            all_consultations_in_receipts = []
            all_services_in_receipts = []
            all_rooms_in_receipts = []
            all_medicines_in_receipts = []

            if receipt.tests.exists() or receipt.packages.exists() or receipt.consultations.exists() or receipt.services.exists() or receipt.rooms.exists():
                all_tests_in_receipts = receipt.tests.all()
                all_packages_in_receipts = receipt.packages.all()
                all_payments_in_receipts = receipt.payments.all()
                all_consultations_in_receipts = receipt.consultations.all()
                all_services_in_receipts = receipt.services.all()
                all_rooms_in_receipts = receipt.rooms.all()
                all_medicines_in_receipts = receipt.medicines.all()

            else:
                for receipt_id in receipts:
                    tests = receipt_id.tests.all()
                    all_tests_in_receipts.extend(tests)

                    packages = receipt_id.packages.all()
                    all_packages_in_receipts.extend(packages)

                    payments = receipt_id.payments.all()
                    all_payments_in_receipts.extend(payments)

                    consultations = receipt_id.consultations.all()
                    all_consultations_in_receipts.extend(consultations)

                    services = receipt_id.services.all()
                    all_services_in_receipts.extend(services)

                    rooms = receipt_id.rooms.all()
                    all_rooms_in_receipts.extend(rooms)

                    medicines = receipt_id.medicines.all()
                    all_medicines_in_receipts.extend(medicines)

            refunds = LabPatientRefund.objects.filter(patient=patient)
            total_refund = sum(getattr(obj, 'refund', 0) for obj in refunds)


        except Exception as error:
            return Response(f"Error fetching details: {error}", status=400)

        search_pattern = r"\{(.*?)\}"
        expression_pattern = r"\[\[(.*?)\]\]"

        # Dictionary to hold totals for tags dynamically
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
                    if tag_name == "LabTestSNo":
                        related_objects = receipt.tests.all() if receipt.tests.exists() else all_tests_in_receipts
                        test_snos = []
                        test_count = 0
                        for obj in related_objects:
                            test_count += 1
                            test_snos.append(test_count)
                        packages = receipt.packages.all() if receipt.packages.exists() else all_packages_in_receipts
                        for package in packages:
                            test_count += 1
                            test_snos.append(test_count)
                            tests = package.lab_tests.all()
                            for test in tests:
                                test_snos.append(f"<br>")

                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in test_snos)

                    if tag_name == "LabTestNames":
                        related_objects = all_tests_in_receipts
                        test_names = []
                        if receipt.tests.exists() or receipt.packages.exists():
                            for obj in related_objects:
                                test_names.append(obj.name)
                        else:
                            for obj in related_objects:
                                if obj.status_id.name == 'Cancelled':
                                    test_names.append(f"{obj.name} ({obj.status_id.name})")
                                else:
                                    test_names.append(obj.name)

                        packages = all_packages_in_receipts
                        if receipt.tests.exists() or receipt.packages.exists():
                            for package in packages:
                                test_names.append(f"<strong>{package.name}</strong>")
                                tests = package.lab_tests.all()

                                for test in tests:
                                    test_names.append(f"{test.name}")
                        else:
                            for package in packages:
                                tests = package.lab_tests.all()
                                if all(test.status_id.name == "Cancelled" for test in tests):
                                    test_names.append(f"<strong>{package.name}</strong>(Cancelled)")
                                else:
                                    test_names.append(f"<strong>{package.name}</strong>")

                                for test in tests:
                                    test_names.append(f"{test.name}")

                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in test_names)

                    if tag_name == "LabTestPrice":
                        related_objects = receipt.tests.all() if receipt.tests.exists() else all_tests_in_receipts
                        test_prices = []

                        for obj in related_objects:
                            test_prices.append(obj.price)
                        packages = receipt.packages.all() if receipt.packages.exists() else all_packages_in_receipts
                        for package in packages:
                            test_prices.append(package.offer_price)
                            tests = package.lab_tests.all()
                            for test in tests:
                                test_prices.append(f"<br>")

                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in test_prices)

                    if tag_name == "TotalLabTestPrice":
                        related_objects = receipt.tests.all() if receipt.tests.exists() else all_tests_in_receipts
                        total_value = 0

                        if receipt.tests.exists() or receipt.packages.exists():
                            total_value = sum(getattr(obj, 'price', 0) for obj in related_objects)
                        else:
                            total_value = invoice.total_cost

                        packages = receipt.packages.all() if receipt.packages.exists() else all_packages_in_receipts

                        if receipt.tests.exists() or receipt.packages.exists():
                            total_value += sum(getattr(obj, 'offer_price', 0) for obj in packages)
                        else:
                            total_value = invoice.total_cost
                        accumulate_tag_totals(tag_name, total_value)
                        return str(total_value)

                    if tag_name == "SubTotalOfReceipt":
                        related_objects = receipt.tests.all() if receipt.tests.exists() else all_tests_in_receipts
                        total_value = 0

                        if receipt.tests.exists() or receipt.packages.exists():
                            total_value = sum(getattr(obj, 'price', 0) for obj in related_objects)
                        else:
                            total_value = invoice.total_cost

                        packages = receipt.packages.all() if receipt.packages.exists() else all_packages_in_receipts

                        if receipt.tests.exists() or receipt.packages.exists():
                            total_value += sum(getattr(obj, 'offer_price', 0) for obj in packages)
                        else:
                            total_value = invoice.total_cost
                        return str(total_value)

                    if tag_name == "TotalDiscountOfReceipt":
                        related_objects = receipt.tests.all() if receipt.tests.exists() else all_tests_in_receipts
                        total_value = 0

                        if receipt.tests.exists() or receipt.packages.exists():
                            total_value = receipt.discount_amt
                        else:
                            total_value = invoice.total_discount
                        return str(total_value)

                    if tag_name == "TotalOfReceipt":
                        related_objects = receipt.tests.all() if receipt.tests.exists() else all_tests_in_receipts
                        total_value = 0

                        if receipt.tests.exists() or receipt.packages.exists():
                            total_value = sum(getattr(obj, 'price', 0) for obj in related_objects)
                        else:
                            pass

                        packages = receipt.packages.all() if receipt.packages.exists() else all_packages_in_receipts

                        if receipt.tests.exists() or receipt.packages.exists():
                            total_value += sum(getattr(obj, 'offer_price', 0) for obj in packages)
                        else:
                            pass

                        if receipt.tests.exists() or receipt.packages.exists():
                            total_price = total_value - receipt.discount_amt
                        else:
                            total_price = invoice.total_price

                        return str(total_price)

                    if tag_name == "HideRecNetAmountIfZero":
                        related_objects = receipt.tests.all() if receipt.tests.exists() else all_tests_in_receipts
                        total_value = 0

                        if receipt.tests.exists() or receipt.packages.exists():
                            total_value = sum(getattr(obj, 'price', 0) for obj in related_objects)
                        else:
                            pass

                        packages = receipt.packages.all() if receipt.packages.exists() else all_packages_in_receipts

                        if receipt.tests.exists() or receipt.packages.exists():
                            total_value += sum(getattr(obj, 'offer_price', 0) for obj in packages)
                        else:
                            pass

                        if receipt.tests.exists() or receipt.packages.exists():
                            total_price = total_value - receipt.discount_amt
                        else:
                            total_price = invoice.total_price

                        return str(total_price) if receipt.discount_amt else ""

                    if tag_name == "TotalPaidOfReceipt":
                        if receipt.tests.exists() or receipt.packages.exists():
                            total_value = sum(getattr(obj, 'paid_amount', 0) for obj in receipt.payments.all())
                        else:
                            total_value = invoice.total_paid

                        return str(total_value)

                    if tag_name == "TotalDueOfReceipt":
                        related_objects = receipt.tests.all() if receipt.tests.exists() else all_tests_in_receipts
                        total_value = 0

                        if receipt.tests.exists() or receipt.packages.exists():
                            total_value = sum(getattr(obj, 'price', 0) for obj in related_objects)
                        else:
                            total_value = invoice.total_due

                        packages = receipt.packages.all() if receipt.packages.exists() else all_packages_in_receipts

                        if receipt.tests.exists() or receipt.packages.exists():
                            total_value += sum(getattr(obj, 'offer_price', 0) for obj in packages)
                        else:
                            total_value = invoice.total_due

                        if receipt.tests.exists() or receipt.packages.exists():
                            related_objects = receipt.payments.all() if (
                                    receipt.tests.exists() or receipt.packages.exists()) else all_payments_in_receipts
                            receipt_paid_amount = sum(getattr(obj, 'paid_amount', 0) for obj in related_objects)

                            total_due = total_value - receipt.discount_amt - receipt_paid_amount
                        else:
                            total_due = invoice.total_due

                        return str(total_due)

                    if tag_name == "ReceiptNo":
                        related_objects = LabPatientReceipts.objects.filter(id=receipt.id) if (
                                receipt.tests.exists() or receipt.packages.exists()) else LabPatientReceipts.objects.filter(
                            patient=patient)
                        receipt_ids = [
                            obj.Receipt_id
                            for obj in related_objects
                            for _ in range(obj.payments.count())
                        ]
                        return "".join(f'<p style="margin: 3px 0px;">{receipt_id}</p>' for receipt_id in
                                       receipt_ids)

                    if tag_name == "PaymentMode":
                        related_objects = LabPatientReceipts.objects.filter(id=receipt.id) if (
                                receipt.tests.exists() or receipt.packages.exists()) else LabPatientReceipts.objects.filter(
                            patient=patient)
                        payment_modes = [payment.pay_mode.name for obj in related_objects for payment in
                                         obj.payments.all()]
                        return "".join(
                            f'<p style="margin: 3px 0px;">{mode}</p>' for mode in payment_modes)

                    if tag_name == "PaymentModeInOneLine":
                        related_objects = LabPatientReceipts.objects.filter(id=receipt.id) if (
                                receipt.tests.exists() or receipt.packages.exists()) else LabPatientReceipts.objects.filter(
                            patient=patient)
                        payment_modes = [payment.pay_mode.name for obj in related_objects for payment in
                                         obj.payments.all()]
                        return ",".join(str(mode) for mode in payment_modes)

                    if tag_name == "PaymentDate":
                        related_objects = LabPatientReceipts.objects.filter(id=receipt.id) if (
                                receipt.tests.exists() or receipt.packages.exists()) else LabPatientReceipts.objects.filter(
                            patient=patient)
                        payment_dates = [
                            obj.added_on.strftime('%d-%m-%y, %I:%M %p')
                            for obj in related_objects
                            for _ in range(obj.payments.count())
                        ]
                        return "".join(
                            f'<p style="margin: 3px 0px;">{date}</p>' for date in payment_dates)

                    if tag_name == "PaymentAmount":
                        related_objects = LabPatientReceipts.objects.filter(id=receipt.id) if (
                                receipt.tests.exists() or receipt.packages.exists()) else LabPatientReceipts.objects.filter(
                            patient=patient)
                        payment_amounts = [
                            sum(payment.paid_amount for payment in obj.payments.filter(pay_mode=mode))
                            for obj in related_objects
                            for mode in obj.payments.values_list('pay_mode', flat=True).distinct()
                        ]
                        return "".join(
                            f'<p style="margin: 3px 0px;">{amount}</p>' for amount in payment_amounts)

                    if tag_name == "PaymentRemark":
                        related_objects = LabPatientReceipts.objects.filter(id=receipt.id) if (
                                receipt.tests.exists() or receipt.packages.exists()) else LabPatientReceipts.objects.filter(
                            patient=patient)
                        payment_remarks = [
                            obj.remarks
                            for obj in related_objects
                            for _ in range(obj.payments.count())
                        ]
                        return "".join(
                            f'<p style="margin: 3px 0px;">{payment_remark if payment_remark else "-"}</p>' for payment_remark in
                            payment_remarks)

                        # IP/OP tags


                    # common tags
                    if tag_name == 'RecSNo':
                        payment_for = receipt.payment_for.name
                        if payment_for == 'Doctor Consultation':
                            related_objects = all_consultations_in_receipts
                            consultations_snos = []
                            consultations_count = 0
                            for obj in related_objects:
                                consultations_count += 1
                                consultations_snos.append(consultations_count)

                            return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in consultations_snos)


                        elif payment_for == 'Services':
                            related_objects = all_services_in_receipts
                            services_snos = []
                            services_count = 0
                            for obj in related_objects:
                                services_count += 1
                                services_snos.append(services_count)

                            return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in services_snos)


                        elif payment_for == 'Rooms':
                            related_objects = all_rooms_in_receipts
                            rooms_snos = []
                            rooms_count = 0
                            for obj in related_objects:
                                rooms_count += 1
                                rooms_snos.append(rooms_count)

                            return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in rooms_snos)


                        elif payment_for == 'Lab Tests':
                            related_objects = all_tests_in_receipts
                            test_snos = []
                            test_count = 0
                            for obj in related_objects:
                                test_count += 1
                                test_snos.append(test_count)

                            return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in test_snos)

                        else:
                            return ""

                    if tag_name == 'RecNames':
                        payment_for = receipt.payment_for.name
                        if payment_for == 'Doctor Consultation':
                            related_objects = all_consultations_in_receipts
                            consultation_names = []
                            for obj in related_objects:
                                consultation_names.append(f"CONSULTATION-{obj.consultation.labdoctors.name}")

                            return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in consultation_names)


                        elif payment_for == 'Services':
                            related_objects = all_services_in_receipts
                            services_names = []
                            for obj in related_objects:
                                services_names.append(f"{obj.name}")

                            return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in services_names)


                        elif payment_for == 'Rooms':
                            related_objects = all_rooms_in_receipts
                            rooms_names = []
                            for obj in related_objects:
                                rooms_names.append(f"{obj.name}")

                            return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in rooms_names)


                        elif payment_for == 'Lab Tests':
                            related_objects = all_tests_in_receipts
                            test_names = []
                            for obj in related_objects:
                                test_names.append(obj.name)

                            return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in test_names)

                        else:
                            return ""

                    if tag_name == 'RecPrices':
                        payment_for = receipt.payment_for.name
                        if payment_for == 'Doctor Consultation':
                            related_objects = all_consultations_in_receipts
                            consultation_prices = []
                            for obj in related_objects:
                                consultation_prices.append(obj.consultation_fee)

                            return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in consultation_prices)


                        elif payment_for == 'Services':
                            related_objects = all_services_in_receipts
                            services_prices = []
                            for obj in related_objects:
                                services_prices.append(obj.price)

                            return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in services_prices)


                        elif payment_for == 'Rooms':
                            related_objects = all_rooms_in_receipts
                            rooms_prices = []
                            for obj in related_objects:
                                if obj.no_of_days:
                                    rooms_prices.append(obj.charges_per_bed * obj.no_of_days)

                            return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in rooms_prices)


                        elif payment_for == 'Lab Tests':
                            related_objects = all_tests_in_receipts
                            test_prices = []
                            for obj in related_objects:
                                test_prices.append(obj.price)

                            return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in test_prices)

                        else:
                            return ""

                    if tag_name == 'RecTotalPrice':
                        payment_for = receipt.payment_for.name
                        if payment_for == 'Doctor Consultation':
                            related_objects = all_consultations_in_receipts
                            total_value = 0
                            if related_objects:
                                total_value = sum(obj.consultation_fee for obj in related_objects)

                            return str(total_value)


                        elif payment_for == 'Services':
                            related_objects = all_services_in_receipts
                            total_value = 0
                            if related_objects:
                                total_value = sum(obj.price for obj in related_objects)

                            return str(total_value)


                        elif payment_for == 'Rooms':
                            related_objects = all_rooms_in_receipts
                            total_value = 0
                            if related_objects:
                                total_value = sum(obj.charges_per_bed * obj.no_of_days if obj.no_of_days else 0.00 for obj in related_objects)

                            return str(total_value)

                        elif payment_for == 'Lab Tests':
                            related_objects = all_tests_in_receipts
                            total_value = 0
                            if related_objects:
                                total_value = sum(obj.price for obj in related_objects)

                            return str(total_value)

                        else:
                            return ""

                    if tag_name == 'RecTotalDisc':
                        payment_for = receipt.payment_for.name
                        if payment_for == 'Doctor Consultation':
                            related_objects = receipts.filter(
                                id=receipt.id) if receipt.consultations.all() else receipts.filter(
                                payment_for__name=payment_for)
                            total_value = 0
                            for obj in related_objects:
                                total_value += obj.discount_amt

                            return str(total_value)

                        elif payment_for == 'Services':
                            related_objects = receipts.filter(
                                id=receipt.id) if receipt.services.all() else receipts.filter(
                                payment_for__name=payment_for)
                            total_value = 0
                            for obj in related_objects:
                                total_value += obj.discount_amt

                            return str(total_value)


                        elif payment_for == 'Rooms':
                            related_objects = receipts.filter(
                                id=receipt.id) if receipt.rooms.all() else receipts.filter(
                                payment_for__name=payment_for)
                            total_value = 0
                            for obj in related_objects:
                                total_value += obj.discount_amt

                            return str(total_value)


                        elif payment_for == 'Lab Tests':
                            related_objects = receipts.filter(
                                id=receipt.id) if receipt.tests.all() else receipts.filter(
                                payment_for__name=payment_for)
                            total_value = 0
                            for obj in related_objects:
                                total_value += obj.discount_amt

                            return str(total_value)

                        else:
                            return ""

                    if tag_name == 'HideRecTotalDisc':
                        payment_for = receipt.payment_for.name
                        if payment_for == 'Doctor Consultation':
                            related_objects = receipts.filter(
                                id=receipt.id) if receipt.consultations.all() else receipts.filter(
                                payment_for__name=payment_for)
                            total_value = 0
                            for obj in related_objects:
                                total_value += obj.discount_amt

                            return str(total_value) if total_value else ""

                        elif payment_for == 'Services':
                            related_objects = receipts.filter(
                                id=receipt.id) if receipt.services.all() else receipts.filter(
                                payment_for__name=payment_for)
                            total_value = 0
                            for obj in related_objects:
                                total_value += obj.discount_amt

                            return str(total_value) if total_value else ""


                        elif payment_for == 'Rooms':
                            related_objects = receipts.filter(
                                id=receipt.id) if receipt.rooms.all() else receipts.filter(
                                payment_for__name=payment_for)
                            total_value = 0
                            for obj in related_objects:
                                total_value += obj.discount_amt

                            return str(total_value) if total_value else ""


                        elif payment_for == 'Lab Tests':
                            related_objects = receipts.filter(
                                id=receipt.id) if receipt.tests.all() else receipts.filter(
                                payment_for__name=payment_for)
                            total_value = 0
                            for obj in related_objects:
                                total_value += obj.discount_amt

                            return str(total_value) if total_value else ""

                        else:
                            return ""

                    if tag_name == 'RecNetAmt':
                        payment_for = receipt.payment_for.name
                        if payment_for == 'Doctor Consultation':
                            related_objects = all_consultations_in_receipts
                            total_cost = sum(obj.consultation_fee for obj in related_objects)

                            related_objects = receipts.filter(
                                id=receipt.id) if receipt.consultations.all() else receipts.filter(
                                payment_for__name=payment_for)
                            total_discount = 0
                            for obj in related_objects:
                                total_discount += obj.discount_amt

                            total_price = total_cost - total_discount

                            return str(total_price)


                        elif payment_for == 'Services':
                            related_objects = all_services_in_receipts
                            total_cost = sum(obj.price for obj in related_objects)
                            related_objects = receipts.filter(
                                id=receipt.id) if receipt.services.all() else receipts.filter(
                                payment_for__name=payment_for)
                            total_discount = 0
                            for obj in related_objects:
                                total_discount += obj.discount_amt

                            total_price = total_cost - total_discount

                            return str(total_price)


                        elif payment_for == 'Rooms':
                            related_objects = all_rooms_in_receipts
                            total_cost = sum(obj.charges_per_bed * obj.no_of_days if obj.no_of_days else Decimal(0.00) for obj in related_objects)

                            related_objects = receipts.filter(
                                id=receipt.id) if receipt.rooms.all() else receipts.filter(
                                payment_for__name=payment_for)
                            total_discount = 0
                            for obj in related_objects:
                                total_discount += obj.discount_amt

                            total_price = total_cost - total_discount

                            return str(total_price)

                        elif payment_for == 'Lab Tests':
                            total_price = 0
                            related_objects = all_tests_in_receipts
                            total_cost = sum(obj.price for obj in related_objects)

                            related_objects = receipts.filter(
                                id=receipt.id) if receipt.tests.all() else receipts.filter(
                                payment_for__name=payment_for)
                            total_discount = 0
                            for obj in related_objects:
                                total_discount += obj.discount_amt

                            total_price = total_cost - total_discount

                            return str(total_price)

                        else:
                            return ""

                    if tag_name == 'HideRecNetAmt':
                        payment_for = receipt.payment_for.name
                        if payment_for == 'Doctor Consultation':
                            related_objects = all_consultations_in_receipts
                            total_cost = sum(obj.consultation_fee for obj in related_objects)

                            related_objects = receipts.filter(
                                id=receipt.id) if receipt.consultations.all() else receipts.filter(
                                payment_for__name=payment_for)
                            total_discount = 0
                            for obj in related_objects:
                                total_discount += obj.discount_amt

                            total_price = total_cost - total_discount

                            return str(total_price) if total_price else ""


                        elif payment_for == 'Services':
                            related_objects = all_services_in_receipts
                            total_cost = sum(obj.price for obj in related_objects)
                            related_objects = receipts.filter(
                                id=receipt.id) if receipt.services.all() else receipts.filter(
                                payment_for__name=payment_for)
                            total_discount = 0
                            for obj in related_objects:
                                total_discount += obj.discount_amt

                            total_price = total_cost - total_discount

                            return str(total_price) if total_price else ""


                        elif payment_for == 'Rooms':
                            related_objects = all_rooms_in_receipts
                            total_cost = sum(obj.charges_per_bed * obj.no_of_days if obj.no_of_days else Decimal(0.00) for obj in related_objects)

                            related_objects = receipts.filter(
                                id=receipt.id) if receipt.rooms.all() else receipts.filter(
                                payment_for__name=payment_for)
                            total_discount = 0
                            for obj in related_objects:
                                total_discount += obj.discount_amt

                            total_price = total_cost - total_discount

                            return str(total_price) if total_price else ""

                        elif payment_for == 'Lab Tests':
                            total_price = 0
                            related_objects = all_tests_in_receipts
                            total_cost = sum(obj.price for obj in related_objects).filter(payment_for__name=payment_for)

                            related_objects = receipts.filter(id=receipt.id) if receipt.tests.all() else receipts
                            total_discount = 0
                            for obj in related_objects:
                                total_discount += obj.discount_amt

                            total_price = total_cost - total_discount

                            return str(total_price) if total_price else ""

                        else:
                            return ""

                    if tag_name == 'RecPaidAmt':
                        payment_for = receipt.payment_for.name
                        if payment_for == 'Doctor Consultation':
                            related_objects = receipts.filter(
                                id=receipt.id) if receipt.consultations.all() else receipts.filter(
                                payment_for__name=payment_for)
                            paid_amount = 0

                            for obj in related_objects:
                                payments = obj.payments.all()
                                for payment in payments:
                                    paid_amount += payment.paid_amount

                            return str(paid_amount)

                        elif payment_for == 'Services':
                            related_objects = receipts.filter(
                                id=receipt.id) if receipt.services.all() else receipts.filter(
                                payment_for__name=payment_for)
                            paid_amount = 0

                            for obj in related_objects:
                                payments = obj.payments.all()
                                for payment in payments:
                                    paid_amount += payment.paid_amount

                            return str(paid_amount)


                        elif payment_for == 'Rooms':
                            related_objects = receipts.filter(
                                id=receipt.id) if receipt.rooms.all() else receipts.filter(
                                payment_for__name=payment_for)
                            paid_amount = 0

                            for obj in related_objects:
                                payments = obj.payments.all()
                                for payment in payments:
                                    paid_amount += payment.paid_amount

                            return str(paid_amount)

                        elif payment_for == 'Lab Tests':
                            related_objects = receipts.filter(
                                id=receipt.id) if receipt.tests.all() else receipts.filter(
                                payment_for__name=payment_for)
                            paid_amount = 0

                            for obj in related_objects:
                                payments = obj.payments.all()
                                for payment in payments:
                                    paid_amount += payment.paid_amount

                            return str(paid_amount)

                        else:
                            return ""

                    if tag_name == 'RecDueAmt':
                        payment_for = receipt.payment_for.name
                        if payment_for == 'Doctor Consultation':
                            related_objects = all_consultations_in_receipts
                            total_due = 0
                            total_cost = sum(obj.consultation_fee for obj in related_objects)
                            paid_amount = 0
                            discount_amount = 0
                            related_receipts = receipts.filter(
                                id=receipt.id) if receipt.consultations.all() else receipts.filter(
                                payment_for__name=payment_for)

                            for obj in related_receipts:
                                discount_amount += obj.discount_amt
                                payments = obj.payments.all()
                                for payment in payments:
                                    paid_amount += payment.paid_amount

                            total_due = total_cost - paid_amount - discount_amount

                            return str(total_due)

                        elif payment_for == 'Services':
                            related_objects = all_services_in_receipts
                            total_due = 0
                            total_cost = sum(obj.price for obj in related_objects)
                            paid_amount = 0
                            discount_amount = 0
                            related_receipts = receipts.filter(
                                id=receipt.id) if receipt.services.all() else receipts.filter(
                                payment_for__name=payment_for)
                            for obj in related_receipts:
                                discount_amount += obj.discount_amt
                                payments = obj.payments.all()
                                for payment in payments:
                                    paid_amount += payment.paid_amount

                            total_due = total_cost - paid_amount - discount_amount

                            return str(total_due)

                        elif payment_for == 'Rooms':
                            related_objects = all_rooms_in_receipts
                            total_due = 0
                            total_cost = sum(obj.charges_per_bed * obj.no_of_days if obj.no_of_days else Decimal(0.00) for obj in related_objects)
                            paid_amount = 0
                            discount_amount = 0
                            related_receipts = receipts.filter(
                                id=receipt.id) if receipt.services.all() else receipts.filter(
                                payment_for__name=payment_for)
                            for obj in related_receipts:
                                discount_amount += obj.discount_amt
                                payments = obj.payments.all()
                                for payment in payments:
                                    paid_amount += payment.paid_amount

                            total_due = total_cost - paid_amount - discount_amount

                            return str(total_due)


                        elif payment_for == 'Lab Tests':
                            related_objects = all_tests_in_receipts
                            total_due = 0
                            total_cost = sum(obj.price for obj in related_objects)
                            paid_amount = 0
                            discount_amount = 0
                            related_receipts = receipts.filter(
                                id=receipt.id) if receipt.tests.all() else receipts.filter(
                                payment_for__name=payment_for)
                            for obj in related_receipts:
                                discount_amount += obj.discount_amt
                                payments = obj.payments.all()
                                for payment in payments:
                                    paid_amount += payment.paid_amount

                            total_due = total_cost - paid_amount - discount_amount

                            return str(total_due)

                        else:
                            return ""



                    if tag_name == "RecReceiptNo":
                        receipt_ids = [
                            obj.Receipt_id
                            for obj in concerned_receipts
                            for _ in range(obj.payments.count())
                        ]
                        return "".join(f'<p style="margin: 3px 0px;">{receipt_id}</p>' for receipt_id in
                                       receipt_ids)


                    if tag_name == "RecPaymentMode":
                        related_objects = concerned_receipts

                        payment_modes = [payment.pay_mode.name for obj in related_objects for payment in
                                         obj.payments.all()]
                        return "".join(f'<p style="margin: 3px 0px;">{mode}</p>' for mode in payment_modes)

                    if tag_name == "RecPaymentModeInOneLine":
                        related_objects = concerned_receipts

                        payment_modes = [payment.pay_mode.name for obj in related_objects for payment in
                                         obj.payments.all()]
                        return ",".join(str(mode) for mode in payment_modes)

                    if tag_name == "RecPaymentDate":
                        related_objects = concerned_receipts

                        payment_dates = [
                            obj.added_on.strftime('%d-%m-%y, %I:%M %p')
                            for obj in related_objects
                            for _ in range(obj.payments.count())
                        ]
                        return "".join(f'<p style="margin: 3px 0px;">{date}</p>' for date in payment_dates)

                    if tag_name == "RecPaymentAmount":
                        related_objects = concerned_receipts

                        payment_amounts = [
                            sum(payment.paid_amount for payment in obj.payments.filter(pay_mode=mode))
                            for obj in related_objects
                            for mode in obj.payments.values_list('pay_mode', flat=True).distinct()
                        ]
                        return "".join(
                            f'<p style="margin: 3px 0px;">{amount}</p>' for amount in payment_amounts)

                    if tag_name == "RecPaymentRemark":
                        related_objects = concerned_receipts

                        payment_remarks = [
                            obj.remarks
                            for obj in related_objects
                            for _ in range(obj.payments.count())
                        ]
                        print(payment_remarks)
                        return "".join(
                            f'<p style="margin: 3px 0px;">{payment_remark if payment_remark else "-"}</p>' for payment_remark in
                            payment_remarks)
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
                # If the tag doesn't exist, return a placeholder indicating so
                return f"{tag_name} not found!"

                # New function to evaluate and replace expressions

        def evaluate_expression(match):
            expression = match.group(1)  # Capture the content without double brackets
            try:
                # Ensure you sanitize or validate the expression if using eval() directly poses a security risk
                result = str(eval(expression, {'__builtins__': None}, {'details': details}))
                return result
            except Exception as eval_error:
                print(f"Error in expression evaluation: {eval_error}")
                return "[Error]"  # Placeholder for any evaluation error

        # Now, add the new snippet here to replace total placeholders with actual total values
        def replace_total(match):
            tag_name = match.group(1)  # Extract the tag name
            total_value = tag_totals.get(tag_name, 0)  # Get the total value from tag_totals
            return str(total_value)  # Return the total value as a string

        template_content = template.data
        # First, replace tags with their values
        intermediate_content = re.sub(search_pattern, replace_tag, template_content)

        # Then, evaluate and replace expressions
        modified_content = re.sub(expression_pattern, evaluate_expression, intermediate_content)

        # Use the regular expression to find and replace total placeholders
        final_content = re.sub(expression_pattern, replace_total, modified_content)

        # Header
        template_header_content = template.header if template.header else ""
        intermediate_header_content = re.sub(search_pattern, replace_tag, template_header_content)
        modified_header_content = re.sub(expression_pattern, evaluate_expression, intermediate_header_content)
        final_header_content = re.sub(expression_pattern, replace_total, modified_header_content)
        letterhead_settings = details['letterhead_settings']
        # Footer
        template_footer_content = template.footer if template.footer else ""
        intermediate_footer_content = re.sub(search_pattern, replace_tag, template_footer_content)
        modified_footer_content = re.sub(expression_pattern, evaluate_expression, intermediate_footer_content)
        final_footer_content = re.sub(expression_pattern, replace_total, modified_footer_content)

        final_content = f'<div style="font-family:{letterhead_settings.default_font.value}">{final_content}</div>'
        pdf_file = HTML(string=final_content).write_pdf()
        pdf_base64 = f"data:application/pdf;base64,{base64.b64encode(pdf_file).decode('utf-8')}"

        return Response({'id': receipt.id,
                         'html_content': final_content,
                         "pdf_base64": pdf_base64,
                         "header": final_header_content,
                         "footer": final_footer_content})

        # return HttpResponse(final_header_content+final_content+final_footer_content)


class GenerateConsolidatedBillViewSet(viewsets.ModelViewSet):
    serializer_class = GeneratePatientReceiptSerializer

    def get_queryset(self):
        return []

    def create(self, request=None, patient_id=None, client_id=None, receipt_id=None, printed_by_id=None, *args,
               **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer_data = serializer.validated_data
        patient_id = serializer_data.get('patient_id')
        client_id = serializer_data.get('client_id')
        template_type = serializer_data.get('template_type')
        printed_by_id = serializer_data.get('printed_by')

        try:
            details = get_lab_patient_details(patient_id=patient_id, client_id=client_id,
                                              printed_by_id=printed_by_id)
            if details is None:
                return Response({"error": "Failed to retrieve lab patient details."}, status=400)

            template_type = PrintTemplateType.objects.get(id=template_type)
            print_template = PrintTemplate.objects.get(print_template_type=template_type, is_default=True)
            template = PrintDataTemplate.objects.get(print_template=print_template)

            patient = details['patient']
            invoice = LabPatientInvoice.objects.filter(patient=patient).first()

            all_tests_in_receipts = []
            all_consultations_in_receipts = []
            all_rooms_in_receipts = []
            all_services_in_receipts = []
            all_packages_in_receipts = []

            all_receipts = LabPatientReceipts.objects.filter(patient=patient)
            tests_related_receipts = all_receipts.filter(payment_for__name='Lab Tests')
            consultations_related_receipts = all_receipts.filter(payment_for__name='Doctor Consultation')
            rooms_related_receipts = all_receipts.filter(payment_for__name='Rooms')
            services_related_receipts = all_receipts.filter(payment_for__name='Services')
            packages_related_receipts = all_receipts.filter(payment_for__name='Packages')

            total_cost_of_report = invoice.total_cost
            total_discount_of_report = invoice.total_discount
            total_price_of_report = invoice.total_price
            total_paid_of_report = invoice.total_paid
            total_due_of_report = invoice.total_due
            total_refund_of_report = invoice.total_refund

            test_snos = []
            test_names = []
            test_prices = []
            tests_count = 0
            total_cost_of_tests = 0
            total_discount_of_tests = 0
            total_paid_of_tests = 0

            for tests_related_receipt in tests_related_receipts:
                all_tests_in_receipts.extend(tests_related_receipt.tests.all())
                total_discount_of_tests += tests_related_receipt.discount_amt
                for payment in tests_related_receipt.payments.all():
                    total_paid_of_tests += payment.paid_amount

            for test in all_tests_in_receipts:
                tests_count += 1
                test_snos.append(tests_count)

                if test.status_id.name =='Cancelled':
                    test_names.append(f"{test.name} (Cancelled)")
                    test_prices.append(f"0.00")
                else:
                    total_cost_of_tests+=test.price
                    test_names.append(f"{test.name}")
                    test_prices.append(f"{test.price}")

            net_amount_of_tests = total_cost_of_tests - total_discount_of_tests
            total_due_of_tests = total_cost_of_tests - total_discount_of_tests - total_paid_of_tests

            consultation_snos = []
            consultation_names = []
            consultation_prices = []
            consultations_count = 0
            total_cost_of_consultations = 0
            total_discount_of_consultations = 0
            total_paid_of_consultations = 0

            for consultations_related_receipt in consultations_related_receipts:
                all_consultations_in_receipts.extend(consultations_related_receipt.consultations.all())
                total_discount_of_consultations += consultations_related_receipt.discount_amt
                for payment in consultations_related_receipt.payments.all():
                    total_paid_of_consultations+=payment.paid_amount

            for consultation in all_consultations_in_receipts:
                consultations_count += 1
                consultation_snos.append(consultations_count)

                if consultation.status_id.name =='Cancelled':
                    consultation_names.append(f"{consultation.consultation.labdoctors.name} (Cancelled)")
                    consultation_prices.append(f"0.00")
                else:
                    total_cost_of_consultations+=consultation.consultation_fee
                    consultation_names.append(f"CONSULTATION-{consultation.consultation.labdoctors.name}")
                    consultation_prices.append(f"{consultation.consultation_fee}")

            net_amount_of_consultations = total_cost_of_consultations - total_discount_of_consultations
            total_due_of_consultations = total_cost_of_consultations - total_discount_of_consultations - total_paid_of_consultations

            room_snos = []
            room_names = []
            room_prices = []
            rooms_count = 0
            total_cost_of_rooms = 0
            total_discount_of_rooms = 0
            total_paid_of_rooms = 0

            for rooms_related_receipt in rooms_related_receipts:
                all_rooms_in_receipts.extend(rooms_related_receipt.rooms.all())
                total_discount_of_rooms += rooms_related_receipt.discount_amt
                for payment in rooms_related_receipt.payments.all():
                    total_paid_of_rooms+=payment.paid_amount

            for room in all_rooms_in_receipts:
                rooms_count += 1
                room_snos.append(rooms_count)

                total_cost_of_rooms+=room.charges_per_bed
                room_names.append(f"{room.name}")
                room_prices.append(f"{room.charges_per_bed}")


            net_amount_of_rooms = total_cost_of_rooms - total_discount_of_rooms
            total_due_of_rooms = total_cost_of_rooms - total_discount_of_rooms - total_paid_of_rooms

            service_snos = []
            service_names = []
            service_prices = []
            services_count = 0
            total_cost_of_services = 0
            total_discount_of_services = 0
            total_paid_of_services = 0

            for services_related_receipt in services_related_receipts:
                all_services_in_receipts.extend(services_related_receipt.services.all())
                total_discount_of_services += services_related_receipt.discount_amt
                for payment in services_related_receipt.payments.all():
                    total_paid_of_services += payment.paid_amount

            for service in all_services_in_receipts:
                services_count += 1
                service_snos.append(services_count)

                if service.status_id.name =='Cancelled':
                    service_names.append(f"{service.name} (Cancelled)")
                    service_prices.append(f"0.00")
                else:
                    total_cost_of_services+=service.price
                    service_names.append(f"{service.name}")
                    service_prices.append(f"{service.price}")

            net_amount_of_services = total_cost_of_services - total_discount_of_services
            total_due_of_services = total_cost_of_services - total_discount_of_services - total_paid_of_services

            package_snos = []
            package_names = []
            package_prices = []
            packages_count = 0
            total_cost_of_packages = 0
            total_discount_of_packages = 0
            total_paid_of_packages = 0

            for packages_related_receipt in packages_related_receipts:
                all_packages_in_receipts.extend(packages_related_receipt.packages.all())
                total_discount_of_packages += packages_related_receipt.discount_amt
                for payment in packages_related_receipt.payments.all():
                    total_paid_of_packages += payment.paid_amount

            for package in all_packages_in_receipts:
                packages_count += 1
                package_snos.append(packages_count)

                if package.is_package_cancelled:
                    package_names.append(f"{package.name} (Cancelled)")
                    package_prices.append(f"0.00")
                else:
                    total_cost_of_packages+=package.price
                    package_names.append(f"{package.name}")
                    package_prices.append(f"{package.offer_price}")

            net_amount_of_packages = total_cost_of_packages - total_discount_of_packages
            total_due_of_packages = total_cost_of_packages - total_discount_of_packages - total_paid_of_packages

        except Exception as error:
            return Response(f"Error fetching details: {error}", status=400)

        search_pattern = r"\{(.*?)\}"
        expression_pattern = r"\[\[(.*?)\]\]"

        # Function to replace tags found by regex search
        def replace_tag(match):
            tag_name = match.group(1)  # Capture the content without braces

            try:
                # Fetch the tag by its name
                tag = Tag.objects.get(tag_name='{' + tag_name + '}')

                # Check if the tag requires fetching a collection of items
                if tag.is_collection:
                    if tag_name == 'TestSNo':
                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in test_snos)

                    if tag_name == "TestNames":
                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in test_names)

                    if tag_name == "TestPrices":
                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in test_prices)

                    if tag_name == "TestsTotalPrice":
                        return str(total_cost_of_tests)

                    if tag_name == "TestsTotalDisc":
                        return str(total_discount_of_tests)

                    if tag_name == "HideTestsTotalDisc":
                        return str(total_discount_of_tests) if total_discount_of_tests else ""

                    if tag_name == "TestsNetAmt":
                        return str(net_amount_of_tests)

                    if tag_name == "HideTestsNetAmt":
                        return str(net_amount_of_tests) if net_amount_of_tests else ""

                    if tag_name == "TestsPaidAmt":
                        return str(total_paid_of_tests)

                    if tag_name == "TestsDueAmt":
                        return str(total_due_of_tests)


                    if tag_name == 'ConsSNo':
                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in consultation_snos)

                    if tag_name == "ConsultationNames":
                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in consultation_names)

                    if tag_name == "ConsPrices":
                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in consultation_prices)

                    if tag_name == "ConsTotalPrice":
                        return str(total_cost_of_consultations)

                    if tag_name == "ConsTotalDisc":
                        return str(total_discount_of_consultations)

                    if tag_name == "HideConsTotalDisc":
                        return str(total_discount_of_consultations) if total_discount_of_consultations else ""

                    if tag_name == "ConsNetAmt":
                        return str(net_amount_of_consultations)

                    if tag_name == "HideConsNetAmt":
                        return str(net_amount_of_consultations) if net_amount_of_consultations else ""

                    if tag_name == "ConsPaidAmt":
                        return str(total_paid_of_consultations)

                    if tag_name == "ConsDueAmt":
                        return str(total_due_of_consultations)


                    if tag_name == 'ServSNo':
                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in service_snos)

                    if tag_name == "ServiceNames":
                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in service_names)

                    if tag_name == "ServicePrices":
                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in service_prices)

                    if tag_name == "ServTotalPrice":
                        return str(total_cost_of_services)

                    if tag_name == "ServTotalDisc":
                        return str(total_discount_of_services)

                    if tag_name == "HideServTotalDisc":
                        return str(total_discount_of_services) if total_discount_of_services else ""

                    if tag_name == "ServNetAmt":
                        return str(net_amount_of_services)

                    if tag_name == "HideServNetAmt":
                        return str(net_amount_of_services) if net_amount_of_services else ""

                    if tag_name == "ServPaidAmt":
                        return str(total_paid_of_services)

                    if tag_name == "ServDueAmt":
                        return str(total_due_of_services)


                    if tag_name == 'RoomSNo':
                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in room_snos)

                    if tag_name == "RoomNames":
                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in room_names)

                    if tag_name == "RoomPrices":
                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in room_prices)

                    if tag_name == "RoomsTotalPrice":
                        return str(total_cost_of_rooms)

                    if tag_name == "RoomsTotalDisc":
                        return str(total_discount_of_rooms)

                    if tag_name == "HideRoomsTotalDisc":
                        return str(total_discount_of_rooms) if total_discount_of_rooms else ""

                    if tag_name == "RoomsNetAmt":
                        return str(net_amount_of_rooms)

                    if tag_name == "HideRoomsNetAmt":
                        return str(net_amount_of_rooms) if net_amount_of_rooms else ""

                    if tag_name == "RoomsPaidAmt":
                        return str(total_paid_of_rooms)

                    if tag_name == "RoomsDueAmt":
                        return str(total_due_of_rooms)


                    if tag_name == 'PkgSNo':
                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in package_snos)

                    if tag_name == "PkgNames":
                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in package_names)

                    if tag_name == "PkgPrices":
                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in package_prices)

                    if tag_name == "PkgsTotalPrice":
                        return str(total_cost_of_packages)

                    if tag_name == "PkgsTotalDisc":
                        return str(total_discount_of_packages)

                    if tag_name == "HidePkgsTotalDisc":
                        return str(total_discount_of_packages) if total_discount_of_packages else ""

                    if tag_name == "PkgsNetAmt":
                        return str(net_amount_of_packages)

                    if tag_name == "HidePkgsNetAmt":
                        return str(net_amount_of_packages) if net_amount_of_packages else ""

                    if tag_name == "PkgsPaidAmt":
                        return str(total_paid_of_packages)

                    if tag_name == "PkgsDueAmt":
                        return str(total_due_of_packages)

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
                # If the tag doesn't exist, return a placeholder indicating so
                return f"{tag_name} not found!"


        template_content = template.data
        intermediate_content = re.sub(search_pattern, replace_tag, template_content)
        final_content = re.sub(expression_pattern,  lambda match: evaluate_expression(match=match, details=details), intermediate_content)

        # Header
        template_header_content = template.header if template.header else ""
        intermediate_header_content = re.sub(search_pattern, replace_tag, template_header_content)
        final_header_content = re.sub(expression_pattern,  lambda match: evaluate_expression(match=match, details=details), intermediate_header_content)

        letterhead_settings = details['letterhead_settings']

        # Footer
        template_footer_content = template.footer if template.footer else ""
        intermediate_footer_content = re.sub(search_pattern, replace_tag, template_footer_content)
        final_footer_content = re.sub(expression_pattern,  lambda match: evaluate_expression(match=match, details=details), intermediate_footer_content)

        final_content = f'<div style="font-family:{letterhead_settings.default_font.value}">{final_content}</div>'
        pdf_file = HTML(string=final_content).write_pdf()
        pdf_base64 = f"data:application/pdf;base64,{base64.b64encode(pdf_file).decode('utf-8')}"

        return Response({
                         'html_content': final_content,
                         "pdf_base64": pdf_base64,
                         "header": final_header_content,
                         "footer": final_footer_content})

        # return HttpResponse(final_header_content+final_content+final_footer_content)



class BulkPaymentsWithGenerateReceiptView(APIView):
    def post(self, request):
        try:
            receipt_data = request.data

            serializer = GenerateReceiptSerializer(data=receipt_data, many=True)

            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)


class GenerateReceiptViewset(viewsets.ModelViewSet):
    queryset = LabPatientReceipts.objects.all()
    serializer_class = GenerateReceiptSerializer

    def list(self, request, *args, **kwargs):
        return Response({'Status': 'Get is not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def create(self, request=None, patient=None, remarks=None, discount_type=None, payment_for=None,
               discount_amt=None, client_id=None, created_by=None, payments=None, is_discount_amt_by_ref_doc=None,
               *args, **kwargs):
        if request:

            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            validated_data = serializer.validated_data

            patient = validated_data.get('patient')
            remarks = validated_data.get('remarks')
            discount_type = validated_data.get('discount_type')
            discount_amt = validated_data.get('discount_amt')
            created_by = validated_data.get('created_by')
            is_discount_amt_by_ref_doc = validated_data.get('is_discount_amt_by_ref_doc', False)
            client_id = validated_data.pop('client_id', None)
            payments = validated_data.pop('payments', None)
            payment_for = validated_data.pop('payment_for', None)

        else:
            print(
                f"This data is from kwargs: {patient}, {remarks},{discount_type},{discount_amt},{created_by},{is_discount_amt_by_ref_doc}, {payment_for}")

        if discount_type and discount_amt:
            return Response(
                {"Error": 'Only one or none of the parameters should be given - discount_type, discount_amt'},
                status=status.HTTP_400_BAD_REQUEST)

        else:
            if patient:
                try:
                    discount = 0
                    paid_amount = 0
                    for payment in payments:
                        paid_amount += payment['paid_amount']

                    invoiceid = LabPatientInvoice.objects.get(patient=patient)

                    if discount_amt:
                        discount = discount_amt
                    elif discount_type:
                        if discount_type.is_percentage:
                            discount = invoiceid.total_due * (discount_type.number / 100)
                        elif not discount_type.is_percentage:
                            discount = discount_type.number

                    if (invoiceid.total_due - discount) >= paid_amount:
                        before_payment_due = invoiceid.total_due
                        after_payment_due = before_payment_due - paid_amount - discount
                        receipt = LabPatientReceipts.objects.create(patient=patient, invoiceid=invoiceid,
                                                                    discount_type=discount_type, remarks=remarks,
                                                                    discount_amt=discount, payment_for=payment_for,
                                                                    before_payment_due=before_payment_due,
                                                                    after_payment_due=after_payment_due,
                                                                    is_discount_amt_by_ref_doc=is_discount_amt_by_ref_doc,
                                                                    created_by=created_by)

                        for payment in payments:
                            payment_instance = LabPatientPayments.objects.create(
                                paid_amount=payment['paid_amount'],
                                pay_mode=payment['pay_mode']
                            )

                            receipt.payments.add(payment_instance)

                        if discount:
                            if is_discount_amt_by_ref_doc:
                                invoiceid.total_ref_discount += discount
                            else:
                                invoiceid.total_lab_discount += discount

                            try:
                                if receipt.payment_for.name == 'Lab Tests':
                                    all_tests_list = LabPatientTests.objects.filter(patient=patient).exclude(status_id__name="Cancelled")
                                    for test in all_tests_list:
                                        total_tests_cost = sum(test.price for test in all_tests_list)
                                        test.discount = (test.price / total_tests_cost) * discount
                                        test.save()

                            except Exception as error:
                                print(error)

                        # Amount_due
                        invoiceid.total_discount += discount
                        invoiceid.total_price -= discount
                        invoiceid.total_paid += paid_amount
                        invoiceid.total_due = invoiceid.total_due-paid_amount-discount
                        invoiceid.save()

                        try:
                            patient_receipt = GeneratePatientReceiptViewSet()

                            patient_receipt = patient_receipt.create(patient_id=patient.id, client_id=client_id,
                                                                     receipt_id=receipt.id,
                                                                     printed_by_id=receipt.created_by.id)
                            return patient_receipt
                            # return HttpResponse(final_header_content+final_content+final_footer_content)
                        except Exception as error:
                            return Response(f"Error fetching details: {error}", status=400)

                    else:
                        print(f"'Error': 'Payment more than due amount is not allowed!")
                        return Response({"Error": "Payment more than due amount is not allowed!"},
                                        status=status.HTTP_400_BAD_REQUEST)

                except Exception as error:
                    return Response(f"'Error': '{error}'", status=status.HTTP_400_BAD_REQUEST)
            else:
                print(f"'Error': 'One of Mandatory parameters missing - patient")
                return Response({"Error": "One of Mandatory parameters missing - patient"},
                                status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            payments = request.data.get('payments')
            for payment in payments:
                payment_obj = LabPatientPayments.objects.get(pk=payment['id'])
                before_value = payment_obj.pay_mode
                after_value = ULabPaymentModeType.objects.get(pk=payment['pay_mode'])
                payment_obj.pay_mode = after_value
                payment_obj.save()

                patient = instance.patient
                client = patient.client
                user = request.user
                lab_staff = LabStaff.objects.get(mobile_number=user.phone_number)

                try:
                    activity_log = ActivityLogs.objects.create(
                        user=user,
                        lab_staff=lab_staff,
                        client=client,
                        patient=patient,
                        operation="PUT",
                        url="lab/generate_receipt",
                        model="LabPatientReceipts",
                        activity=f"Receipt {instance.Receipt_id} modified for Patient {instance.patient.name} by {lab_staff.name if lab_staff else None} on {instance.added_on.strftime('%d-%m-%y %I:%M %p')}",
                        model_instance_id=instance.id,
                        response_code=200,
                        duration="",
                    )

                    if before_value != after_value:
                        change = ChangesInModels.objects.create(field_name='Payment Type',
                                                                before_value=before_value.name,
                                                                after_value=after_value.name)
                        activity_log.changes.add(change)

                except Exception as error:
                    print(error)
                    return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"Status": "Payment Type Updated Successfully!"})

        except Exception as error:
            print(error)
            return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)


def generate_test_report_content(test_id=None):
    test = LabPatientTests.objects.get(pk=test_id)
    patient_id = test.patient.id
    client_id = test.patient.client.id

    generate_test_report_content = GenerateTestReportViewset()
    response = generate_test_report_content.create(test_id=test_id, client_id=client_id)
    header = response.data.get('header')
    signature_content = response.data.get('signature_content')

    if not header:
        header = ""

    if not signature_content:
        signature_content = None

    return header, signature_content


def return_word_report_header():
    template_type = PrintTemplateType.objects.get(name='Lab Test Report (Word)')

    print_template = PrintTemplate.objects.filter(print_template_type=template_type, is_default=True).first()

    template = PrintDataTemplate.objects.get(print_template=print_template)

    header = template.header

    return header


def get_value_from_parameter_value(parameter_value):
    if parameter_value.lower().startswith('select**'):
        match = re.match(r'^select\*\*(.*?)\*\*', parameter_value)
        if match:
            extracted_value = match.group(1)
            print(f'Extracted value: {extracted_value}')
            return extracted_value

    return parameter_value


def get_value_of_tag(tag_name=None, lab_patient_test=None, client_report_settings=None):
    if tag_name == "LabTestParameterHeadings":
        related_objects = LabPatientFixedReportTemplate.objects.filter(
            LabPatientTestID=lab_patient_test)
        if all(obj.is_value_only for obj in related_objects):
            report_heading = f'''
                                 <tr class="fixedHead" style="font-size:14px;border-top:0.5px solid black; border-bottom:0.5px solid black; border-left:none; border-right:none;">
                                     <th style=" text-align:left;padding:2px 5px;border:none; width:40%">Test Name</th>
                                     <th style="text-align:left; padding:2px 5px;border:none; width:60%">Result</th>
                                 </tr>
                                 '''
        else:
            report_heading = f'''
                                 <tr class="fixedHead" style="font-size:14px;border-top:0.5px solid black; border-bottom:0.5px solid black; border-left:none; border-right:none;">
                                     <th style=" text-align:left;padding:2px 5px;border:none; width:40%">Test Name</th>
                                     <th style="text-align:left;padding:2px 5px;border:none; width:15%">Result</th>
                                     <th style="text-align:left; padding:2px 5px;border:none;width:15%">Unit</th>
                                     <th style="text-align:left; padding:2px 5px;border:none; width:30%">Bio.Ref.Range</th>
                                 </tr>
                                 '''
        content = f'''
                     <table class="labTestParameterHeadings" cellspacing="0" style="border-collapse:collapse; margin-top:1px; width:100%">
                        <tbody>
                           <tr class="fixedDepartmentHead" style="border-top:0.5px solid black;border-bottom:0.5px solid black; border-left:none; border-right:none;">
                                <td colspan="4" style="text-align:center;font-size:16px;padding:5px;font-weight:600;">DEPARTMENT OF {lab_patient_test.department.name.upper()} </td>
                            </tr>
                            {report_heading}
                            <tr class="fixedTestHead" style="">
                                <td colspan="4" style="text-align:left;font-size:14px;padding:5px;">{lab_patient_test.name.upper()} </td>
                            </tr>
                        </tbody>
                    </table>
                    '''
        return content
    
    if tag_name == "LabTestGroups":
        related_objects = LabPatientFixedReportTemplate.objects.filter(
            LabPatientTestID=lab_patient_test).order_by('ordering')

        groups = related_objects.values_list('group', flat=True).distinct()
        groups_content = ""
        group = ""

        for data in related_objects:
            data_value = get_value_from_parameter_value(data.value)
            if not data_value:
                continue
            if not data.template.to_display:
                continue

            if group != data.group:
                group = data.group
                if group != "":
                    groups_content += f'''<tr>
                                            <td colspan="4" style="font-size:14px; padding: 5px;"></td>
                                          </tr>
                                          <tr class="fixedGroupName">
                                            <td colspan="4" style="font-size:14px; padding: 5px;"><strong>{group}</strong></td>
                                          </tr>
                                        '''

                else:
                    groups_content += f'''<tr class="noFixedGroupName">
                                            <td colspan="4" style="font-size:14px;padding: 5px;"></td>
                                          </tr>
                                        '''


            # Check if units or referral range exist and construct data content accordingly
            if data.units or data.referral_range:
                if data.is_value_only:
                    data_content =  f'''
                                        <tr class="parameterRows" style="font-size:12px;">
                                            <td class="parameterName" style="text-align:left;width:40%;padding: 5px; ">{data.parameter}</td>
                                            <td class="parameterResult" colspan="4" style="text-align:left; padding:5px;">
                                            <span>{'<b> ' + data_value + '*</b>' if data.is_value_bold else data_value}</span></td>
                                        </tr>

                                        '''

                else:
                    data_content = f'''
                                    <tr class="parameterRows" style="font-size:12px;">
                                        <td style="text-align:left;padding: 5px; vertical-align:top; width:40%;">
                                            <div style="display: flex; flex-direction: column;">
                                                <span class="parameterName">{data.parameter}</span>
                                                <span class="parameterMethod"><i>{'(Method : ' + data.method + ')' if data.method else ""}</i></span>
                                            </div>
                                        </td>
                                        <td class="parameterResult" style="text-align:left; vertical-align:top; min-height:10px;padding: 5px; width:15%;">
                                            <span>{'<strong><strong>' + data_value + '*</strong></strong>' if data.is_value_bold else data_value}</span>
                                        </td>
                                        <td class="parameterUnits" style="text-align:left; vertical-align:top; width:15%;padding: 5px;">{data.units}</td>
                                        <td class="parameterRefRanges" style="text-align:left; vertical-align:top; width:30%;padding: 5px;">{data.referral_range.replace("\n", "<br>")}</td>
                                    </tr>

                                    '''

            else:
                data_content = f'''
                                <tr class="parameterRows" style="font-size:12px;">
                                    <td class="parameterName" style="text-align:left;width:40%;padding: 5px;">{data.parameter}</td>
                                    <td class="parameterResult" colspan="4" style="text-align:left;padding: 5px;">
                                        <span>{'<b> ' + data_value + '*</b>' if data.is_value_bold else data_value}</span>
                                    </td>
                                </tr>

                                '''

            if data.value:
                groups_content += data_content

        groups_content = f'''
                        <table  border="0" cellspacing="0" style="width:100%;border-collapse:collapse;">
                            <tbody>
                                {groups_content}
                            </tbody>
                        </table>

                        '''
        return groups_content

    if tag_name == "LabTestDeptHeading":
        tag_value = f'''
                        <tr class="fixedDepartmentHead" style="border-top:0.5px solid black;border-bottom:0.5px solid black; border-left:none; border-right:none;">
                            <td colspan="4" style="font-size:{client_report_settings.dept_name_size}px;text-align:{client_report_settings.dept_name_alignment};padding:5px;font-weight:{client_report_settings.dept_name_weight};">DEPARTMENT OF {lab_patient_test.department.name.upper()} </td>
                        </tr>
                    
                    '''
        return tag_value

    if tag_name == "LabTestDisplayName":
        if lab_patient_test.display_name:
            tag_value = f'''
                            <tr class="fixedTestHead" style="">
                                <td colspan="4" 
                                    style="
                                    font-size:{client_report_settings.test_name_size}px;
                                    text-align:{client_report_settings.test_name_alignment};
                                    padding:5px;font-weight:{client_report_settings.test_name_weight};">
                                        <u>{lab_patient_test.display_name.upper()}</u>
                                </td>
                            </tr>
                            
                        '''
        else:
            tag_value = ""
        return tag_value

    if tag_name == "LabTestNormalName":
        tag_value = f'''
                        <tr class="fixedTestHead" style="">
                            <td colspan="4" style="font-size:{client_report_settings.test_name_size}px;text-align:{client_report_settings.test_name_alignment};padding:5px;font-weight:{client_report_settings.test_name_weight};">{lab_patient_test.name.upper()} </td>
                        </tr>
                        
                    '''
        return tag_value

    if tag_name == 'LabReportHeading':
        related_objects = LabPatientFixedReportTemplate.objects.filter(LabPatientTestID=lab_patient_test)
        if all(obj.is_value_only for obj in related_objects):
            tag_value = f'''
                          <tr class="fixedHead" style="font-weight:{client_report_settings.report_head_weight};font-size:{client_report_settings.report_head_size}px;border-top:0.5px solid black;border-bottom:0.5px solid black; border-left:none; border-right:none;">
                              <td style="text-align:left;padding:2px 5px;border:none; width:40%">{client_report_settings.test_display_name}</td>
                              <td style="text-align:left; padding:2px 5px;border:none; width:60%">{client_report_settings.result_display_name}</td>
                          </tr>
                          
                          '''
        else:
            tag_value = f'''
                          <tr class="fixedHead" style="font-weight:{client_report_settings.report_head_weight};font-size:{client_report_settings.report_head_size}px;border-top:0.5px solid black;border-bottom:0.5px solid black; border-left:none; border-right:none;">
                              <td style=" text-align:left;padding:2px 5px;border:none; width:40%">{client_report_settings.test_display_name}</td>
                              <td style="text-align:left;padding:2px 5px;border:none; width:15%">{client_report_settings.result_display_name}</td>
                              <td style="text-align:left; padding:2px 5px;border:none;width:15%">{client_report_settings.unit_display_name}</td>
                              <td style="text-align:left; padding:2px 5px;border:none; width:30%">{client_report_settings.ref_ranges_display_name}</td>
                          </tr>
                          
                          '''

        return tag_value

    if tag_name == "LabTestReportGroups":
        related_objects = LabPatientFixedReportTemplate.objects.filter(LabPatientTestID=lab_patient_test).order_by('ordering')

        groups = related_objects.values_list('group', flat=True).distinct()
        groups_content = ""
        group = ""

        for data in related_objects:
            data_value = get_value_from_parameter_value(data.value)
            if not data_value:
                continue

            if not data.template.to_display:
                continue

            if group != data.group:
                group = data.group
                if group != "":
                    groups_content += f'''<tr class="fixedGroupNameGap">
                                            <td colspan="4" style="font-size:{client_report_settings.group_name_size}px; padding: 5px;"></td>
                                          </tr>
                                          <tr class="fixedGroupName">
                                            <td colspan="4" style="font-size:{client_report_settings.group_name_size}px; font-weight:{client_report_settings.group_name_weight};padding: 5px;">{group}</td>
                                          </tr>
                                          
                                        '''

                else:
                    groups_content += f'''<tr class="noFixedGroupName">
                                            <td colspan="4" style="font-size:{client_report_settings.group_name_size}px;padding: 5px;"> </td>
                                          </tr>
                                          
                                        '''


            # Check if units or referral range exist and construct data content accordingly
            data_value_content = f"<strong>{data_value}*</strong>" if data.is_value_bold else data_value
            if data.units or data.referral_range:
                if data.is_value_only:
                    data_content =  f'''
                                        <tr class="parameterRows" style="">
                                            <td class="parameterName" style="text-align:left; font-size:{client_report_settings.parameter_size}px; font-weight:{client_report_settings.parameter_weight};width:40%;padding: 5px;">{data.parameter}</td>
                                            <td class="parameterResult" colspan="4" style="text-align:left; font-size:{client_report_settings.result_size}px; padding:5px;">{data_value_content}</td>
                                        </tr>

                                        '''

                else:
                    method_content = f"({client_report_settings.method_display_name} {data.method})" if data.method else ""
                    method_content= f"<i>{method_content}</i>" if client_report_settings.method_is_italic else method_content

                    data_content = f'''
                                    <tr class="parameterRows" style="">
                                        <td style="text-align:left;padding: 5px; vertical-align:top; width:40%;">
                                            <div style="display: flex; flex-direction: column;">
                                                <span class="parameterName" style="font-size:{client_report_settings.parameter_size}px;font-weight:{client_report_settings.parameter_weight}">{data.parameter}</span>
                                                <span class="parameterMethod" style="font-size:{client_report_settings.method_size}px;font-weight:{client_report_settings.method_weight}">{method_content}</span>
                                            </div>
                                        </td>
                                        <td class="parameterResult" style="font-size:{client_report_settings.result_size}px; text-align:left; vertical-align:top; min-height:10px; padding: 5px; width:15%;">{data_value_content}</td>
                                        <td class="parameterUnits" style="font-size:{client_report_settings.unit_size}px;font-weight:{client_report_settings.unit_weight}; text-align:left; vertical-align:top; width:15%;padding: 5px;">{data.units}</td>
                                        <td class="parameterRefRanges" style="font-size:{client_report_settings.ref_range_size}px;font-weight:{client_report_settings.ref_range_weight}; text-align:left; vertical-align:top; width:30%;padding: 5px;">{data.referral_range.replace("\n", "<br>")}</td>
                                    </tr>

                                    '''

            else:
                data_content = f'''
                                <tr class="parameterRows" style="">
                                    <td class="parameterName" style="font-size:{client_report_settings.parameter_size}px; font-weight:{client_report_settings.parameter_weight};text-align:left;width:40%;padding: 5px;">{data.parameter}</td>
                                    <td class="parameterResult" colspan="4" style="font-size:{client_report_settings.result_size}px; text-align:left;padding: 5px;">{data_value_content}</td>
                                </tr>

                                '''

            groups_content += data_content

        return groups_content

    if tag_name =='LabTestTechnicianRemarks':
        lab_technician_remarks = LabTechnicianRemarks.objects.filter(
            LabPatientTestID=lab_patient_test).first() if lab_patient_test else None

        if lab_technician_remarks:
            lab_technician_remarks = lab_technician_remarks.remark if lab_technician_remarks.remark else ""

            if lab_technician_remarks:
                tag_value = f'''
                              <tr class="fixedReportTechnicianRemarks" style="">
                                  <td colspan="4">{lab_technician_remarks}</td>
                              </tr>
        
                              '''
                return tag_value
        return ""

    if tag_name == 'Space':
        value = f'''
                <tr>
                    <td class="spacingContent" style="height:16px;"></td>
                </tr>
                  
                '''
        return value




def get_age_details(patient):
    age = patient.age
    age_units = patient.ULabPatientAge.name

    if age_units == "DOB":
        birth_date = patient.dob
        current_date = datetime.now().date()

        # Calculate the difference between current date and birth date
        delta = relativedelta(current_date, birth_date)
        print(delta, delta.days, delta.months, delta.years)

        # Determine the most appropriate unit to return
        if delta.years > 0:
            return f"{delta.years} Years"
        elif delta.months > 0:
            return f"{delta.months} Months"
        else:
            return f"{delta.days} Days"
    return f"{age} {age_units}"


def get_age_details_in_short_form(patient):
    age = patient.age
    age_units = patient.ULabPatientAge.name

    if age_units == "DOB":
        birth_date = patient.dob
        current_date = datetime.now().date()

        # Calculate the difference between current date and birth date
        delta = relativedelta(current_date, birth_date)

        # Determine the most appropriate unit to return
        if delta.years > 0:
            return f"{delta.years} Y"
        elif delta.months > 0:
            return f"{delta.months} M"
        else:
            return f"{delta.days} D"

    return f"{age} {age_units[:1]}"


def get_param_value(parameter=None, lab_patient_test=None):
    report = LabPatientFixedReportTemplate.objects.filter(LabPatientTestID=lab_patient_test,
                                                          parameter=parameter).first()
    if report:
        value = report.value
        if value.lower().startswith('select**'):
            match = re.match(r'^select\*\*(.*?)\*\*', value, re.IGNORECASE)
            if match:
                extracted_value = match.group(1)
                return extracted_value
        return value



def get_lab_patient_details(test_id=None, patient_id=None, client_id=None, printed_by_id=None, receipt_id=None):
    print(test_id, 'test_id', client_id, 'client_id', printed_by_id, 'patient_id', patient_id)
    try:
        lab_patient_test, lab_phlebotomist, lab_technician, template, template_type, is_word_report = None, None, None, None, None, None
        if test_id:
            try:
                lab_patient_test = LabPatientTests.objects.get(pk=test_id)
                patient = lab_patient_test.patient
                mobile_number = patient.mobile_number
                lab_phlebotomist = LabPhlebotomist.objects.filter(LabPatientTestID=lab_patient_test).first()
                lab_technician = LabTechnicians.objects.filter(LabPatientTestID=lab_patient_test).first()
                is_word_report = lab_technician.is_word_report if lab_technician is not None else False

                if is_word_report:
                    template_type = PrintTemplateType.objects.get(name='Lab Test Report (Word)')
                else:
                    if lab_patient_test.department.name == "Medical Examination":
                        template_type = PrintTemplateType.objects.get(name='Medical Examination Report')
                    else:
                        template_type = PrintTemplateType.objects.get(name='Lab Test Report (Fixed)')

                print_template = PrintTemplate.objects.filter(print_template_type=template_type,
                                                              is_default=True).first()
                template = PrintDataTemplate.objects.get(print_template=print_template)

            except LabPatientTests.DoesNotExist:
                print(f"LabPatientTests matching query does not exist for test_id: {test_id}")
                return None
        else:
            try:
                patient = Patient.objects.get(pk=patient_id)
            except Patient.DoesNotExist:
                print(f"Patient matching query does not exist for patient_id: {patient_id}")
                return None
        client = Client.objects.get(pk=client_id)
        bProfile = BusinessProfiles.objects.get(organization_name=client.name)
        b_address = BusinessAddresses.objects.filter(b_id=bProfile.id).first()
        letterhead_settings = LetterHeadSettings.objects.filter(client=client).first()
        background_image_url = bProfile.b_letterhead if letterhead_settings.display_letterhead else ""
        appointment_details = AppointmentDetails.objects.filter(patient=patient).first()
        contacts = BContacts.objects.filter(b_id=bProfile, is_primary=True).first()
        labpatientinvoice = LabPatientInvoice.objects.filter(patient=patient).first()
        labpatientpackages = LabPatientPackages.objects.filter(patient=patient).first()
        receipt = LabPatientReceipts.objects.filter(invoiceid=labpatientinvoice).first()
        Signature_template_type = PrintTemplateType.objects.get(name='Signature on Reports')
        signature_print_template = PrintTemplate.objects.filter(print_template_type=Signature_template_type,
                                                                is_default=True).first()
        signature_template = PrintDataTemplate.objects.filter(print_template=signature_print_template).first()

        signature_content = signature_template.data if signature_template else ""

        client_report_settings = ReportFontSizes.objects.first()


        if receipt_id:
            try:
                receipt = LabPatientReceipts.objects.get(pk=receipt_id)
                template_type = PrintTemplateType.objects.get(name='Receipt')
                print_template = PrintTemplate.objects.get(print_template_type=template_type, is_default=True)
                template = PrintDataTemplate.objects.get(print_template=print_template)

            except LabPatientReceipts.DoesNotExist:
                print(f"Receipt matching query does not exist for receipt_id: {receipt_id}")
                return None
        elif not receipt_id and not test_id:
            template_type = PrintTemplateType.objects.get(name='Receipt')
            print_template = PrintTemplate.objects.get(print_template_type=template_type, is_default=True)
            template = PrintDataTemplate.objects.get(print_template=print_template)

        created_by = patient.created_by
        invoice_barcode_img = generate_barcode_image(labpatientinvoice.id) if labpatientinvoice else None
        receipt_barcode_img = generate_barcode_image(receipt.id) if receipt else None
        mr_no_barcode_img = generate_barcode_image(patient.mr_no) if patient else None
        visit_id_barcode_img = generate_barcode_image(patient.visit_id) if patient else None
        paid_amount_of_receipt = sum(payment.paid_amount for payment in receipt.payments.all())
        paid_amount_in_words = f"{num2words(paid_amount_of_receipt, lang='en_IN').title()} rupees only"
        qr_alignments = PrintReportSettings.objects.first()
        invoice_barcode_img = (
            f'<img class="invoiceBarcode" alt ="invoice_barcode_img" src ="{invoice_barcode_img}" style="height:30px; min-width:100px;'
            f'padding:0 10px 0 0"/>') if invoice_barcode_img else ""

        receipt_barcode_img = (
            f'<img class="receiptBarcode" alt ="invoice_barcode_img" src ="{receipt_barcode_img}" style="height:30px; min-width:100px;' f'padding:0 10px 0 0"/>') if receipt_barcode_img else ""

        sample_barcode_image = generate_barcode_image(
            f"{lab_phlebotomist.assession_number}|{lab_patient_test.department.name}") if lab_phlebotomist else None

        sample_barcode_img = (
            f'<img class="sampleBarcode" alt ="barcode_img" src ="{sample_barcode_image}" style="height:{qr_alignments.test_barcode_height}px; min-width: {qr_alignments.test_barcode_width}px; '
            f'padding:0 10px 0 0"/>') if sample_barcode_image else ""

        vertical_sample_barcode_img = (
            f'<img class="verticalSampleBarcode" alt="barcode_img" src="{sample_barcode_image}"  style="height:{qr_alignments.test_barcode_height}px; min-width: {qr_alignments.test_barcode_width}px; '
            f'padding:0 10px 0 0; transform:rotate(90deg)"/>') if sample_barcode_image else ""

        mr_no_barcode_img = (
            f'<img class="mrNoBarcode" alt ="mr_no_barcode_img" src ="{mr_no_barcode_img}" style="height:30px; min-width:100px;' f'padding:0 10px 0 0"/>') if mr_no_barcode_img else ""

        visit_id_barcode_img = (
            f'<img class="visitIdBarcode" alt ="mr_no_barcode_img" src ="{visit_id_barcode_img}" style="height:30px; min-width:100px;' f'padding:0 10px 0 0"/>') if visit_id_barcode_img else ""

        printed_by = LabStaff.objects.get(pk=printed_by_id) if printed_by_id else ""
        branch_address = get_branch_address_of_lab_staff(lab_staff=printed_by) if printed_by else ""
        hashed_test_id = encode_id(test_id) if test_id else ""
        hashed_client_id = encode_id(client_id)
        mobile_number = patient.mobile_number
        hashed_mobile_number = encode_id(mobile_number)

        domain_obj = Domain.objects.first()
        domain_url = domain_obj.url

        qr_data = f"{domain_url}/patient_report/?t={hashed_test_id}&c={hashed_client_id}&m={hashed_mobile_number}"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=0
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
        # img = qr.make_image(fill='black', back_color='white')
        qr_buffer = BytesIO()
        img.save(qr_buffer, format='PNG')
        qr_base64 = base64.b64encode(qr_buffer.getvalue()).decode()
        qrcode_img = f"data:image/png;base64,{qr_base64}"
        qrcode_img = (
            f'<img alt ="qrcode_img" src ="{qrcode_img}" style="height:{qr_alignments.qr_code_size}px; width:{qr_alignments.qr_code_size}px;"/>') if qrcode_img else "NA"

        lab_technician_sign = None
        consulting_doctor_sign = None

        if lab_technician:
            lab_technician_sign = lab_technician.report_created_by.signature if lab_technician.report_created_by else None
            consulting_doctor_sign = lab_technician.consulting_doctor.signature_for_consulting if lab_technician.consulting_doctor else None

        lab_technician_sign = (
            f'<img class="labTechnicianSign" alt ="lab_technician_sign" src ="{lab_technician_sign}" style="height:30px; min-width:100px; '
            f'padding:0 10px 0 0"/>') if lab_technician_sign else ""

        consulting_doctor_sign = (
            f'<img class="consultingDoctorSign" alt ="consulting_doctor_sign" src ="{consulting_doctor_sign}" style="height:30px; '
            f'min-width:100px;'
            f'padding:0 10px 0 0"/>') if consulting_doctor_sign else ""

        lab_technician_remarks = LabTechnicianRemarks.objects.filter(
            LabPatientTestID=lab_patient_test).first() if lab_patient_test else None

        if lab_technician_remarks:
            lab_technician_remarks = lab_technician_remarks.remark if lab_technician_remarks.remark else ""

        try:
            word_report = LabPatientWordReportTemplate.objects.filter(
                LabPatientTestID=lab_patient_test).first() if lab_patient_test else None
        except Exception as error:
            word_report = None

        word_report_content = word_report.report if word_report else ''

        test_report_date = ''

        report_printed_on = datetime.now().strftime('%d-%m-%y %I:%M %p')

        default_consulting_doctor = None
        default_technician = None
        default_consulting_doctor_name = ""
        default_technician_name = ""
        default_consulting_doctor_sign = ""
        default_technician_sign = ""

        try:
            if lab_patient_test:
                defaults_obj = DefaultsForDepartments.objects.filter(department=lab_patient_test.department).first()

                if defaults_obj:
                    default_consulting_doctor = defaults_obj.doctor if defaults_obj.doctor else ""
                    default_technician = defaults_obj.lab_technician if defaults_obj.lab_technician else ""

                    if default_consulting_doctor:
                        default_consulting_doctor_name = default_consulting_doctor.name
                        default_consulting_doctor_sign_content = default_consulting_doctor.signature_for_consulting

                        default_consulting_doctor_sign = (
                            f'<img class="defconsultingDoctorSign" alt ="consulting_doctor_sign" src ="{default_consulting_doctor_sign_content}" style="height:30px; '
                            f'min-width:100px;'
                            f'padding:0 10px 0 0"/>') if default_consulting_doctor_sign_content else ""

                    if default_technician:
                        default_technician_name = default_technician.name
                        default_technician_sign_value = default_technician.signature
                        default_technician_sign = (
                            f'<img class="deflabTechnicianSign" alt ="lab_technician_sign" src ="{default_technician_sign_value}" style="height:30px; min-width:100px; '
                            f'padding:0 10px 0 0"/>') if default_technician_sign_value else ""

        except Exception as error:
            print(error)

        try:
            if lab_technician:
                if lab_technician.is_word_report:
                    report = LabPatientWordReportTemplate.objects.filter(LabPatientTestID=lab_patient_test).first()
                    test_report_date = report.added_on if report else ''
                else:
                    report = LabPatientFixedReportTemplate.objects.filter(LabPatientTestID=lab_patient_test).first()
                    test_report_date = report.added_on if report else ''
        except Exception as error:
            print(error)
            pass

        payment_status = None

        if labpatientinvoice:
            if labpatientinvoice.total_paid == 0:
                payment_status = f"<span style='color:red;'>UNPAID</span>"
            elif 0 < labpatientinvoice.total_paid < labpatientinvoice.total_due:
                payment_status = f"<span style='color:blue;'>PARTIALLY PAID</span>"
            elif labpatientinvoice.total_paid >= labpatientinvoice.total_due:
                payment_status = f"<span style='color: green;'>FULLY PAID</span>"

        details = {
            'lab_patient_test': lab_patient_test,
            'patient': patient,
            "age": get_age_details(patient),
            "age_short_form": get_age_details_in_short_form(patient),
            'bProfile': bProfile,
            'appointment_details': appointment_details,
            'contacts': contacts,
            'labpatientinvoice': labpatientinvoice,
            'receipt': receipt,
            'sample_barcode_img': sample_barcode_img,
            'vertical_sample_barcode_img': vertical_sample_barcode_img,
            "qrcode_img": qrcode_img,
            "mr_no_barcode_img": mr_no_barcode_img,
            "visit_id_barcode_img": visit_id_barcode_img,
            'is_word_report': is_word_report,
            'payment_status': payment_status,
            'lab_phlebotomist': lab_phlebotomist,
            'lab_technician': lab_technician,
            "lab_technician_remarks": lab_technician_remarks,
            'word_report_content': word_report_content,
            'test_report_date': test_report_date,
            "report_printed_on": report_printed_on,
            "lab_technician_sign": lab_technician_sign,
            "consulting_doctor_sign": consulting_doctor_sign,
            "b_letterhead": bProfile.b_letterhead,
            "printed_by": printed_by,
            'invoice_barcode_img': invoice_barcode_img,
            'receipt_barcode_img': receipt_barcode_img,
            'template': template,
            "created_by": created_by,
            "paid_amount_of_receipt": paid_amount_of_receipt,
            "paid_amount_in_words": paid_amount_in_words,
            'labpatientpackages': labpatientpackages,
            'letterhead_settings': letterhead_settings,
            'background_image_url': background_image_url,
            'b_address': b_address,
            "signature_content": signature_content,
            "default_consulting_doctor": default_consulting_doctor,
            "default_technician": default_technician,
            "default_consulting_doctor_name": default_consulting_doctor_name,
            "default_technician_name": default_technician_name,
            "default_consulting_doctor_sign": default_consulting_doctor_sign,
            "default_technician_sign": default_technician_sign,
            "branch_address":branch_address,
            "partner":"",
            "client_report_settings":client_report_settings
        }


        if lab_patient_test:
            if lab_patient_test.department.name == 'Medical Examination':
                medical_test_params = LabPatientFixedReportTemplate.objects.filter(LabPatientTestID=lab_patient_test)
                for obj in medical_test_params:
                    details[f"get_value_of_{obj.parameter}"] = get_param_value(parameter=obj.parameter, lab_patient_test=lab_patient_test)
                    details[f"{obj.parameter}"] = get_param_value(parameter=obj.parameter,
                                                                               lab_patient_test=lab_patient_test)

                details['partner']= patient.partner

        return details

    except Exception as error:
        print(f"Error occurred: {error}")



# using to remove multiple occurrences of Department heading in multiprint
def remove_duplicate_department_headings(content):
    # Regex to match the entire <tr> row containing "DEPARTMENT OF ..."
    pattern = re.compile(r'<tr[^>]*?>\s*<td[^>]*?>DEPARTMENT OF ([^<]+)</td>\s*</tr>', re.IGNORECASE)

    # Set to track seen department names
    seen_departments = set()

    # Function to replace duplicate rows
    def replace_duplicate(match):
        try:
            department_name = match.group(1).strip()  # Extract department name
            if department_name in seen_departments:
                return ''  # Remove entire duplicate row
            seen_departments.add(department_name)
            return match.group(0)  # Keep the entire row
        except Exception as error:
            print(f"Error: {error}")
            return match.group(0)  # Return the original match on error

    # Replace duplicates in the content
    result = pattern.sub(replace_duplicate, content)
    return result



# Normalize the content to remove extra spaces and newlines
def normalize_html(html):
    return re.sub(r'\s+', ' ', html).strip()


def remove_duplicate_report_headings(content=None):
    # Normalize the content (optional, if normalize_html is already defined elsewhere)
    content = normalize_html(content)

    # Define a regex pattern to match <tr> elements with the class "fixedHead"
    pattern = re.compile(r'<tr[^>]*class="fixedHead"[^>]*>.*?</tr>', re.DOTALL | re.IGNORECASE)

    # Remove all matching <tr> elements
    content = pattern.sub('', content)

    return content



def replace_tag(match=None, lab_patient_test=None,client_report_settings=None, details=None):
    tag_name = match.group(1)

    try:
        tag = Tag.objects.get(tag_name='{'+tag_name+'}')
        if tag.is_collection:
            return get_value_of_tag(tag_name=tag_name, lab_patient_test=lab_patient_test,
                                    client_report_settings=client_report_settings)
        else:
            if tag.tag_formula:
                try:
                    tag_value = str(eval(tag.tag_formula, {'details': details}))
                    return tag_value
                except Exception as eval_error:
                    print(f"{tag_name} - Error in formula evaluation: {eval_error}")
                    return " "
            else:
                print(f"No formula for {tag_name}")
                return ""
    except Tag.DoesNotExist:
        if lab_patient_test.department.name == 'Medical Examination':
            tag_value = details.get(f'{tag_name}', "")
            return tag_value

        else:
            print(f"{tag_name} not found!")
            return ""


def evaluate_expression(match=None, details=None):
    expression = match.group(1)
    try:
        result = str(eval(expression, {'__builtins__': None}, {'details': details}))
        return result
    except Exception as eval_error:
        print(f"Error in expression evaluation: {eval_error}")
        return ""



class GenerateTestReportViewset(viewsets.ModelViewSet):
    serializer_class = GenerateTestReportSerializer

    def get_queryset(self):
        return []

    def create(self, request=None, test_id=None, client_id=None, printed_by_id=None, is_report_printed=None, pdf=None,
               lh=None, download=None, *args, **kwargs):
        if request:
            test_id = self.request.query_params.get('test_id', None)
            client_id = self.request.query_params.get('client_id', None)
            printed_by_id = self.request.query_params.get('printed_by', None)
            download = self.request.query_params.get('download', 'false')

            if test_id and client_id:
                pass
            else:
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer_data = serializer.validated_data
                test_id = serializer_data.get('test_id')
                client_id = serializer_data.get('client_id')
                printed_by_id = serializer_data.get('printed_by')
                is_report_printed = serializer_data.get('is_report_printed')
                client_id = serializer_data.get('client_id')
                pdf = serializer_data.get('pdf', False)
                lh = serializer_data.get('lh', None)
                download = serializer_data.get('download', 'false')

        else:
            pass

        try:
            details = get_lab_patient_details(test_id=test_id, client_id=client_id, printed_by_id=printed_by_id)
            if details is None:
                return Response({"error": "Failed to retrieve lab patient details."}, status=400)

            lab_patient_test = details['lab_patient_test']
            template = details['template']
            is_word_report = details['is_word_report']
            letterhead_settings = details['letterhead_settings']
            medical_examination_content = ""
            client_report_settings = details['client_report_settings']

        except Exception as error:
            print(error)
            return Response(f"Error fetching details: {error}", status=400)

        # print(f"details at test report : {details}")

        search_pattern = r"\{(.*?)\}"
        expression_pattern = r"\[\[(.*?)\]\]"


        word_report = LabPatientWordReportTemplate.objects.filter(LabPatientTestID=lab_patient_test).first()
        if word_report:
            template_content = "<div>" + word_report.report + "</div>"
        else:
            template_content = template.data

        intermediate_content = re.sub(search_pattern, lambda match: replace_tag(match=match, lab_patient_test=lab_patient_test,
                                                                    client_report_settings=client_report_settings,
                                                                    details=details), template_content)

        final_content = re.sub(expression_pattern, lambda match: evaluate_expression(match=match, details=details), intermediate_content)

        signature_content = details['signature_content']
        #
        sign_intermediate_content = re.sub(search_pattern, lambda match: replace_tag(match=match, lab_patient_test=lab_patient_test,
                                                                    client_report_settings=client_report_settings,
                                                                    details=details), signature_content)
        sign_final_content = re.sub(expression_pattern, lambda match: evaluate_expression(match=match, details=details), sign_intermediate_content)

        if sign_final_content:
            sign_final_content = f'''
                                    <tr>
                                        <td colspan="4">{sign_final_content}</td>
                                    </tr>
                                        '''

        if not is_word_report and lab_patient_test.department.name != 'Medical Examination':
            final_content = final_content + sign_final_content
            # final_content = final_content + f'''
            # <tr>
            #     <td>
            #         {sign_final_content}
            #     </td>
            # </tr>
            # '''

        if lab_patient_test.department.name == 'Medical Examination':
            final_header_content = ""
            final_footer_content = ""

        else:
            # Header
            template_header_content = template.header if template.header else ""
            intermediate_header_content = re.sub(search_pattern, lambda match: replace_tag(match=match, lab_patient_test=lab_patient_test,
                                                                    client_report_settings=client_report_settings,
                                                                    details=details), template_header_content)
            final_header_content = re.sub(expression_pattern, lambda match: evaluate_expression(match=match, details=details), intermediate_header_content)


            # Footer
            template_footer_content = template.footer if template.footer else ""
            intermediate_footer_content = re.sub(search_pattern, lambda match: replace_tag(match=match, lab_patient_test=lab_patient_test,
                                                                    client_report_settings=client_report_settings,
                                                                    details=details), template_footer_content)
            final_footer_content = re.sub(expression_pattern, lambda match: evaluate_expression(match=match, details=details), intermediate_footer_content)

        base64_pdf = ""
        if pdf:
            base64_pdf = get_pdf_content(test_id, client_id, lh)

        try:
            if printed_by_id:
                technician = LabTechnicians.objects.filter(LabPatientTestID=lab_patient_test,
                                                           is_report_printed=False).last()
                if technician:
                    technician.is_report_printed = True
                    technician.save()
        except Exception as error:
            print(error)

        if lab_patient_test.department.name == "Medical Examination":
            medical_examination_content = final_content
            final_content = ""
        else:
            final_content = (f'<table style="border-collapse:collapse;width:100%; font-family:{letterhead_settings.default_font.value}">'
                             f'     <tbody>'
                             f'         {final_content}'
                             f'     </tbody>'
                             f'</table>')

        is_only_fixed=True

        try:
            is_only_fixed = False if is_word_report else True
        except Exception as error:
            pass



        # final_content = f'<div style="font-family:{letterhead_settings.default_font.value}">{final_content}</div>'
        return Response({ "fixed_report": True if not is_word_report else False,
                        'html_content': final_content,
                         "header": final_header_content,
                         "footer": final_footer_content,
                          "signature_content":sign_final_content,
                         "medical_examination_content": medical_examination_content,
                         "link_pdf": base64_pdf,
                          "is_only_fixed":is_only_fixed
                         })
        # return HttpResponse(final_content)


class StringToHTMLView(generics.ListAPIView):
    def list(self, request, *args, **kwargs):
        data = request.data.get('html_content')
        return HttpResponse(data)




class GeneratePatientTestReportViewset(viewsets.ModelViewSet):
    serializer_class = GeneratePatientTestReportSerializer

    def get_queryset(self):
        return []

    def create(self=None, request=None, patient_id=None, client_id=None, test_ids=None, printed_by_id=None,
               letterhead=None,sourcing_lab_for_settings=None,download=None, *args, **kwargs):
        if request:
            test_ids = self.request.query_params.get('test_ids', None)
            if test_ids:
                test_ids = list(map(int, test_ids.split(',')))
            client_id = self.request.query_params.get('client_id', None)
            patient_id = self.request.query_params.get('patient_id', None)
            letterhead = self.request.query_params.get('lh', None)
            download = self.request.query_params.get('download', 'false')
            sourcing_lab_for_settings = self.request.query_params.get('sourcing_lab_for_settings', None)

        else:
            download = 'false' if download is None else download
            pass

        patient = Patient.objects.get(pk=patient_id)
        client = Client.objects.get(pk=client_id)
        tests_ordering = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(test_ids)])
        lab_patient_tests = LabPatientTests.objects.filter(id__in=test_ids).order_by(tests_ordering)
        test_report_settings = PrintTestReportSettings.objects.get(client=client_id)

        if patient.referral_lab:
            sourcing_lab = patient.referral_lab
            if sourcing_lab.credit_payment:
                pass
            else:
                paid_percentage = patient.labpatientinvoice.total_paid / patient.labpatientinvoice.total_price * 100
                if paid_percentage >= sourcing_lab.min_print_amount:
                    pass
                else:
                    return Response({"Error": "Minimum payment to print is not paid!"},
                                    status=status.HTTP_400_BAD_REQUEST)

        else:
            pass
        letterhead_settings = ""
        word_report = None
        output_content = []
        sign_final_content = None
        current_department = None  # Keep track of the current department
        department_under_progress = None
        department_content = []
        medical_examination_content = ""
        final_header_content = ""
        final_footer_content = ''
        base64_pdf=""
        last_department = None
        is_current_report_type_word = None

        search_pattern = r"\{(.*?)\}"
        expression_pattern = r"\[\[(.*?)\]\]"


        if lab_patient_tests and download=='false':
            for test in lab_patient_tests:
                department = test.department.name
                last_department = department

                try:
                    details = get_lab_patient_details(test_id=test.id, patient_id=patient_id, client_id=client_id)
                    is_word_report = details['is_word_report']
                    lab_patient_test = details['lab_patient_test']
                    letterhead_settings = details['letterhead_settings']
                    client_report_settings = details['client_report_settings']

                except Exception as error:
                    print(error)
                    return Response(f"Error fetching details: {error}", status=400)

                if department != current_department:
                    if current_department is not None and current_department != 'Medical Examination':
                        if not is_current_report_type_word:
                            department_content.append(sign_final_content)
                            output_content.append('\n'.join(department_content))
                            output_content.append("<div class='break_page'></div>")  # Add page break
                        else:
                            output_content.append('\n'.join(department_content))

                    current_department = department  # Update the current department
                    department_content = []

                    table_start = f'''
                                    <table style="border-collapse:collapse;width:100%;">
                                        <tbody>
                                        
                                    '''

                    output_content.append(table_start)

                else:
                    if current_department is not None and not is_current_report_type_word and current_department != 'Medical Examination':
                        spacing_content = f'''
                                            <tr>
                                                <td class="spacingContent" style="height:16px;"></td>
                                            </tr>
                                            
                                            '''
                        department_content.append(spacing_content)

                is_current_report_type_word = is_word_report

                # Determine the template type
                if not is_word_report and lab_patient_test.department.name == "Medical Examination":
                    template_type = PrintTemplateType.objects.get(name='Medical Examination Report')

                elif not is_word_report:
                    template_type = PrintTemplateType.objects.get(name='Lab Test Report (Fixed)')
                else:
                    template_type = PrintTemplateType.objects.get(name='Lab Test Report (Word)')

                # Fetch the template
                print_template = PrintTemplate.objects.filter(print_template_type=template_type,
                                                              is_default=True).first()
                if print_template:
                    template = PrintDataTemplate.objects.get(print_template=print_template)
                else:
                    return Response({"Error": "Please check whether default template is selected or not!"},
                                    status=status.HTTP_400_BAD_REQUEST)

                word_report = LabPatientWordReportTemplate.objects.filter(LabPatientTestID=lab_patient_test).first()
                if word_report:
                    template_content = "<div>" + word_report.report + "</div>"
                else:
                    template_content = template.data

                intermediate_content = re.sub(search_pattern, lambda match: replace_tag(match=match,lab_patient_test=lab_patient_test,
                                                                          client_report_settings=client_report_settings,
                                                                          details=details), template_content)
                final_content = re.sub(expression_pattern, lambda match: evaluate_expression(match=match, details=details), intermediate_content)

                if lab_patient_test.department.name == "Medical Examination":
                    medical_examination_content += final_content
                    final_content = None

                else:
                    if department == department_under_progress:
                        final_content = remove_duplicate_report_headings(content=final_content)
                    template_header_content = template.header if template.header else ""
                    intermediate_header_content = re.sub(search_pattern, lambda match: replace_tag(match=match,lab_patient_test=lab_patient_test,
                                                                          client_report_settings=client_report_settings,
                                                                          details=details), template_header_content)
                    final_header_content = re.sub(expression_pattern, lambda match: evaluate_expression(match=match, details=details),
                                                     intermediate_header_content)

                    # Footer
                    template_footer_content = template.footer if template.footer else ""
                    intermediate_footer_content = re.sub(search_pattern, lambda match: replace_tag(match=match,lab_patient_test=lab_patient_test,
                                                                          client_report_settings=client_report_settings,
                                                                          details=details), template_footer_content)
                    final_footer_content = re.sub(expression_pattern, lambda match: evaluate_expression(match=match, details=details),
                                                     intermediate_footer_content)

                    signature_content = details['signature_content']
                    sign_intermediate_content = re.sub(search_pattern, lambda match: replace_tag(match=match,lab_patient_test=lab_patient_test,
                                                                          client_report_settings=client_report_settings,
                                                                          details=details), signature_content)
                    sign_final_content = re.sub(expression_pattern, lambda match: evaluate_expression(match=match, details=details), sign_intermediate_content)
                    if sign_final_content:
                            sign_final_content = f'''
                                                        <tr>
                                                            <td colspan="4">{sign_final_content}</td>
                                                        </tr>
                                                    </tbody>
                                                </table>
                                                
                                                '''
                if final_content:
                    department_content.append(final_content)
                    department_under_progress = department
            if department_content:
                if not word_report and last_department != 'Medical Examination':
                    department_content.append(sign_final_content)
                output_content.append('\n'.join(department_content))

            output_content = '\n'.join(output_content)

            output_content = remove_duplicate_department_headings(output_content)

            if lab_patient_tests.exclude(department__name="Medical Examination"):
                output_content = output_content
                output_content = f'<div style="font-family:{letterhead_settings.default_font.value}">{output_content}</div>'
            else:
                output_content = None

        else:
            try:
                download_api = DownloadTestReportViewset()

                # download_api.request = request  # Set the request context
                hashed_test_ids = ','.join(encode_id(test_id) for test_id in test_ids)

                download_response = download_api.list(test_ids=hashed_test_ids, client_id=encode_id(client_id),
                                                      letterhead=letterhead, sourcing_lab_for_settings=sourcing_lab_for_settings)
                print('download completed')
                base64_pdf = download_response.data.get('pdf_base64', None)
            except Exception as error:
                return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

        is_only_fixed = True  # Default to True
        try:
            for test in lab_patient_tests:
                if word_report:
                    is_only_fixed = False
                technician = LabTechnicians.objects.filter(LabPatientTestID=test, is_report_printed=False).first()
                print(technician)
                if technician:
                    technician.is_report_printed = True
                    technician.save()

        except Exception as error:
            print(error)

        return Response({
            'html_content': output_content,
            "header": final_header_content,
            "footer": final_footer_content,
            "link_pdf": base64_pdf,
            "medical_examination_content": medical_examination_content,
            "is_only_fixed": is_only_fixed
        })

        # return HttpResponse(output_content)


class TpaUltrasoundConfigViewset(viewsets.ModelViewSet):
    queryset = TpaUltrasoundConfig.objects.all()
    serializer_class = TpaUltrasoundConfigSerializer

    def destroy(self, request, *args, **kwargs):
        return Response({"Error": "Method Not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


class TpaUltrasoundImagesViewset(viewsets.ModelViewSet):
    queryset = TpaUltrasoundImages.objects.all()
    serializer_class = TpaUltrasoundImagesSerializer


class TpaUltrasoundViewset(viewsets.ModelViewSet):
    queryset = TpaUltrasound.objects.all()
    serializer_class = TpaUltrasoundSerializer

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer_data = serializer.validated_data
            images = request.data.getlist('images')
            tpa_ultrasound_instance = serializer.save()

            if images:
                for image in images:
                    image_data = TpaUltrasoundImages.objects.create(image=image)
                    tpa_ultrasound_instance.images.add(image_data)

                serializer = TpaUltrasoundSerializer(tpa_ultrasound_instance)

            return Response(serializer.data)

        except Exception as error:
            return Response({"Error": f"{error}"})

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            # Update associated images
            images = request.data.getlist('images', None)
            instance.images.all().delete()  # Remove existing images
            if images is not None:
                for image in images:
                    image_data = TpaUltrasoundImages.objects.create(image=image)
                    instance.images.add(image_data)

            return Response(serializer.data)
        except Exception as error:
            return Response({"Error": f"{error}"})

    def destroy(self, request, *args, **kwargs):
        return Response({"Error": "Method Not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


class TpaUltrasoundIntegrationView(generics.CreateAPIView):
    queryset = TpaUltrasound.objects.all()
    serializer_class = TpaUltrasoundIntegrationSerializer
    permission_classes = [permissions.AllowAny]


class TpaUltrasoundMetaInfoListView(generics.ListAPIView):
    queryset = TpaUltrasound.objects.all()
    serializer_class = TpaUltrasoundMetaInfoListViewSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = TpaUltraSoundFilter



class PrintReceptionistReportViewset(viewsets.ModelViewSet):
    serializer_class = PrintReceptionistReportSerializer

    def create(self, request=None, lab_staff=None, start_date=None, end_date=None, template_id=None, client_id=None,
               report=None,
               *args, **kwargs):
        lab_staff_id = self.request.query_params.get('lab_staff', None)
        start_date_input = self.request.query_params.get('start_date', None)
        end_date_input = self.request.query_params.get('end_date', None)
        template_id = self.request.query_params.get('template_id', None)
        client_id = self.request.query_params.get('client_id', None)
        report_type = self.request.query_params.get('report', None)

        client = Client.objects.get(pk=client_id)

        if start_date_input or end_date_input:
            print(start_date_input, 'start_date')

            start_date = datetime.strptime(start_date_input, "%Y-%m-%d").date()
            if not end_date_input:
                end_date = datetime.combine(start_date, time.max)
                print(end_date, 'new end_date')
            else:
                end_date = datetime.strptime(end_date_input, "%Y-%m-%d").date()
                end_date = datetime.combine(end_date, datetime.max.time())

                # end_date = end_date - timedelta(seconds=1)
                print(end_date, 'end_date')

        report_printed_on = datetime.now().strftime('%d-%m-%y %I:%M %p')

        report_date_range = f"{start_date.strftime('%d-%m-%Y')}"

        if end_date_input:
            report_date_range = f"{start_date.strftime('%d-%m-%Y')} to {end_date.strftime('%d-%m-%Y')}"

        if template_id == '5':
            # Filter receipts and refunds based on date range
            receipts_queryset = LabPatientReceipts.objects.filter(added_on__range=(start_date, end_date))
            refunds_queryset = LabPatientRefund.objects.filter(added_on__range=(start_date, end_date))
            expenses_queryset = LabExpenses.objects.filter(authorized_by=lab_staff,
                                                           added_on__range=(start_date,end_date))

            # Get LabStaff who created these receipts or refunds
            staff_queryset = LabStaff.objects.filter(
                Q(labpatientreceipts__in=receipts_queryset) | Q(labpatientrefund__in=refunds_queryset)
                | Q(labexpenses__in=expenses_queryset)
            ).distinct()

            report_heading = f'User Collection Consolidated Report of {report_date_range}'

        else:
            staff_queryset = None
            if lab_staff_id:
                staff_queryset = LabStaff.objects.filter(pk=lab_staff_id)

            report_heading = f'User Collection Shift Report of {report_date_range}'

        def return_test_and_package_names(receipt=None):
            tests = receipt.tests.exclude(status_id__name='Cancelled')
            packages = receipt.packages.exclude(is_package_cancelled=False)

            tests_and_packages_names = []
            tests_and_packages_count = []
            for test in tests:
                tests_and_packages_names.append(test.name)

            for package in packages:
                tests_and_packages_names.append(package.name)

            if tests:
                tests_and_packages_count.append(f'Total Tests: {tests.count()}')

            if packages:
                tests_and_packages_count.append(f'Packages: {packages.count()}')

            tests_and_packages_names = ", \n".join(test for test in tests_and_packages_names)
            tests_and_packages_count = ", \n".join(count for count in tests_and_packages_count)

            return tests_and_packages_names, tests_and_packages_count

        def return_today_registered_patients_data():
            patients_list = Patient.objects.filter(created_by=lab_staff, added_on__gte=start_date,
                                                   added_on__lte=end_date)

            head_content = '''
                            <tr>
                                <th colspan="13" style="text-align:center; padding:5px 10px;background-color:#e6e8e6;">Today's Registered Collection</th>
                            </tr>
                            <tr>
                              <th style="text-align:center; padding:2px 5px;background-color:#e6e8e6;">S.No.</th>
                              <th style="text-align:center; padding:2px 5px;background-color:#e6e8e6;">Visit ID</th>
                              <th style="text-align:center; padding:2px 5px;background-color:#e6e8e6;">Bill No</th>
                              <th style="text-align:left; padding:2px 5px;background-color:#e6e8e6;">Patient Name</th>
                              <th style="text-align:left; padding:2px 5px;background-color:#e6e8e6;">Age</th>
                              <th style="text-align:left; padding:2px 5px;background-color:#e6e8e6;">Gender</th>
                              <th style="text-align:left; padding:2px 5px;background-color:#e6e8e6;">Mobile Number</th>
                              <th style="text-align:left; padding:2px 5px;background-color:#e6e8e6;">Tests/Packages</th>
                              <th style="text-align:right; padding:2px 5px;background-color:#e6e8e6;">Total</th>
                              <th style="text-align:right; padding:2px 5px;background-color:#e6e8e6;">Discount</th>
                              <th style="text-align:right; padding:2px 5px;background-color:#e6e8e6;">Paid</th>
                              <th style="text-align:right; padding:2px 5px;background-color:#e6e8e6;">Balance</th>
                              <th style="text-align:left; padding:2px 5px;background-color:#e6e8e6;">Remarks</th>
                            </tr>
                            '''

            body_content = ""
            patient_data = {}

            related_objects = LabPatientReceipts.objects.filter(
                patient__in=patients_list, added_on__gte=start_date, added_on__lte=end_date, created_by=lab_staff
            ).select_related('patient', 'invoiceid').prefetch_related('payments__pay_mode')

            for obj in related_objects:
                patient_key = (obj.patient.visit_id, obj.invoiceid.invoice_id)
                tests, tests_count = return_test_and_package_names(obj)

                if patient_key not in patient_data:
                    patient_data[patient_key] = {
                        "visit_id": obj.patient.visit_id,
                        "invoice_id": obj.invoiceid.invoice_id,
                        "name": obj.patient.name,
                        "age": get_age_details_in_short_form(obj.patient),
                        "gender": obj.patient.gender,
                        "mobile_number": obj.patient.mobile_number,
                        "tests": tests,
                        "tests_count":tests_count,
                        "total": obj.invoiceid.total_cost,
                        "paid": sum(payment.paid_amount for payment in obj.payments.all()),
                        "discount": Decimal(obj.discount_amt if obj.discount_amt else "0.00"),
                        "balance": Decimal(obj.after_payment_due if obj.after_payment_due else "0.00"),
                        "remarks": str(obj.remarks + '\n') if obj.remarks else ''

                    }
                else:
                    patient_data[patient_key]["total"] = obj.invoiceid.total_cost
                    patient_data[patient_key]["paid"] += sum(
                        payment.paid_amount for payment in obj.payments.all())
                    patient_data[patient_key]["discount"] += Decimal(
                        obj.discount_amt if obj.discount_amt else "0.00")
                    patient_data[patient_key]["balance"] = Decimal(
                        obj.after_payment_due if obj.after_payment_due else "0.00")
                    patient_data[patient_key]["remarks"] += str(obj.remarks + '\n') if obj.remarks else ''

            serial_number = 1
            for key, data in patient_data.items():
                body_content += f'''
                                <tr>
                                    <td style="text-align:center; padding:2px 5px;">{serial_number}</td>
                                    <td style="text-align:center; padding:2px 5px;" class="text-nowrap">{data["visit_id"]}</td>
                                    <td style="text-align:center; padding:2px 5px;">{data["invoice_id"]}</td>
                                    <td style="text-align:left; padding:2px 5px;">{data["name"]}</td>                                    
                                    <td style="text-align:left; padding:2px 5px;" class="text-nowrap">{data["age"]}</td>
                                    <td style="text-align:left; padding:2px 5px;" class="text-nowrap">{data["gender"]}</td>
                                    <td style="text-align:left; padding:2px 5px;">{data["mobile_number"]}</td>
                                    <td style="text-align:left;vertical-align:middle; padding: 2px 5px; white-space: pre-line;line-height:14px;"><small>{data['tests']}. <br> <strong style="line-height:16px;">{data['tests_count']}</strong></small></td>
                                    <td style="text-align:right; padding:2px 5px;">{data["total"]}</td>
                                    <td style="text-align:right; padding:2px 5px;">{data["discount"]}</td>
                                    <td style="text-align:right; padding:2px 5px;">{data["paid"]}</td>
                                    <td style="text-align:right; padding:2px 5px;">{data["balance"]}</td>
                                    <td style="text-align:left; padding:2px 5px;max-width:100px;white-space:pre-line;">{data["remarks"]}</td>
                                </tr>'''
                serial_number += 1

            if body_content:
                totals_row = f'''
                              <tr>
                                  <td colspan="8" style="text-align:right; font-weight:bold;padding:2px 5px;">Totals</td>
                                  <td style="text-align:right; padding:2px 5px; font-weight: bold;">
                                      {sum(data["total"] for data in patient_data.values())}
                                  </td>
                                  <td style="text-align:right;padding:2px 5px; font-weight: bold;">
                                      {sum(data["discount"] for data in patient_data.values())}
                                  </td>
                                  <td style="text-align:right; padding:2px 5px; font-weight: bold;">
                                      {sum(data["paid"] for data in patient_data.values())}
                                  </td>

                                  <td style="text-align:right; padding:2px 5px; font-weight: bold;">
                                      {sum(data["balance"] for data in patient_data.values())}
                                  </td>
                                  <td style="text-align:left; padding:2px 5px; font-weight: bold;"></td>
                              </tr>'''

                body_content += totals_row

            if body_content:
                total_content = f'''
                                {head_content}{body_content}
                                <tr><td colspan="13" style="height: 20px;"></td></tr>
                                '''
            else:
                total_content = f'''<tr><td colspan="13" style="padding:5px 10px;">No today's registered collections found for the given period.</td></tr>
                                    <tr><td colspan="13" style="height: 20px;"></td></tr>'''

            return total_content

        def return_previous_patients_data():
            patients_list = Patient.objects.filter(created_by=lab_staff, added_on__lte=start_date)

            head_content = '''<tr>
                                <th colspan="13" style="text-align:center; padding:5px 10px;background-color:#e6e8e6;">Due Collection</th>
                              </tr>
                              <tr>
                                 <th style="text-align:center; padding:2px 5px;background-color:#e6e8e6;">S.No.</th>
                                 <th style="text-align:center; padding:2px 5px;background-color:#e6e8e6;">Visit ID</th>
                                 <th style="text-align:center; padding:2px 5px;background-color:#e6e8e6;">Bill No</th>
                                 <th style="text-align:left; padding:2px 5px;background-color:#e6e8e6;">Patient Name</th>
                                <th style="text-align:left; padding:2px 5px;background-color:#e6e8e6;">Age</th>
                                <th style="text-align:left; padding:2px 5px;background-color:#e6e8e6;">Gender</th>
                                <th style="text-align:left; padding:2px 5px;background-color:#e6e8e6;">Mobile Number</th>
                                <th style="text-align:left; padding:2px 5px;background-color:#e6e8e6;">Tests/Packages</th>
                                 <th style="text-align:right; padding:2px 5px;background-color:#e6e8e6;">Last Due</th>
                                 <th style="text-align:right; padding:2px 5px;background-color:#e6e8e6;">Discount</th>
                                 <th style="text-align:right; padding:2px 5px;background-color:#e6e8e6;">Paid</th>
                                 <th style="text-align:right; padding:2px 5px;background-color:#e6e8e6;">Balance</th>
                                 <th style="text-align:left; padding:2px 5px;background-color:#e6e8e6;">Remarks</th>
                              </tr>'''

            body_content = ""
            patient_data = {}

            related_objects = LabPatientReceipts.objects.filter(
                patient__in=patients_list,
                added_on__gte=start_date,
                added_on__lte=end_date,
                created_by=lab_staff
            ).select_related('patient', 'invoiceid').prefetch_related('payments__pay_mode')

            for obj in related_objects:
                patient_key = (obj.patient.visit_id, obj.invoiceid.invoice_id)
                tests, tests_count = return_test_and_package_names(obj)

                if patient_key not in patient_data:
                    patient_data[patient_key] = {
                        "visit_id": obj.patient.visit_id,
                        "invoice_id": obj.invoiceid.invoice_id,
                        "name": obj.patient.name,
                        "age": get_age_details_in_short_form(obj.patient),
                        "gender": obj.patient.gender,
                        "mobile_number": obj.patient.mobile_number,
                        "tests": tests,
                        "tests_count": tests_count,
                        "last_due": Decimal(obj.before_payment_due if obj.before_payment_due else "0.00"),
                        "paid": sum(payment.paid_amount for payment in obj.payments.all()),
                        "discount": Decimal(obj.discount_amt if obj.discount_amt else "0.00"),
                        "balance": Decimal(obj.after_payment_due if obj.after_payment_due else "0.00"),
                        "remarks": str(obj.remarks + '\n') if obj.remarks else ''
                    }
                else:
                    patient_data[patient_key]["paid"] += sum(
                        payment.paid_amount for payment in obj.payments.all())
                    patient_data[patient_key]["discount"] += Decimal(
                        obj.discount_amt if obj.discount_amt else "0.00")
                    patient_data[patient_key]["balance"] = Decimal(
                        obj.after_payment_due if obj.after_payment_due else "0.00")
                    patient_data[patient_key]["remarks"] += str(obj.remarks + '\n') if obj.remarks else ''

            serial_number = 1
            for key, data in patient_data.items():
                body_content += f'''<tr>
                                       <td style="text-align:center; padding:2px 5px;">{serial_number}</td>
                                       <td style="text-align:center; padding:2px 5px;" class="text-nowrap">{data["visit_id"]}</td>
                                       <td style="text-align:center; padding:2px 5px;">{data["invoice_id"]}</td>
                                       <td style="text-align:left; padding:2px 5px;">{data["name"]}</td>
                                        <td style="text-align:left; padding:2px 5px;" class="text-nowrap">{data["age"]}</td>
                                        <td style="text-align:left; padding:2px 5px;" class="text-nowrap">{data["gender"]}</td>
                                        <td style="text-align:left; padding:2px 5px;">{data["mobile_number"]}</td>
                                        <td style="text-align:left;vertical-align:middle; padding: 2px 5px; white-space: pre-line;line-height:14px;"><small>{data['tests']}. <br> <strong style="line-height:16px;">{data['tests_count']}</strong></small></td>
                                        <td style="text-align:right; padding:2px 5px;">{data["last_due"]}</td>
                                       <td style="text-align:right; padding:2px 5px;">{data["discount"]}</td>
                                       <td style="text-align:right; padding:2px 5px;">{data["paid"]}</td>
                                       <td style="text-align:right; padding:2px 5px;">{data["balance"]}</td>
                                       <td style="text-align:left; padding:2px 5px;">{data["remarks"]}</td>
                                   </tr>'''
                serial_number += 1

            if body_content:
                totals_row = f'''<tr>
                                   <td colspan="8" style="text-align:right;font-weight:bold;padding:2px 5px;">Totals</td>
                                   <td style="text-align:right; padding:2px 5px; font-weight: bold;">
                                       {sum(data["last_due"] for data in patient_data.values())}
                                   </td>
                                   <td style="text-align:right; padding:2px 5px; font-weight: bold;">
                                       {sum(data["discount"] for data in patient_data.values())}
                                   </td>
                                   <td style="text-align:right; padding:2px 5px; font-weight: bold;">
                                       {sum(data["paid"] for data in patient_data.values())}
                                   </td>

                                   <td style="text-align:right; padding:2px 5px; font-weight: bold;">
                                       {sum(data["balance"] for data in patient_data.values())}
                                   </td>
                                   <td style="text-align:left; padding:2px 5px; font-weight: bold;"></td>
                               </tr>'''

                body_content += totals_row

            if body_content:
                total_content = f'''
                                    {head_content}{body_content}
                                    <tr><td colspan="13" style="height: 20px;"></td></tr>
                                '''
            else:
                total_content = f'''
                    <tr><td colspan="13" style="padding:5px 10px;">No due collections found for the given period.</td></tr>
                    <tr><td colspan="13" style="height: 20px;"></td></tr>
                    '''

            return total_content

        def return_others_previous_patients_data():
            patients_list = Patient.objects.all()
            head_content = '''
                                <tr>
                                    <th colspan="13" style="text-align:center; padding:5px 10px;background-color:#e6e8e6;">Payment Collected (Registered By Others)</th>
                                </tr>
                                <tr>
                                    <th style="text-align:center; padding:2px 5px;background-color:#e6e8e6;">S.No.</th>
                                    <th style="text-align:center; padding:2px 5px;background-color:#e6e8e6;">Visit ID</th>
                                    <th style="text-align:center; padding:2px 5px;background-color:#e6e8e6;">Bill No</th>
                                    <th style="text-align:left; padding:2px 5px;background-color:#e6e8e6;">Patient Name</th>
                                    <th style="text-align:left; padding:2px 5px;background-color:#e6e8e6;">Age</th>
                                    <th style="text-align:left; padding:2px 5px;background-color:#e6e8e6;">Gender</th>
                                    <th style="text-align:left; padding:2px 5px;background-color:#e6e8e6;">Mobile Number</th>
                                    <th style="text-align:left; padding:2px 5px;background-color:#e6e8e6;">Tests/Packages</th>
                                    <th style="text-align:right; padding:2px 5px;background-color:#e6e8e6;">Last Due</th>
                                    <th style="text-align:right; padding:2px 5px;background-color:#e6e8e6;">Discount</th>
                                    <th style="text-align:right; padding:2px 5px;background-color:#e6e8e6;">Paid</th>
                                    <th style="text-align:right; padding:2px 5px;background-color:#e6e8e6;">Balance</th>
                                    <th style="text-align:left; padding:2px 5px;background-color:#e6e8e6;">Remarks</th>
                                </tr>'''

            body_content = ""

            related_objects = LabPatientReceipts.objects.filter(
                patient__in=patients_list, created_by=lab_staff,
                added_on__gte=start_date, added_on__lt=end_date
            ).select_related('patient', 'invoiceid').prefetch_related('payments__pay_mode')

            patient_data = {}

            for obj in related_objects:
                if obj.patient.created_by == lab_staff:
                    continue

                patient_key = (obj.patient.visit_id, obj.invoiceid.invoice_id)
                tests, tests_count = return_test_and_package_names(obj)

                if patient_key not in patient_data:
                    patient_data[patient_key] = {
                        "visit_id": obj.patient.visit_id,
                        "invoice_id": obj.invoiceid.invoice_id,
                        "name": obj.patient.name,
                        "age": get_age_details_in_short_form(obj.patient),
                        "gender": obj.patient.gender,
                        "mobile_number": obj.patient.mobile_number,
                        "tests": tests,
                        "tests_count": tests_count,
                        "last_due": Decimal(obj.before_payment_due if obj.before_payment_due else "0.00"),
                        "paid": sum(payment.paid_amount for payment in obj.payments.all()),
                        "discount": Decimal(obj.discount_amt if obj.discount_amt else "0.00"),
                        "balance": Decimal(obj.after_payment_due if obj.after_payment_due else "0.00"),
                        "remarks": str(obj.remarks + '\n') if obj.remarks else ''
                    }

                else:
                    patient_data[patient_key]["paid"] += sum(
                        payment.paid_amount for payment in obj.payments.all())
                    patient_data[patient_key]["discount"] += Decimal(
                        obj.discount_amt if obj.discount_amt else "0.00")
                    patient_data[patient_key]["balance"] = Decimal(
                        obj.after_payment_due if obj.after_payment_due else "0.00")
                    patient_data[patient_key]["remarks"] += str(obj.remarks + '\n') if obj.remarks else ''

            serial_number = 1
            for key, data in patient_data.items():
                body_content += f'''
                                    <tr>
                                        <td style="text-align:center; padding:2px 5px;">{serial_number}</td>
                                        <td style="text-align:center; padding:2px 5px;" class="text-nowrap">{data["visit_id"]}</td>
                                        <td style="text-align:center; padding:2px 5px;">{data["invoice_id"]}</td>
                                        <td style="text-align:left; padding:2px 5px;">{data["name"]}</td>
                                        <td style="text-align:left; padding:2px 5px;" class="text-nowrap">{data["age"]}</td>
                                        <td style="text-align:left; padding:2px 5px;" class="text-nowrap">{data["gender"]}</td>
                                        <td style="text-align:left; padding:2px 5px;">{data["mobile_number"]}</td>
                                        <td style="text-align:left;vertical-align:middle; padding: 2px 5px; white-space: pre-line;line-height:14px;"><small>{data['tests']}. <br> <strong style="line-height:16px;">{data['tests_count']}</strong></small></td>
                                        <td style="text-align:right; padding:2px 5px;">{data["last_due"]}</td>
                                        <td style="text-align:right; padding:2px 5px;">{data["discount"]}</td>
                                        <td style="text-align:right; padding:2px 5px;">{data["paid"]}</td>
                                        <td style="text-align:right; padding:2px 5px;">{data["balance"]}</td>
                                        <td style="text-align:left; padding:2px 5px;">{data["remarks"]}</td>
                                    </tr>'''
                serial_number += 1

            if body_content:
                totals_row = f'''<tr>
                                    <td colspan="8" style="text-align:right;font-weight:bold;padding:2px 5px;">Totals</td>
                                    <td style="text-align:right; font-weight: bold; padding:2px 5px;">
                                        {sum(data["last_due"] for data in patient_data.values())}
                                    </td>
                                    <td style="text-align:right; font-weight: bold; padding:2px 5px;">
                                        {sum(data["discount"] for data in patient_data.values())}
                                    </td>
                                    <td style="text-align:right; font-weight: bold; padding:2px 5px;">
                                        {sum(data["paid"] for data in patient_data.values())}
                                    </td>

                                    <td style="text-align:right; font-weight: bold; padding:2px 5px;">
                                        {sum(data["balance"] for data in patient_data.values())}
                                    </td>
                                    <td style="text-align:left; font-weight: bold; padding:2px 5px;"></td>
                                </tr>'''

                body_content += totals_row

            if body_content:
                total_content = f'''
                                    {head_content}{body_content}
                                    <tr><td colspan="13" style="height: 20px;"></td></tr>
                                '''
            else:
                total_content = f'''
                    <tr><td colspan="13" style="padding:5px 10px;">No payments collected on behalf of others for the given period.</td></tr>
                    <tr><td colspan="13" style="height: 20px;"></td></tr>
                    '''

            return total_content

        def return_transaction_wise_payments_data():
            related_objects = LabPatientReceipts.objects.filter(
                added_on__gte=start_date,
                added_on__lt=end_date,
                created_by=lab_staff
            ).select_related('patient').prefetch_related('payments__pay_mode')

            head_content = '''<tr>
                                    <th colspan="13" style="text-align:center; padding:5px 10px;background-color:#e6e8e6;">Transactions Collection</th>
                              </tr>
                              <tr>
                                  <th style="text-align:center;padding:2px 5px;background-color:#e6e8e6;">S.No</th>
                                  <th style="text-align:center; padding:2px 5px;background-color:#e6e8e6;">Registration Date</th>
                                  <th style="text-align:center; padding:2px 5px;background-color:#e6e8e6;">Transaction Date</th>
                                  <th colspan="2" style="text-align:center;padding:2px 5px;background-color:#e6e8e6;">Receipt ID</th>
                                  <th colspan="2" style="text-align:center;padding:2px 5px;background-color:#e6e8e6;">Visit ID</th>
                                  <th colspan="2" style="text-align:left; padding:2px 5px;background-color:#e6e8e6;">Patient Name</th>
                                  <th colspan="2" style="text-align:right;padding:2px 5px;background-color:#e6e8e6;">Amount Paid</th>
                                  <th colspan="2" style="text-align:center; padding:2px 5px;background-color:#e6e8e6;">Pay mode</th>
                              </tr>'''

            body_content = ""

            total_collections = Decimal('0.00')

            for i, obj in enumerate(related_objects, start=1):
                added_on = obj.added_on.strftime('%Y-%m-%d %I:%M %p') if obj.added_on else ""
                patient_added_on = obj.patient.added_on.strftime('%Y-%m-%d %I:%M %p') if obj.patient.added_on else ""

                paid_amounts = [str(payment.paid_amount) for payment in obj.payments.all()]
                pay_modes = [payment.pay_mode.name for payment in obj.payments.all()]

                amount_paid = sum(Decimal(payment.paid_amount) for payment in obj.payments.all())
                total_collections += amount_paid

                body_content += f'''<tr>
                                          <td style="text-align:center;padding:2px 5px;">{i}</td>
                                          <td style="text-align:center; padding:2px 5px;">{patient_added_on}</td>  
                                          <td style="text-align:center; padding:2px 5px;">{added_on}</td>  
                                          <td colspan="2" style="text-align:center;padding:2px 5px;">{obj.Receipt_id}</td>
                                          <td colspan="2" style="text-align:center;padding:2px 5px;">{obj.patient.visit_id}</td>
                                          <td colspan="2" style="text-align:left;padding:2px 5px;">{obj.patient.name}</td>
                                          <td colspan="2" style="text-align:right;padding:2px 5px;">{"<br>".join(paid_amounts)}</td>
                                          <td colspan="2" style="text-align:center;padding:2px 5px;">{"<br>".join(pay_modes)}</td>                                                    
                                      </tr>'''

            body_content += f'''<tr>
                                       <td colspan="9" style="text-align:right; font-weight: bold; padding:5px 10px;">Total Collections</td>
                                       <td colspan="2" style="text-align:right; font-weight: bold;padding:5px;">{total_collections}</td>
                                       <td colspan="2" style="text-align:right; font-weight: bold;"></td>
                                  </tr>'''

            if body_content:
                total_content = f'''
                                    {head_content}{body_content}
                                    <tr><td colspan="13" style="height: 20px;"></td></tr>
                                '''
            else:
                total_content = f'''
                                    <tr><td colspan="13" style="padding:5px 10px;">No transactions found for the given period.</td></tr>
                                    <tr><td colspan="13" style="height: 20px;"></td></tr>
                                '''

            return total_content

        def return_refund_collections_data():
            related_objects_for_labstaff = LabPatientRefund.objects.filter(
                added_on__gte=start_date,
                added_on__lt=end_date,
                created_by=lab_staff
            ).select_related('patient')

            head_content = '''<tr>
                                    <th colspan="13" style="text-align:center; padding:5px 10px;background-color:#e6e8e6;">Refund</th>
                              </tr>
                              <tr>
                                  <th colspan="2" style="text-align:center; padding:2px 5px;background-color:#e6e8e6;">S.No</th>
                                  <th colspan="2" style="text-align:center; padding:2px 5px;background-color:#e6e8e6;">Refund ID</th>
                                  <th colspan="2" style="text-align:center; padding:2px 5px;background-color:#e6e8e6;">Visit ID</th>
                                  <th colspan="3" style="text-align:left; padding:2px 5px;background-color:#e6e8e6;">Name</th>
                                  <th colspan="2" style="text-align:right;padding:2px 5px;background-color:#e6e8e6;">Refund Amount</th>
                                  <th colspan="2" style="text-align:center; padding:2px 5px;background-color:#e6e8e6;">Refund Mode</th>
                              </tr>'''

            body_content = ""

            total_refund_amount = related_objects_for_labstaff.aggregate(total=Sum('refund'))['total'] or Decimal('0.00')

            for i, obj in enumerate(related_objects_for_labstaff, start=1):
                body_content += f'''<tr>
                                        <td colspan="2" style="text-align:center; padding:2px 5px;">{i}</td>
                                        <td colspan="2" style="text-align:center; padding:2px 5px;">{obj.refund_id}</td>
                                        <td colspan="2" style="text-align:center; padding:2px 5px;">{obj.patient.visit_id}</td>
                                        <td colspan="3" style="text-align:left; padding:2px 5px;">{obj.patient.name}</td>
                                        <td colspan="2" style="text-align:right;padding:2px 5px;">{obj.refund}</td>
                                        <td colspan="2" style="text-align:center; padding:2px 5px;">{obj.refund_mode}</td>
                                    </tr>'''

            if body_content:
                body_content += f'''<tr>
                                         <td colspan="9" style="text-align:right; font-weight: bold; padding:5px;">Totals</td>
                                         <td colspan="2" style="text-align:right; font-weight: bold; padding:5px;">{total_refund_amount}</td>
                                         <td colspan="2" style="text-align:right; font-weight: bold;"></td>
                                    </tr>'''

                total_content = f'''
                                    {head_content}{body_content}
                                    <tr><td colspan="13" style="height: 20px;"></td></tr>
                                '''
            else:
                total_content = f'''
                                    <tr><td colspan="13" style="padding:5px 10px;">No Refund collections found for the given period.</td></tr>
                                    <tr><td colspan="13" style="height: 20px;"></td></tr>
                                '''

            return total_content

        def return_total_calculations_data():
            related_objects = LabPatientReceipts.objects.filter(added_on__gte=start_date,added_on__lt=end_date,
                                                            created_by=lab_staff).prefetch_related('payments__pay_mode')

            total_calculation = sum(
                payment.paid_amount for obj in related_objects for payment in obj.payments.all()
            )

            refund_objects = LabPatientRefund.objects.filter(added_on__gte=start_date, added_on__lt=end_date,
                                                             created_by=lab_staff, refund_mode__name='Cash')

            total_refund = refund_objects.aggregate(total=Sum('refund'))['total'] or Decimal('0.00')

            total_online_payments = sum(
                payment.paid_amount for obj in related_objects for payment in
                obj.payments.exclude(pay_mode__name="Cash")
            )

            expenses_by_cash_list = LabExpenses.objects.filter(authorized_by=lab_staff, added_on__gte=start_date,
                                                   added_on__lte=end_date,pay_mode__name='Cash')
            total_expenses_by_cash = expenses_by_cash_list.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            total_cash_payments = total_calculation - total_refund - total_online_payments - total_expenses_by_cash

            body_content = f'''
                    <tr style="font-weight:bold; font-size:14px;">
                        <td style="text-align:center; padding:5px 10px;">(+)</td>
                        <td colspan="8" style="text-align:left; padding:5px 10px;">
                            Total Collection (Today's Registered Collection + Due Collection + Payment Collected)
                        </td>
                        <td colspan="4" style="text-align:left; padding:5px 10px;">{total_calculation}</td>                        
                    </tr>
                    <tr style="font-weight:bold; font-size:14px;">
                        <td style="text-align:center; padding:5px 10px;">(-)</td>
                        <td colspan="8" style="text-align:left; padding:5px 10px;">Refund</td>
                        <td colspan="4" style="text-align:left; padding:5px 10px;">{total_refund}</td>
                    </tr>
                    
                    <tr style="font-weight:bold; font-size:14px;">
                        <td style="text-align:center; padding:5px 10px;">(-)</td>
                        <td colspan="8" style="text-align:left; padding:5px 10px;">Online Collection</td>
                        <td colspan="4" style="text-align:left; padding:5px 10px;">{total_online_payments}</td>
                    </tr>
                    
                    <tr style="font-weight:bold; font-size:14px;">
                        <td style="text-align:center; padding:5px 10px;">(-)</td>
                        <td colspan="8" style="text-align:left; padding:5px 10px;">Expenses(Cash)</td>
                        <td colspan="4" style="text-align:left; padding:5px 10px;">{total_expenses_by_cash}</td>
                    </tr>
                    
                    <tr style="font-weight:bold; font-size:14px;">
                        <td style="text-align:center; padding:5px 10px;"></td>
                        <td colspan="8" style="text-align:left; padding:5px 10px;">Net Cash Collection</td>
                        <td colspan="4" style="text-align:left; padding:5px 10px;">{total_cash_payments}</td>
                    </tr>
                '''

            total_content = f'''
                                {body_content}
                            '''
            return total_content

        def return_expenses_data():
            expenses_list = LabExpenses.objects.filter(authorized_by=lab_staff, added_on__gte=start_date,
                                                   added_on__lte=end_date)
            total_expenses_amount = expenses_list.aggregate(total=Sum('amount'))['total']

            total_expenses_by_cash = expenses_list.filter(pay_mode__name='Cash').aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            head_content = '''
                            <tr>
                                <th colspan="13" style="text-align:center; padding:5px 10px;background-color:#e6e8e6;">Today's Expenses</th>
                            </tr>
                            <tr>
                              <th style="text-align:center; padding:2px 5px;background-color:#e6e8e6;">S.No.</th>
                              <th style="text-align:center; padding:2px 5px;background-color:#e6e8e6;">Expense ID</th>
                              <th colspan="2" style="text-align:left; padding:2px 5px;background-color:#e6e8e6;">Paid To</th>
                              <th colspan="2" style="text-align:left; padding:2px 5px;background-color:#e6e8e6;">Authorised By</th>
                              <th colspan="2" style="text-align:left; padding:2px 5px;background-color:#e6e8e6;">Type</th>
                              <th style="text-align:center; padding:2px 5px;background-color:#e6e8e6;">Voucher No</th>
                              <th style="text-align:right; padding:2px 5px;background-color:#e6e8e6;">Amount</th>
                              <th style="text-align:center; padding:2px 5px;background-color:#e6e8e6;">Mode</th>
                              <th colspan="2" style="text-align:left; padding:2px 5px;background-color:#e6e8e6;">Remarks</th>
                            </tr>
                            '''

            body_content = ""
            expenses_data = {}

            related_objects = expenses_list
            serial_number = 1
            for obj in related_objects:
                body_content += f'''
                                <tr>
                                    <td style="text-align:center; padding:2px 5px;">{serial_number}</td>
                                    <td style="text-align:center; padding:2px 5px;">{obj.voucher_id}</td>
                                    <td colspan="2" style="text-align:left; padding:2px 5px;">{obj.paid_to.name}</td>
                                    <td colspan="2" style="text-align:left; padding:2px 5px;">{lab_staff.name}</td>
                                    <td colspan="2" style="text-align:left; padding:2px 5px;">{obj.expense_type.name}</td>
                                    <td style="text-align:center; padding:2px 5px;">{obj.invoice_no}</td>
                                    <td style="text-align:right; padding:2px 5px;">{obj.amount}</td>
                                    <td style="text-align:center; padding:2px 5px;">{obj.pay_mode.name}</td>
                                    <td colspan="2" style="text-align:left; padding:2px 5px;max-width:100px;white-space:pre-line;">{obj.description}</td>
                                </tr>'''
                serial_number += 1

            if body_content:
                totals_row = f'''
                              <tr>
                                  <td colspan="9" style="text-align:right; font-weight:bold;padding:2px 5px;">Totals</td>
                                  <td style="text-align:right; padding:2px 5px; font-weight: bold;">{total_expenses_amount}</td>
                                  <td style="text-align:right;padding:2px 5px; font-weight: bold;"></td>
                                  <td colspan="2" style="text-align:right; padding:2px 5px; font-weight: bold;"></td>
                              </tr>

                              <tr>
                                  <td colspan="9" style="text-align:right; font-weight:bold;padding:2px 5px;">Cash Expenses</td>
                                  <td style="text-align:right; padding:2px 5px; font-weight: bold;">{total_expenses_by_cash}</td>
                                  <td style="text-align:right;padding:2px 5px; font-weight: bold;"></td>
                                  <td colspan="2" style="text-align:right; padding:2px 5px; font-weight: bold;"></td>
                              </tr>'''

                body_content += totals_row

            if body_content:
                total_content = f'''
                                {head_content}{body_content}
                                <tr><td colspan="13" style="height: 20px;"></td></tr>
                                '''
            else:
                total_content = f'''<tr><td colspan="13" style="padding:5px 10px;">No Expenses found for the given period.</td></tr>
                                    <tr><td colspan="13" style="height: 20px;"></td></tr>'''

            return total_content


        output_content = []

        for lab_staff in staff_queryset:
            table_content = ""
            if report_type == 'general':
                today_registered_patients_data = return_today_registered_patients_data()
                previous_patients_data = return_previous_patients_data()
                others_previous_patients_data = return_others_previous_patients_data()
                refund_collections_data = return_refund_collections_data()
                total_calculations_data = return_total_calculations_data()
                expenses_data = return_expenses_data()

                table_content = today_registered_patients_data + previous_patients_data + others_previous_patients_data + refund_collections_data + expenses_data + total_calculations_data

            if report_type == 'transactions':
                transaction_wise_payments_data = return_transaction_wise_payments_data()
                refund_collections_data = return_refund_collections_data()
                total_calculations_data = return_total_calculations_data()

                table_content = transaction_wise_payments_data + refund_collections_data + total_calculations_data

            extra_spacing_in_end = f'''<tr><td colspan="13" style="height: 20px;border:0px;"></td></tr>
                                        <tr><td colspan="13" style="height: 20px;border:0px;"></td></tr>
                                        '''

            final_content = f'''
                        <table class="table table-hover inter-font" id="excelReport" border="1" cellspacing="0" style="border-collapse:collapse; width:100%;font-size:12px;">
                        <tbody>
                            <tr>
                                <td colspan="13" style="text-align:center; padding:5px 10px;background-color:#e6e8e6;font-size:18px;">
                                    <strong>{report_heading}</strong> 
                                </td>

                            </tr>
                            <tr style="font-size:14px;">
                                <td colspan="7" style="padding: 2px 10px;">Username: <strong>{lab_staff}</strong> </td>
                                <td colspan="6" style="padding: 2px 10px;">
                                    Generated On: <strong>{report_printed_on}</strong>
                                </td>                                    
                            </tr>
                            <tr><td colspan="13" style="height: 20px;"></td></tr>
                            {table_content}
                            {extra_spacing_in_end if template_id=='5' else ""}
                        </tbody>
                    </table>

            '''

            output_content.append(final_content)

        output_content = "\n".join(output_content)

        # return HttpResponse(output_content)

        return Response({'html_content': output_content})



class ReferralDoctorReportViewset(viewsets.ModelViewSet):
    serializer_class = ReferralDoctorReportSerializer

    def create(self, request=None, referral_doctor=None, start_date=None, end_date=None, template_id=None,
               client_id=None, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer_data = serializer.validated_data
        doctor = serializer_data.get('doctor_id')
        start_date = serializer_data.get('start_date')
        end_date = serializer_data.get('end_date')
        client = serializer_data.get('client')


        if doctor.doctor_type_id.id==1 and start_date and end_date and client:
            referral_doctor = doctor
            template_type = PrintTemplateType.objects.get(name='Referral Doctor')
            print_template = PrintTemplate.objects.get(print_template_type=template_type, is_default=True)
            template = PrintDataTemplate.objects.get(print_template=print_template)
            doctor_settings = BusinessReferralDoctorSettings.objects.get(client=client)
            bProfile = BusinessProfiles.objects.get(organization_name=client.name)

            start_date = datetime.strptime(str(start_date), "%Y-%m-%d")

            # end_date = datetime.strptime(str(end_date), "%Y-%m-%d")
            end_date = datetime.combine(end_date, datetime.max.time())

            referral_time_period = f"{start_date.strftime('%d-%m-%y')}" if start_date == end_date else f"{start_date.strftime('%d-%m-%y')} to {end_date.strftime('%d-%m-%y')}"

            report_printed_on = datetime.now().strftime('%d-%m-%y %I:%M %p')

            if start_date == end_date:
                end_date = end_date + timedelta(days=1)

            patients = Patient.objects.filter(referral_doctor=referral_doctor, added_on__gte=start_date,
                                              added_on__lte=end_date)

            if doctor_settings.due_clear_patients:
                patients = patients.filter(labpatientinvoice__total_due=0)

            patients_referred = patients.count()

            def ref_doctor_amount(patient):
                total_referral_amount = Decimal('0.00')
                for test in LabPatientTests.objects.filter(patient=patient).exclude(status_id__name='Cancelled'):
                    referral_model = ReferralAmountForDoctor.objects.filter(
                        referral_doctor=referral_doctor, lab_test=test.LabGlobalTestId).first()

                    test_price = test.price_after_discount if doctor_settings.is_calculation_by_net_total else test.price

                    if referral_model:
                        referral_amount = Decimal(test_price * (referral_model.referral_amount * Decimal(
                            '0.01'))) if referral_model.is_percentage else Decimal(referral_model.referral_amount)
                    else:
                        referral_amount = Decimal('0.00')

                    total_referral_amount += referral_amount

                if doctor_settings.discount_by_doctor:
                    total_referral_amount -= patient.labpatientinvoice.total_ref_discount

                total_referral_amount = total_referral_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                return total_referral_amount

            total_ref_amount = sum(ref_doctor_amount(patient) for patient in patients)

            # Handle fetching and formatting of all related data

            content = f'''
            <table class="table table-hover inter-font rounded-3 overflow-hidden border border-3 pt-5" id="excelReport" border="1" style="border-collapse: collapse; border-spacing: 0; width: 100%;font-size:12px;">                                    
                <tbody>
                <tr><th colspan="14" style="padding: 2px 4px;background-color:#e6e8e6; font-size: 18px;text-align:center; ">Referral Amount Report</th></tr>                    
                <tr><td colspan="7" style="padding: 2px 4px;">Ref.Doctor Name: <strong>{referral_doctor.name}</strong> </td><td colspan="7" style="padding: 2px 4px;">Report Time Period: <strong> {referral_time_period}</strong></td></tr>
                <tr><td colspan="7" style="padding: 2px 4px;">Ref.Doctor Mobile: {referral_doctor.mobile_number} </td><td colspan="7" style="padding: 2px 4px;">No. of Patients referred: {patients_referred} </td></tr>
                <tr><td colspan="7" style="padding: 2px 4px;">Ref.Doctor Area: {referral_doctor.geo_area} </td><td colspan="7" style="padding: 2px 4px;">Total Ref Amount for the period:<strong> Rs.{total_ref_amount}</strong> </td></tr>                                
                <tr><td colspan="7" style="padding: 2px 4px;"></td><td colspan="7" style="padding: 2px 4px;">Report printed On: {report_printed_on}</td></tr>
                <tr><td colspan="14" style="height:20px;"></td></tr>
                <tr>
                    <th style="text-align:center; padding: 2px 4px;background-color:#e6e8e6;">S.No</th>
                    <th style="text-align:center; padding: 2px 4px;background-color:#e6e8e6;">Visit ID</th>
                    <th style="text-align:center; padding: 2px 4px;background-color:#e6e8e6;">Reg Date</th>
                    <th style="text-align:left; padding: 2px 4px;background-color:#e6e8e6;">Name</th>                        
                    <th colspan="2" style="text-align:left; padding: 2px 4px;background-color:#e6e8e6;">Tests Names</th>
                    <th style="text-align:right; padding: 2px 4px;background-color:#e6e8e6;">Total Amount</th>
                    {f'<th colspan="2" style="text-align:right; padding: 2px 4px;background-color:#e6e8e6;">Discount</th>' if not doctor_settings.discount_by_doctor else ''}
                    {f'<th style="text-align:right; padding: 2px 4px;background-color:#e6e8e6;">Lab Discount</th>' if doctor_settings.discount_by_doctor else ''}
                    {f'<th style="text-align:right; padding: 2px 4px;background-color:#e6e8e6;">Ref Discount</th>' if doctor_settings.discount_by_doctor else ''}
                    <th style="text-align:right; padding: 2px 4px;background-color:#e6e8e6;">Net Amount</th>
                    <th style="text-align:right; padding: 2px 4px;background-color:#e6e8e6;">Paid</th>
                    <th style="text-align:right; padding: 2px 4px;background-color:#e6e8e6;">Refund</th>
                    <th style="text-align:right; padding: 2px 4px;background-color:#e6e8e6;">Due</th>                                    
                    <th style="text-align:right; padding: 2px 4px;background-color:#e6e8e6;">Ref. Amount</th>
                </tr>                    
            '''

            for i, patient in enumerate(patients, start=1):
                patient_tests_count = patient.labpatienttests_set.exclude(status_id__name='Cancelled').count()
                if patient_tests_count >= 1:
                    patient_row_content = f'''
                    <tr>
                        <td style="text-align:center;vertical-align:middle; padding: 2px 4px;">{i}</td>
                        <td style="text-align:left;vertical-align:middle; padding: 2px 4px;font-size:12px;white-space: nowrap;">{patient.visit_id}</td>
                        <td style="text-align:left;vertical-align:middle; padding: 2px 4px;font-size:12px;white-space: nowrap;">{patient.added_on.strftime('%d/%m/%y')}</td>
                        <td style="text-align:left;vertical-align:middle; padding: 2px 4px;font-size:12px;">{patient.name}</td>                            
                        <td colspan="2" style="text-align:left;vertical-align:middle; padding: 2px 4px; white-space: pre-line;line-height:14px;"><small>{", \n".join(test.name for test in patient.labpatienttests_set.exclude(status_id__name='Cancelled'))}. <br> <strong style="line-height:16px;">Total Tests : {patient_tests_count}</strong></small></td>
                        <td style="text-align:right;vertical-align:middle; padding: 2px 4px;">{patient.labpatientinvoice.total_cost}</td>
                        {f'<td colspan="2" style="text-align:right; vertical-align:middle;padding: 2px 4px;">{patient.labpatientinvoice.total_discount}</td>' if not doctor_settings.discount_by_doctor else ''}
                        {f'<td style="text-align:right;vertical-align:middle; padding: 2px 4px;">{patient.labpatientinvoice.total_lab_discount}</td>' if doctor_settings.discount_by_doctor else ''}
                        {f'<td style="text-align:right; vertical-align:middle;padding: 2px 4px;">{patient.labpatientinvoice.total_ref_discount}</td>' if doctor_settings.discount_by_doctor else ''}
                        <td style="text-align:right;vertical-align:middle; padding: 2px 4px;">{patient.labpatientinvoice.total_price}</td>
                        <td style="text-align:right;vertical-align:middle; padding: 2px 4px;">{patient.labpatientinvoice.total_paid}</td>
                        <td style="text-align:right;vertical-align:middle; padding: 2px 4px;">{patient.labpatientinvoice.total_refund}</td>
                        <td style="text-align:right;vertical-align:middle; padding: 2px 4px;">{patient.labpatientinvoice.total_due}</td>                                    
                        <td style="text-align:right; vertical-align:middle;padding: 2px 4px;">{ref_doctor_amount(patient)}</td>
                    </tr>
                    '''
                    content += patient_row_content

                else:
                    pass

            content += f'''
                <tr>

                    <th colspan="6" style="text-align:right;padding: 2px 4px;">Totals</th>
                    <th style="text-align:right; padding: 2px 4px;">{sum(getattr(patient.labpatientinvoice, 'total_cost', 0) for patient in patients)}</th>
                    {f'<th colspan="2" style="text-align:right; padding: 2px 4px;">{sum(getattr(patient.labpatientinvoice, 'total_discount', 0) for patient in patients)}</th>' if not doctor_settings.discount_by_doctor else ''}
                    {f'<th style="text-align:right; padding: 2px 4px;">{sum(getattr(patient.labpatientinvoice, 'total_lab_discount', 0) for patient in patients)}</th>' if doctor_settings.discount_by_doctor else ''}
                    {f'<th style="text-align:right; padding: 2px 4px;">{sum(getattr(patient.labpatientinvoice, 'total_ref_discount', 0) for patient in patients)}</th>' if doctor_settings.discount_by_doctor else ''}
                    <th style="text-align:right; padding: 2px 4px;">{sum(getattr(patient.labpatientinvoice, 'total_price', 0) for patient in patients)}</th>
                    <th style="text-align:right; padding: 2px 4px;">{sum(getattr(patient.labpatientinvoice, 'total_paid', 0) for patient in patients)}</th>
                    <th style="text-align:right; padding: 2px 4px;">{sum(getattr(patient.labpatientinvoice, 'total_refund', 0) for patient in patients)}</th>
                    <th style="text-align:right; padding: 2px 4px;">{sum(getattr(patient.labpatientinvoice, 'total_due', 0) for patient in patients)}</th>
                    <th style="text-align:right; padding: 2px 4px;">{total_ref_amount}</th>
                </tr>
                </tbody>
            </table>
            '''

            final_content = content

            # return HttpResponse(final_content)
            return Response({'html_content': final_content})
        else:
            start_date = datetime.strptime(str(start_date), "%Y-%m-%d")

            end_date = datetime.combine(end_date, datetime.max.time())
            consulting_time_period = f"{start_date.strftime('%d-%m-%y')}" if start_date == end_date else f"{start_date.strftime('%d-%m-%y')} to {end_date.strftime('%d-%m-%y')}"

            report_printed_on = datetime.now().strftime('%d-%m-%y %I:%M %p')


            if start_date == end_date:
                end_date = end_date + timedelta(days=1)

            lab_technicians = LabTechnicians.objects.filter(
                added_on__range=[start_date, end_date],
                consulting_doctor=doctor
            )
            lab_tests = LabPatientTests.objects.filter(
                id__in=lab_technicians.values_list('LabPatientTestID', flat=True),
                department__department_flow_type__id=2
            )
            patients = Patient.objects.filter(id__in=lab_tests.values_list('patient_id', flat=True))
            patients_referred = patients.count()

            def consultation_amount(patient):
                total_consult_amount = Decimal('0.00')
                for test in lab_tests.filter(patient=patient).exclude(status_id__name='Cancelled'):
                    referral_model = ReferralAmountForDoctor.objects.filter(
                        referral_doctor=doctor, lab_test=test.LabGlobalTestId).first()

                    if referral_model:
                        referral_amount = Decimal(test.price * (referral_model.referral_amount * Decimal(
                            '0.01'))) if referral_model.is_percentage else Decimal(referral_model.referral_amount)
                    else:
                        referral_amount = Decimal('0.00')

                    total_consult_amount += referral_amount

                total_consult_amount = total_consult_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                return total_consult_amount

            total_consultation_amount = sum(consultation_amount(patient) for patient in patients)
            content = f'''
                    <table class="table table-hover inter-font rounded-3 overflow-hidden border border-3 pt-5" id="excelReport" border="1" style="border-collapse: collapse; border-spacing: 0; width: 100%;font-size:12px;">                                    
                        <tbody>
                        <tr><th colspan="14" style="padding: 2px 4px;background-color:#e6e8e6; font-size: 18px;text-align:center; ">Doctor Payout Report</th></tr>                    
                        <tr><td colspan="7" style="padding: 2px 4px;">Consultant Doctor Name: <strong>{doctor.name}</strong> </td><td colspan="7" style="padding: 2px 4px;">Report Time Period: <strong> {consulting_time_period}</strong></td></tr>
                        <tr><td colspan="7" style="padding: 2px 4px;">Consultant Doctor Mobile: {doctor.mobile_number} </td><td colspan="7" style="padding: 2px 4px;">No. of Patients consulted: {patients_referred} </td></tr>
                        <tr><td colspan="7" style="padding: 2px 4px;">Consultant Doctor Area: {doctor.geo_area} </td><td colspan="7" style="padding: 2px 4px;">Total payout for the period:<strong> Rs.{total_consultation_amount}</strong> </td></tr>                                
                        <tr><td colspan="7" style="padding: 2px 4px;"></td><td colspan="7" style="padding: 2px 4px;">Report printed On: {report_printed_on}</td></tr>
                        <tr><td colspan="14" style="height:20px;"></td></tr>
                        <tr>
                            <th style="text-align:center; padding: 2px 4px;background-color:#e6e8e6;">S.No</th>
                            <th style="text-align:center; padding: 2px 4px;background-color:#e6e8e6;">Visit ID</th>
                            <th style="text-align:center; padding: 2px 4px;background-color:#e6e8e6;">Reg Date</th>
                            <th style="text-align:left; padding: 2px 4px;background-color:#e6e8e6;">Name</th>                        
                            <th colspan="2" style="text-align:left; padding: 2px 4px;background-color:#e6e8e6;">Tests Names</th>
                            <th style="text-align:right; padding: 2px 4px;background-color:#e6e8e6;">Total Amount</th>                                    
                            <th style="text-align:right; padding: 2px 4px;background-color:#e6e8e6;">Pay Amount</th>
                        </tr>                    
                    '''
            for i, patient in enumerate(patients, start=1):
                total_amount = sum(
                    test.price for test in lab_tests.filter(patient=patient).exclude(status_id__name='Cancelled'))
                patient_tests_count = lab_tests.filter(patient=patient).exclude(status_id__name='Cancelled').count()
                if patient_tests_count >= 1:
                    patient_row_content = f'''
                    <tr>
                        <td style="text-align:center;vertical-align:middle; padding: 2px 4px;">{i}</td>
                        <td style="text-align:left;vertical-align:middle; padding: 2px 4px;font-size:12px;white-space: nowrap;">{patient.visit_id}</td>
                        <td style="text-align:left;vertical-align:middle; padding: 2px 4px;font-size:12px;white-space: nowrap;">{patient.added_on.strftime('%d/%m/%y')}</td>
                        <td style="text-align:left;vertical-align:middle; padding: 2px 4px;font-size:12px;">{patient.name}</td>                            
                        <td colspan="2" style="text-align:left;vertical-align:middle; padding: 2px 4px; white-space: pre-line;line-height:14px;"><small>{", \n".join(test.name for test in lab_tests.filter(patient=patient).exclude(status_id__name='Cancelled'))}. <br> <strong style="line-height:16px;">Total Tests : {patient_tests_count}</strong></small></td>
                        <td style="text-align:right;vertical-align:middle; padding: 2px 4px;">{total_amount}</td>                              
                        <td style="text-align:right; vertical-align:middle;padding: 2px 4px;">{consultation_amount(patient)}</td>
                    </tr>
                    '''
                    content += patient_row_content

                else:
                    pass

            total_price = sum(
                test.price
                for patient in patients
                for test in lab_tests.filter(patient=patient).exclude(status_id__name='Cancelled')
            )
            content += f'''
            <tr>
                <th colspan="6" style="text-align:right;padding: 2px 4px;">Totals</th>
                <th style="text-align:right; padding: 2px 4px;">{total_price}</th>
                <th style="text-align:right; padding: 2px 4px;">{total_consultation_amount}</th>
            </tr>
            </tbody>
            </table>
            '''

            final_content = content
            return Response({'html_content': final_content})
            # return HttpResponse(final_content)


class TestCollectionReportView(generics.ListCreateAPIView):
    def get(self, request, *args, **kwargs):
        try:
            action = self.request.query_params.get('action')
            ids = self.request.query_params.get('ids')

            if ids:
                ids = ids.split(',')

            start_date = self.request.query_params.get('start_date')
            end_date = self.request.query_params.get('end_date')

            start_date = datetime.strptime(str(start_date), "%Y-%m-%d")
            end_date = datetime.strptime(str(end_date), "%Y-%m-%d")
            end_date = end_date + timezone.timedelta(days=1)

            time_period = f"{start_date.strftime('%d-%m-%y')}" if start_date == end_date else f"{start_date.strftime('%d-%m-%y')} to {end_date.strftime('%d-%m-%y')}"

            report_printed_on = datetime.now().strftime('%d-%m-%y %I:%M %p')

            if action == 'tests_details':
                tests_data=[]
                tests = LabPatientTests.objects.filter(is_package_test=False,added_on__gte=start_date,
                                              added_on__lte=end_date).exclude(status_id__name='Cancelled')

                lab_global_test_counts = tests.values("LabGlobalTestId").annotate(patients_count=Count("patient")).order_by("-patients_count")

                page = self.paginate_queryset(lab_global_test_counts)
                if page is not None:
                    for test in lab_global_test_counts:
                        global_test_obj = LabGlobalTests.objects.get(pk=test['LabGlobalTestId'])
                        tests_data.append({**LabGlobalTestsSerializer(global_test_obj).data,
                                           "patients_count": test['patients_count'],
                                           "total_amount": test['patients_count'] * global_test_obj.price})
                    return self.get_paginated_response(tests_data)


            if action == 'packages_details':
                packages_data=[]
                tests = LabPatientPackages.objects.filter(is_package_cancelled=False,added_on__gte=start_date,
                                              added_on__lte=end_date)

                lab_global_packages_counts = tests.values("LabGlobalPackageId").annotate(patients_count=Count("patient")).order_by("-patients_count")

                page = self.paginate_queryset(lab_global_packages_counts)
                if page is not None:
                    for package in lab_global_packages_counts:
                        global_package_obj = LabGlobalPackages.objects.get(pk=package['LabGlobalPackageId'])
                        packages_data.append({**LabGlobalPackagesGetSerializer(global_package_obj).data,
                                           "patients_count": package['patients_count'],
                                           "total_amount": package['patients_count'] * global_package_obj.offer_price})
                    return self.get_paginated_response(packages_data)


            if action == 'tests_print':
                global_tests = LabGlobalTests.objects.filter(id__in=ids)
                final_content = ""
                for global_test in global_tests:
                    tests = LabPatientTests.objects.filter(is_package_test=False, LabGlobalTestId=global_test, added_on__gte=start_date,
                                                  added_on__lte=end_date).exclude(status_id__name='Cancelled').select_related('LabGlobalTestId', 'patient')

                    total_price = tests.aggregate(total_price=Sum('price'))['total_price']

                    content = f'''
                                <table class="table table-hover inter-font rounded-3 overflow-hidden border border-3 pt-5" id="excelReport" border="1" style="border-collapse: collapse; border-spacing: 0; width: 100%;font-size:12px;">                                    
                                    <tbody>
                                        <tr>
                                            <th colspan="7" style="padding: 2px 4px;background-color:#e6e8e6; font-size: 18px;text-align:center;">Test Collection Report</th>
                                        </tr>                    
                                        <tr>
                                            <td colspan="7" style="padding: 2px 4px;">Test Name: <strong>{global_test.name}</strong> </td>
                                        </tr>
                                        <tr>
                                            <td colspan="7" style="padding: 2px 4px;">Report Time Period: <strong> {time_period}</strong></td>
                                        </tr>
                                        <tr>
                                            <td colspan="7" style="padding: 2px 4px;">Report printed On: {report_printed_on}</td>
                                        </tr>
                                        
                                    <tr>
                                        <th style="text-align:center; padding: 2px 4px;background-color:#e6e8e6;">S.No</th>
                                        <th style="text-align:center; padding: 2px 4px;background-color:#e6e8e6;">Visit ID</th>
                                        <th style="text-align:center; padding: 2px 4px;background-color:#e6e8e6;">Reg Date</th>
                                        <th style="text-align:left; padding: 2px 4px;background-color:#e6e8e6;">Name</th>                        
                                        <th style="text-align:center; padding: 2px 4px;background-color:#e6e8e6;">Mobile Number</th>
                                        <th style="text-align:left; padding: 2px 4px;background-color:#e6e8e6;">Ref. Doctor</th>
                                        <th style="text-align:right; padding: 2px 4px;background-color:#e6e8e6;">Amount</th>
                                    </tr>                    
                                '''

                    for i,test in enumerate(tests,start=1):
                        patient = test.patient
                        content += f'''
                                        <tr>
                                            <td style="text-align:center; padding: 2px 4px;">{i}</td>
                                            <td style="text-align:center; padding: 2px 4px;">{patient.visit_id}</td>
                                            <td style="text-align:center; padding: 2px 4px;">{patient.added_on.strftime('%d-%m-%y')}</td>
                                            <td style="text-align:left; padding: 2px 4px;">{patient.name}</td>                        
                                            <td style="text-align:center; padding: 2px 4px;">{patient.mobile_number}</td>
                                            <td style="text-align:left; padding: 2px 4px;">{patient.referral_doctor.name if patient.referral_doctor else "SELF"}</td>
                                            <td style="text-align:right; padding: 2px 4px;">{test.price}</td>
                                        </tr>
                                        '''

                    end_content = f'''
                                        <tr>
                                            <th colspan="6" style="text-align:right;padding: 2px 4px;">Totals</th>
                                            <th style="text-align:right; padding: 2px 4px;">{total_price}</th>
                                        </tr>
                                        <tr class="extraSpaceAtEnd">
                                            <th colspan="7" style="text-align:right;padding: 2px 4px;height:20px;"></th>
                                        </tr>
                                    </tbody>
                                </table>
                                <div class="extraSpaceAtEndDiv" style="height:50px;"></div>
                                    '''
                    content+=end_content
                    final_content+=content

                return Response({"html_content":final_content})
                # return HttpResponse(final_content)

            if action == 'packages_print':
                global_packages = LabGlobalPackages.objects.filter(id__in=ids)
                final_content = ""
                for global_package in global_packages:
                    packages = LabPatientPackages.objects.filter(is_package_cancelled=False, LabGlobalPackageId=global_package,
                                                           added_on__gte=start_date, added_on__lte=end_date).select_related('LabGlobalPackageId', 'patient')

                    total_price = packages.aggregate(total_price=Sum('offer_price'))['total_price']

                    content = f'''
                                <table class="table table-hover inter-font rounded-3 overflow-hidden border border-3 pt-5" id="excelReport" border="1" style="border-collapse: collapse; border-spacing: 0; width: 100%;font-size:12px;">                                    
                                    <tbody>
                                        <tr>
                                            <th colspan="7" style="padding: 2px 4px;background-color:#e6e8e6; font-size: 18px;text-align:center;">Package Collection Report</th>
                                        </tr>                    
                                        <tr>
                                            <td colspan="7" style="padding: 2px 4px;">Test Name: <strong>{global_package.name}</strong> </td>
                                        </tr>
                                        <tr>
                                            <td colspan="7" style="padding: 2px 4px;">Report Time Period: <strong> {time_period}</strong></td>
                                        </tr>
                                        <tr>
                                            </td><td colspan="7" style="padding: 2px 4px;">Report printed On: {report_printed_on}</td>
                                        </tr>
    
                                    <tr>
                                        <th style="text-align:center; padding: 2px 4px;background-color:#e6e8e6;">S.No</th>
                                        <th style="text-align:center; padding: 2px 4px;background-color:#e6e8e6;">Visit ID</th>
                                        <th style="text-align:center; padding: 2px 4px;background-color:#e6e8e6;">Reg Date</th>
                                        <th style="text-align:left; padding: 2px 4px;background-color:#e6e8e6;">Name</th>                        
                                        <th style="text-align:center; padding: 2px 4px;background-color:#e6e8e6;">Mobile Number</th>
                                        <th style="text-align:left; padding: 2px 4px;background-color:#e6e8e6;">Ref. Doctor</th>
                                        <th style="text-align:right; padding: 2px 4px;background-color:#e6e8e6;">Amount</th>
                                    </tr>                    
                                '''

                    for i, package in enumerate(packages, start=1):
                        patient = package.patient
                        content += f'''
                                        <tr>
                                            <td style="text-align:center; padding: 2px 4px;">{i}</td>
                                            <td style="text-align:center; padding: 2px 4px;">{patient.visit_id}</td>
                                            <td style="text-align:center; padding: 2px 4px;">{patient.added_on.strftime('%d-%m-%y')}</td>
                                            <td style="text-align:left; padding: 2px 4px;">{patient.name}</td>                        
                                            <td style="text-align:left; padding: 2px 4px;">{patient.mobile_number}</td>
                                            <td style="text-align:right; padding: 2px 4px;">{patient.referral_doctor.name if patient.referral_doctor else "SELF"}</td>
                                            <td style="text-align:right; padding: 2px 4px;">{package.offer_price}</td>
                                        </tr>
                                        '''

                    end_content = f'''
                                        <tr>
                                            <th colspan="6" style="text-align:right;padding: 2px 4px;">Totals</th>
                                            <th style="text-align:right; padding: 2px 4px;">{total_price}</th>
                                        </tr>
                                        <tr class="extraSpaceAtEnd">
                                            <th colspan="7" style="text-align:right;padding: 2px 4px;height:20px;"></th>
                                        </tr>
                                    </tbody>
                                </table>
                                <div class="extraSpaceAtEndDiv" style="height:50px;"></div>
                                '''
                    content += end_content
                    final_content += content

                return Response({"html_content":final_content})
                # return HttpResponse(final_content)
        except Exception as error:
            print(error)
            return Response({"Error":f"{error}"}, status=status.HTTP_400_BAD_REQUEST)

class PrintTemplateViewset(viewsets.ModelViewSet):
    queryset = PrintTemplate.objects.all()
    serializer_class = PrintTemplateSerializer

    def get_queryset(self):
        queryset = PrintTemplate.objects.filter(print_template_type__is_active=True)
        query = self.request.query_params.get('q', None)
        type_id = self.request.query_params.get('type', None)
        if query:
            queryset = queryset.filter(name__icontains=query)
        if type_id is not None:
            queryset = queryset.filter(print_template_type__id=type_id)
        queryset = queryset.order_by('print_template_type__id', 'added_on')

        return queryset


class PrintDataTemplateViewset(viewsets.ModelViewSet):
    serializer_class = PrintDataTemplateSerializer

    def get_queryset(self):
        query = self.request.query_params.get('q')
        if query:
            queryset = PrintDataTemplate.objects.filter(print_template_id=query)
        else:
            queryset = PrintDataTemplate.objects.all()
        return queryset


class UserCollectionReportsList(generics.ListAPIView):
    serializer_class = PrintTemplateSerializer

    def get_queryset(self):
        template_type_list = PrintTemplateType.objects.filter(
            name__in=['User Collection - Shift Wise Report', 'User Collection - Consolidated Report'])
        print_templates = PrintTemplate.objects.filter(print_template_type__in=template_type_list, is_default=True)
        queryset = print_templates.order_by('print_template_type_id')
        return queryset


class DownloadTestReportViewset(viewsets.ModelViewSet):
    serializer_class = GenerateTestReportSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return []

    def list(self=None, request=None, test_ids=None, client_id=None, letterhead=None, water_mark=None,sourcing_lab_for_settings=None, *args, **kwargs):
        if request:
            test_ids = self.request.query_params.get('t', None)
            client_id = self.request.query_params.get('c', None)
            letterhead = self.request.query_params.get('lh', None)
            water_mark = self.request.query_params.get('mark', None)
            sourcing_lab_for_settings = self.request.query_params.get('sourcing_lab_for_settings', None)


        else:
            print(test_ids, client_id)

        client_id = decode_id(client_id)
        test_ids = test_ids.split(',')
        test_ids = [decode_id(tid) for tid in test_ids]
        tests_ordering = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(test_ids)])
        client = Client.objects.get(pk=client_id)

        with schema_context(client.schema_name):
            lab_patient_tests = LabPatientTests.objects.filter(id__in=test_ids).order_by(tests_ordering)
            test = lab_patient_tests.first()

            patient = test.patient

            if patient.referral_lab:
                sourcing_lab = patient.referral_lab
                if sourcing_lab.credit_payment:
                    pass
                else:
                    paid_percentage = patient.labpatientinvoice.total_paid / patient.labpatientinvoice.total_price * 100
                    if paid_percentage >= sourcing_lab.min_print_amount:
                        pass
                    else:
                        return Response({"Error": "Minimum payment to print is not paid!"},
                                        status=status.HTTP_400_BAD_REQUEST)
            else:
                pass

            try:
                try:
                    from weasyprint import HTML
                except ImportError as import_error:
                    HTML = None

                pdf_files = []
                overall_content = ""
                final_header_content = ""
                final_footer_content = ""
                for test in lab_patient_tests:
                    details = get_lab_patient_details(test_id=test.id, client_id=client_id)
                    lab_patient_test = details['lab_patient_test']
                    is_word_report = details['is_word_report']
                    client_report_settings = details['client_report_settings']

                    search_pattern = r"\{(.*?)\}"
                    expression_pattern = r"\[\[(.*?)\]\]"


                    if is_word_report:
                        template_type = PrintTemplateType.objects.get(name='Lab Test Report (Word)')
                    else:
                        if lab_patient_test.department.name == "Medical Examination":
                            template_type = PrintTemplateType.objects.get(name='Medical Examination Report')
                        else:
                            template_type = PrintTemplateType.objects.get(name='Lab Test Report (Fixed)')

                    print_template = PrintTemplate.objects.filter(print_template_type=template_type,
                                                                  is_default=True).first()
                    template = None
                    if print_template:
                        template = PrintDataTemplate.objects.get(print_template=print_template)
                    else:
                        return Response({"Error": "Please check whether default template is selected or not!"},
                                        status=status.HTTP_400_BAD_REQUEST)


                    if is_word_report:
                        word_report = LabPatientWordReportTemplate.objects.filter(
                            LabPatientTestID=lab_patient_test).first()
                        template_content = "<div>" + word_report.report + "</div>"
                    else:
                        template_content = template.data

                    intermediate_content = re.sub(search_pattern,  lambda match: replace_tag(match=match,
                                                                                            lab_patient_test=lab_patient_test,
                                                                                            client_report_settings=client_report_settings,
                                                                                            details=details), template_content)
                    modified_content = re.sub(expression_pattern, lambda match: evaluate_expression(match=match, details=details),
                                           intermediate_content)

                    # header content
                    if is_word_report:
                        template_header_content = template.header if template.header else ""
                        intermediate_header_content = re.sub(search_pattern, lambda match: replace_tag(match=match,
                                                                                            lab_patient_test=lab_patient_test,
                                                                                            client_report_settings=client_report_settings,
                                                                                            details=details), template_header_content)
                        final_header_content = re.sub(expression_pattern, lambda match: evaluate_expression(match=match, details=details),
                                                         intermediate_header_content)
                    else:
                        template_header_content = template.header if template.header else ""
                        intermediate_header_content = re.sub(search_pattern,  lambda match: replace_tag(match=match,
                                                                                            lab_patient_test=lab_patient_test,
                                                                                            client_report_settings=client_report_settings,
                                                                                            details=details), template_header_content)
                        final_header_content = re.sub(expression_pattern, lambda match: evaluate_expression(match=match, details=details),
                                                         intermediate_header_content)

                    # footer content
                    template_footer_content = template.footer if template.footer else ""
                    intermediate_footer_content = re.sub(search_pattern, lambda match: replace_tag(match=match,
                                                                                            lab_patient_test=lab_patient_test,
                                                                                            client_report_settings=client_report_settings,
                                                                                            details=details), template_footer_content)
                    final_footer_content = re.sub(expression_pattern, lambda match: evaluate_expression(match=match, details=details),
                                                     intermediate_footer_content)

                    # doctor signature template content
                    signature_content = details['signature_content']
                    sign_intermediate_content = re.sub(search_pattern,  lambda match: replace_tag(match=match,
                                                                                            lab_patient_test=lab_patient_test,
                                                                                            client_report_settings=client_report_settings,
                                                                                            details=details), signature_content)
                    sign_final_content = re.sub(expression_pattern, lambda match: evaluate_expression(match=match, details=details), sign_intermediate_content)

                    if sign_final_content:
                        sign_final_content = f'''
                                                <tr>
                                                    <td colspan="4">{sign_final_content}</td>
                                                </tr>
                        
                                                '''


                    if not is_word_report and modified_content and test.department.name!='Medical Examination':
                        modified_content = f'''
                                            <div style="font-family:{letterhead_settings.default_font.value}">
                                                <table style="border-collapse:collapse;width:100%;">
                                                    <tbody>
                                                    {modified_content + sign_final_content}
                                                    </tbody>
                                                </table>
                                            </div>

                                            '''

                        # modified_content = f'''
                        #                             <table style="border-collapse:collapse;width:100%;">
                        #                                 <tbody>
                        #                                 {modified_content + sign_final_content}
                        #                                 </tbody>
                        #                             </table>
                        #
                        #                         '''
                    # final_content = f'''<div class="break-page">{modified_content}</div>'''
                    final_content = modified_content


                    patient = details['patient']
                    business = BusinessProfiles.objects.get(organization_name=client.name)

                    if sourcing_lab_for_settings:
                        letterhead_settings = SourcingLabLetterHeadSettings.objects.get(sourcing_lab=sourcing_lab_for_settings)
                        background_image_url = letterhead_settings.letterhead if letterhead_settings.letterhead else ""
                        letter_head_settings_content = SourcingLabLetterHeadSettingsSerializer(letterhead_settings).data

                    else:
                        letterhead_settings = details['letterhead_settings']
                        background_image_url = business.b_letterhead if business.b_letterhead else ""
                        letter_head_settings_content = LetterHeadSettingsSerializer(letterhead_settings).data

                    watermark_in_print = ""
                    if water_mark == 'true':
                        watermark_in_print = f'''
                            @left-top{{
                            content: 'NOT FOR PRINT';
                            font-size: 50px;
                            font-weight: 600;
                            color:#0000003D;
                            text-wrap:nowrap;
                            z-index: 100000;
                            padding-left: 50px;
                            filter: opacity(0.2);
                            transform: rotate(45deg);
                            font-family: "Arial", Tahoma, sans-serif;
                            }}'''

                    letterhead_value = str(letterhead).strip().lower()
                    if letterhead_value == 'false':
                        background_image = ""
                    else:
                        background_image = f'''background-image: url('{background_image_url}');'''
                    page_margin = f'''margin: {letterhead_settings.header_height}px {letterhead_settings.margin_right}px {letterhead_settings.footer_height}px {letterhead_settings.margin_left}px ;'''
                    page_padding = f'''padding: {letterhead_settings.header_height + template.header_height}px {letterhead_settings.margin_right}px {letterhead_settings.footer_height}px {letterhead_settings.margin_left}px ;'''

                    current_datetime = timezone.now()
                    formatted_datetime = current_datetime.strftime("%I:%M %p")
                    report_name = f"{patient.name}_{lab_patient_test.name}_{formatted_datetime}.pdf"


                    if test.department.name == 'Medical Examination':
                        final_header_content = ""
                        page_padding = f'''padding: {letterhead_settings.header_height}px {letterhead_settings.margin_right}px {letterhead_settings.footer_height}px {letterhead_settings.margin_left}px ;'''

                    if HTML is not None:
                        header = f'''
                        <html>
                        <head>
                        <meta charset="UTF-8">
                        <meta http-equiv="X-UA-Compatible" content="IE=edge">
                        <meta name="viewport" content="width=device-width, initial-scale=1.0">
                        <link href="https://cdn.jsdelivr.net/npm/devexpress-richedit@24.1.5/dist/dx.richedit.min.css" rel="stylesheet">
                        <script defer src="https://unpkg.com/pagedjs/dist/paged.polyfill.js"></script>
                        <style>
                        body {{
                            margin: 0;
                            padding: 0;
                            {background_image}
                            background-size: 210mm 297mm;
                            background-repeat: repeat-y;
                        }}
                        .header {{
                            position: running(headerContent);
                            width: {793 - letterhead_settings.margin_right - letterhead_settings.margin_left}px;
                            padding: {letterhead_settings.header_height}px {letterhead_settings.margin_right}px 0px {letterhead_settings.margin_left}px;
                        }}
                        .hide_from_pdf{{display: none;}}
                        @media print {{
                            .hide_from_pdf{{display: none;}}
                            .header {{
                                position: running(headerContent);
                                padding: {letterhead_settings.header_height}px {letterhead_settings.margin_right}px 0px {letterhead_settings.margin_left}px;
                            }}
                            body {{
                                margin: 0;
                                padding: 0;
                                {background_image}

                                background-size: 210mm 297mm;
                                background-repeat: repeat-y;
                            }}
                            @page {{
                                size: 210mm 297mm;
                                margin: 0;
                                {page_padding}
                            }}
                            @page {{
                                {watermark_in_print}
                                @top-center {{
                                    content: element(headerContent);
                                    vertical-align: top;
                                }}
                            }}
                            .break-page {{
                                break-after: page;
                            }}
                            .dxrePageArea {{
                                position: relative;
                                break-after: page;
                                background-color: transparent !important;
                            }}
                        }}
                        </style>
                        </head>
                        <body>
                            <div class="header">
                            {final_header_content}
                            </div>
                        '''

                        footer = '</body></html>'

                        # if page number required add this
                        #                 @bottom - center
                        #
                        #                 {{
                        #                     content: 'Page 'counter(page) ' of 'counter(pages);
                        #                 font - size: 12
                        #                 pt;
                        #                 font - weight: 600;
                        #                 color:  # 000000;
                        #                 }}

                        final_content = header + f'<div class = "content">{final_content}</div>' + footer
                        overall_content += final_content
                        pdf_file = HTML(string=final_content).write_pdf()
                        pdf_files.append(pdf_file)

                pdf_binaries = pdf_files
                pdf_writer = PdfWriter()

                # Loop through each binary PDF and merge them
                for pdf_binary in pdf_binaries:
                    pdf_reader = PdfReader(BytesIO(pdf_binary))  # Read the binary data into a PdfReader
                    for page in pdf_reader.pages:
                        pdf_writer.add_page(page)  # Add each page from the PDF to the writer

                # Write the merged PDF to a binary stream
                merged_pdf_binary = BytesIO()
                pdf_writer.write(merged_pdf_binary)

                # Convert the merged PDF binary to base64
                pdf_base64 = base64.b64encode(merged_pdf_binary.getvalue()).decode('utf-8')


                pdf_base64_with_data = f"data:application/pdf;base64,{pdf_base64}"

                # response = HttpResponse(pdf_file, content_type='application/pdf')
                # response['Content-Disposition'] = 'attachment; filename="tests_report.pdf"'
                # return response

                if HTML is not None:
                    return Response({
                                    "pdf": True,
                                     "report": "TestReport",
                                     "report_name": report_name,
                                     "pdf_base64": pdf_base64_with_data,
                                     "html_content": overall_content,
                                     "letter_head_settings_content": letter_head_settings_content,
                                     })
                else:
                    return Response({"pdf": False,
                                     "report": "TestReport",
                                     "report_name": report_name,
                                     "pdf_base64": overall_content,
                                     'html_content': overall_content,
                                     "header": final_header_content,
                                     "footer": final_footer_content,
                                     "letter_head_settings_content": letter_head_settings_content})
                # return HttpResponse(final_header_content + final_content + final_footer_content)
            except Exception as e:
                print(e)
                return Response(f'{e}')


class DownloadBulkPatientsReportsViewSet(viewsets.ModelViewSet):
    serializer_class = GenerateTestReportSerializer
    permission_classes = [permissions.AllowAny]

    def list(self, request=None, patient_ids=None, client_id=None, letterhead=None, *args, **kwargs):
        if request:
            client_id = self.request.query_params.get('c', None)
            patient_ids = self.request.query_params.get('p', None)

        if client_id is None or patient_ids is None:
            return Response({"Error": "Client ID and Patient IDs must be provided!"},
                            status=status.HTTP_400_BAD_REQUEST)

        patient_ids = patient_ids.split(',')
        patient_ids = [decode_id(pid) for pid in patient_ids]
        client_id = decode_id(client_id)

        final_content = ""

        client = Client.objects.get(pk=client_id)

        with schema_context(client.schema_name):
            for patient_id in patient_ids:
                lab_patient_tests = LabPatientTests.objects.filter(patient__id=patient_id, status_id__in=[3, 7, 17])

                test_ids = [test.id for test in lab_patient_tests]
                download_api = DownloadTestReportViewset()
                hashed_test_ids = ','.join(encode_id(test_id) for test_id in test_ids)

                try:
                    download_response = download_api.list(
                        test_ids=hashed_test_ids,
                        client_id=encode_id(client_id),
                        letterhead=letterhead
                    )
                    html_content = download_response.data.get('html_content', None)

                    if html_content:
                        final_content += html_content

                except Exception as error:
                    return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

        pdf_file = HTML(string=final_content).write_pdf()
        # response = HttpResponse(pdf_file, content_type='application/pdf')
        # response['Content-Disposition'] = 'attachment; filename="tests_report.pdf"'
        # return response

        pdf_base64 = base64.b64encode(pdf_file).decode('utf-8')

        report_name = "Multiple_Patient_Test_Reports.pdf"

        return Response({
            "pdf": True,
            "report_name": report_name,
            "pdf_base64": f"data:application/pdf;base64,{pdf_base64}",
            "html_content": final_content,
        })


class GeneratePatientRefundViewset(viewsets.ModelViewSet):
    serializer_class = GeneratePatientRefundSerializer

    def get_queryset(self):
        return []

    def create(self, request=None, patient_id=None, client_id=None, printed_by=None, refund_id=None, *args, **kwargs):
        if request:
            patient_id = self.request.query_params.get('patient_id', None)
            client_id = self.request.query_params.get('client_id', None)
            printed_by = self.request.query_params.get('printed_by', None)
            refund_id = self.request.query_params.get('refund_id', None)

            if patient_id and client_id:
                pass
            else:
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer_data = serializer.validated_data
                patient_id = serializer_data.get('patient_id')
                client_id = serializer_data.get('client_id')
                printed_by = serializer_data.get('printed_by')
                refund_id = serializer_data.get('refund_id')
            print(patient_id, client_id, printed_by)
        else:
            print(patient_id, client_id, printed_by)

        try:
            patient = Patient.objects.get(pk=patient_id)
            client = Client.objects.get(pk=client_id)
            bProfile = BusinessProfiles.objects.get(organization_name=client.name)
            b_address = BusinessAddresses.objects.filter(b_id=bProfile.id).first()
            appointment_details = AppointmentDetails.objects.filter(patient=patient).first()
            contacts = BContacts.objects.filter(b_id=bProfile, is_primary=True).first()
            labpatientinvoice = LabPatientInvoice.objects.filter(patient=patient).first()

            labpatienttests = LabPatientTests.objects.filter(patient=patient).first()
            receipt = LabPatientReceipts.objects.filter(invoiceid=labpatientinvoice).first()

            created_by = patient.created_by
            printed_by = LabStaff.objects.get(pk=printed_by)

            refund = LabPatientRefund.objects.get(pk=refund_id)

            refund_barcode_img = generate_barcode_image(refund.id)

            refund_barcode_img = (
                f'<img  class="refundBarcode" alt ="refund_barcode_img" src ="{refund_barcode_img}" style="height:30px; min-width:100px;'
                f'padding:0 10px 0 0"/>') if refund_barcode_img is not None else ""

            template_type = PrintTemplateType.objects.get(name='Refund')
            print_template = PrintTemplate.objects.get(print_template_type=template_type, is_default=True)
            template = PrintDataTemplate.objects.get(print_template=print_template)

            report_printed_on = datetime.now().strftime('%d-%m-%y %I:%M %p')

            details = {
                'patient': patient,
                'bProfile': bProfile,
                'appointment_details': appointment_details,
                'contacts': contacts,
                'labpatientinvoice': labpatientinvoice,
                'labpatienttests': labpatienttests,
                'receipt': receipt,
                'refund_barcode_img': refund_barcode_img,
                "report_printed_on": report_printed_on,
                "refund": refund,
                "b_letterhead": bProfile.b_letterhead,
                "created_by": created_by,
                "printed_by": printed_by,
                'b_address': b_address
            }

        except Exception as error:
            print(error)
            return Response(f"Error fetching details: {error}", status=400)

        # print(f"details : {details}")

        search_pattern = r"\{(.*?)\}"
        expression_pattern = r"\[\[(.*?)\]\]"

        # Dictionary to hold totals for tags dynamically
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
                    refund_objects = LabPatientRefund.objects.filter(patient=details['patient'])

                    if refund_objects.exists():
                        if tag_name == "RefundNo":
                            related_objects = LabPatientRefund.objects.filter(id=refund.id)
                            return "".join(
                                f'<p style="margin: 3px 0px;">{obj.refund_id}</p>' for obj in related_objects)

                        if tag_name == "RefundMode":
                            related_objects = LabPatientRefund.objects.filter(id=refund.id)

                            return "".join(
                                f'<p style="margin: 3px 0px;">{obj.refund_mode.name}</p>'
                                for obj in related_objects)

                        if tag_name == "RefundDate":
                            related_objects = LabPatientRefund.objects.filter(id=refund.id)

                            return "".join(
                                f'<span style="margin: 3px 0px;">{obj.added_on.strftime('%d-%m-%y, %I:%M %p')}</span>'
                                for obj
                                in
                                related_objects)

                        if tag_name == "RefundRemark":
                            related_objects = LabPatientRefund.objects.filter(id=refund.id)
                            return "".join(
                                f'<p style="margin: 3px 0px;">{obj.remarks_from_staff if obj.remarks_from_staff else ""}</p>'
                                for obj in related_objects)

                        if tag_name == "RefundAmountInWords":
                            related_objects = LabPatientRefund.objects.filter(id=refund.id)
                            total_refund_amount = sum(obj.refund for obj in related_objects)
                            amount_in_words = num2words(total_refund_amount, lang='en_IN').title()
                            return f'({amount_in_words} Rupees only)'

                        if tag_name == "RefundAmount":
                            related_objects = LabPatientRefund.objects.filter(id=refund.id)
                            return "".join(
                                f'<p style="margin: 3px 0px;">₹ {obj.refund}</p>' for obj in related_objects)

                        if tag_name == "TotalRefundAmount":
                            related_objects = LabPatientRefund.objects.filter(id=refund.id)
                            total_refund_amount = sum(obj.refund for obj in related_objects)
                            return f'₹ {total_refund_amount}'
                    else:
                        # Exclude refund tags if no refund objects exist
                        return ""
                else:
                    # Handle single item fetch and formula evaluation as before
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
                # If the tag doesn't exist, return a placeholder indicating so
                return f"{tag_name} not found!"

                # New function to evaluate and replace expressions

        def evaluate_expression(match):
            expression = match.group(1)  # Capture the content without double brackets
            try:
                # Ensure you sanitize or validate the expression if using eval() directly poses a security risk
                result = str(eval(expression, {'__builtins__': None}, {'details': details}))
                return result
            except Exception as eval_error:
                print(f"Error in expression evaluation: {eval_error}")
                return "[Error]"  # Placeholder for any evaluation error

        # Now, add the new snippet here to replace total placeholders with actual total values
        def replace_total(match):
            tag_name = match.group(1)  # Extract the tag name
            total_value = tag_totals.get(tag_name, 0)  # Get the total value from tag_totals
            return str(total_value)  # Return the total value as a string

        template_content = template.data
        # First, replace tags with their values
        intermediate_content = re.sub(search_pattern, replace_tag, template_content)

        # Then, evaluate and replace expressions
        modified_content = re.sub(expression_pattern, evaluate_expression, intermediate_content)

        # Use the regular expression to find and replace total placeholders
        final_content = re.sub(expression_pattern, replace_total, modified_content)

        # Header
        template_header_content = template.header if template.header else ""
        intermediate_header_content = re.sub(search_pattern, replace_tag, template_header_content)
        modified_header_content = re.sub(expression_pattern, evaluate_expression, intermediate_header_content)
        final_header_content = re.sub(expression_pattern, replace_total, modified_header_content)

        # Footer
        template_footer_content = template.footer if template.footer else ""
        intermediate_footer_content = re.sub(search_pattern, replace_tag, template_footer_content)
        modified_footer_content = re.sub(expression_pattern, evaluate_expression, intermediate_footer_content)
        final_footer_content = re.sub(expression_pattern, replace_total, modified_footer_content)

        return Response({'html_content': final_content,
                         "header": final_header_content,
                         "footer": final_footer_content})
        # return HttpResponse(final_header_content+final_content+final_footer_content)


class DoctorSharedTestReportViewset(viewsets.ModelViewSet):
    serializer_class = DoctorSharedTestReportSerializer

    def get_queryset(self):
        return []

    def create(self, request=None, test_id=None, client_id=None, doctor=None, *args, **kwargs):
        if request:
            test_id = self.request.query_params.get('test_id', None)
            client_id = self.request.query_params.get('client_id', None)
            entered_doctor = self.request.query_params.get('doctor', None)

            if test_id and client_id and entered_doctor:
                pass
            else:
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer_data = serializer.validated_data
                test_id = serializer_data.get('test_id')
                client_id = serializer_data.get('client_id')
                entered_doctor = serializer_data.get('doctor')

        else:
            pass

        client = Client.objects.get(pk=client_id)
        with schema_context(client.schema_name):
            try:
                lab_patient_test = LabPatientTests.objects.get(pk=test_id)
                patient = lab_patient_test.patient
                client = Client.objects.get(pk=client_id)
                entered_doctor = HealthOProUser.objects.get(pk=entered_doctor)
                obj = DoctorSharedReport.objects.get(test=test_id, client_id=client_id)
                saved_doctor = obj.doctor
                if saved_doctor != entered_doctor:
                    return Response('Doctor does not have access to get this report',
                                    status=status.HTTP_400_BAD_REQUEST)
                bProfile = BusinessProfiles.objects.get(organization_name=client.name)
                appointment_details = AppointmentDetails.objects.filter(patient=patient).first()
                contacts = BContacts.objects.filter(b_id=bProfile, is_primary=True).first()
                labpatientinvoice = LabPatientInvoice.objects.filter(patient=patient).first()
                # labpatienttests = LabPatientTests.objects.filter(patient=patient).first()
                receipt = LabPatientReceipts.objects.filter(invoiceid=labpatientinvoice).first()

                lab_technician = LabTechnicians.objects.filter(LabPatientTestID=lab_patient_test).first()
                is_word_report = lab_technician.is_word_report if lab_technician is not None else False
                lab_phlebotomist = LabPhlebotomist.objects.filter(LabPatientTestID=lab_patient_test).first()

                sample_barcode_img = generate_barcode_image(
                    f"{lab_phlebotomist.assession_number}|{lab_patient_test.department.name}") if lab_phlebotomist is not None else None
                # print(barcode_img)

                sample_barcode_img = (
                    f'<img alt ="barcode_img" src ="{sample_barcode_img}" style="height:30px; min-width:150px; '
                    f'padding:0 10px 0 0"/>') if sample_barcode_img is not None else "NA"
                # print(barcode_img)
                # printed_by = HealthOProUser.objects.get(pk=printed_by_id)
                hashed_test_id = test_id
                hashed_client_id = client_id
                # hashed_test_id = hash_id(test_id)
                # hashed_client_id = hash_id(client_id)
                mobile_number = patient.mobile_number
                hashed_mobile_number = mobile_number
                # hashed_mobile_number = hash_id(mobile_number)
                domain_obj = Domain.objects.first()
                domain_url = domain_obj.url

                qr_data = f"{domain_url}/patient_report/?test_id={hashed_test_id}&client_id={hashed_client_id}&mobile_number={hashed_mobile_number}"
                qr = qrcode.make(qr_data)
                qr_buffer = BytesIO()
                qr.save(qr_buffer, format='PNG')
                qr_base64 = base64.b64encode(qr_buffer.getvalue()).decode()
                qrcode_img = f"data:image/png;base64,{qr_base64}"
                qrcode_img = (f'<img alt ="qrcode_img" src ="{qrcode_img}" style="height:100px; min-width:100px; '
                              f'padding:0 10px 0 0"/>') if qrcode_img is not None else "NA"
                # print(qrcode_img)
                lab_technician_sign = None
                consulting_doctor_sign = None

                if lab_technician:
                    lab_technician_sign = lab_technician.report_created_by.signature if lab_technician.report_created_by else None
                    consulting_doctor_sign = lab_technician.consulting_doctor.signature_for_consulting if lab_technician.consulting_doctor else None

                lab_technician_sign = (
                    f'<img alt ="lab_technician_sign" src ="{lab_technician_sign}" style="height:30px; min-width:100px; '
                    f'padding:0 10px 0 0"/>') if lab_technician_sign is not None else ""

                consulting_doctor_sign = (
                    f'<img alt ="consulting_doctor_sign" src ="{consulting_doctor_sign}" style="height:30px; '
                    f'min-width:100px;'
                    f'padding:0 10px 0 0"/>') if consulting_doctor_sign is not None else ""

                lab_technician_remarks = LabTechnicianRemarks.objects.filter(LabPatientTestID=lab_patient_test).first()

                try:
                    word_report = LabPatientWordReportTemplate.objects.filter(LabPatientTestID=lab_patient_test).first()
                except Exception as error:
                    print(error)
                    word_report = None

                word_report_content = word_report.report if word_report is not None else ''

                test_report_date = ''

                report_printed_on = datetime.now().strftime('%d-%m-%y %I:%M %p')

                try:
                    if lab_technician:
                        if lab_technician.is_word_report:
                            report = LabPatientWordReportTemplate.objects.filter(
                                LabPatientTestID=lab_patient_test).first()
                            test_report_date = report.added_on
                        else:
                            report = LabPatientFixedReportTemplate.objects.filter(
                                LabPatientTestID=lab_patient_test).first()
                            test_report_date = report.added_on
                except Exception as error:
                    print(error)

                payment_status = None

                if labpatientinvoice.total_paid == 0:
                    payment_status = f"<span style='color:red;'>UNPAID</span>"
                elif 0 < labpatientinvoice.total_paid < labpatientinvoice.total_due:
                    payment_status = f"<span style='color:blue;'>PARTIALLY PAID</span>"
                elif labpatientinvoice.total_paid >= labpatientinvoice.total_due:
                    payment_status = f"<span style='color: green;'>FULLY PAID</span>"

                details = {
                    'lab_patient_test': lab_patient_test,
                    'patient': patient,
                    'bProfile': bProfile,
                    'appointment_details': appointment_details,
                    'contacts': contacts,
                    'labpatientinvoice': labpatientinvoice,
                    # 'labpatienttests': labpatienttests,
                    'receipt': receipt,
                    'sample_barcode_img': sample_barcode_img,
                    'payment_status': payment_status,
                    'lab_phlebotomist': lab_phlebotomist,
                    'lab_technician': lab_technician,
                    "lab_technician_remarks": lab_technician_remarks,
                    'word_report_content': word_report_content,
                    'test_report_date': test_report_date,
                    "report_printed_on": report_printed_on,
                    "lab_technician_sign": lab_technician_sign,
                    "consulting_doctor_sign": consulting_doctor_sign,
                    "b_letterhead": bProfile.b_letterhead,
                    "qrcode_img": qrcode_img
                }

            except Exception as error:
                print(error)
                return Response(f"Error fetching details: {error}", status=400)

            # print(f"details : {details}")

            search_pattern = r"\{(.*?)\}"
            expression_pattern = r"\[\[(.*?)\]\]"

            # Dictionary to hold totals for tags dynamically
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
                        if tag_name == "LabTestParameter":
                            related_objects = LabPatientFixedReportTemplate.objects.filter(
                                LabPatientTestID=lab_patient_test)

                            return "".join(
                                f'<p style="margin: 3px 5px;">{obj.parameter}</p>' for obj in related_objects)

                        if tag_name == "LabTestValue":
                            related_objects = LabPatientFixedReportTemplate.objects.filter(
                                LabPatientTestID=lab_patient_test)
                            return "".join(f'<p style="margin: 3px 5px;">{obj.value}</p>' for obj in related_objects)

                        if tag_name == "LabTestUnits":
                            related_objects = LabPatientFixedReportTemplate.objects.filter(
                                LabPatientTestID=lab_patient_test)
                            return "".join(f'<p style="margin: 3px 5px;">{obj.units}</p>' for obj in related_objects)

                        if tag_name == "LabTestReferralInterval":
                            related_objects = LabPatientFixedReportTemplate.objects.filter(
                                LabPatientTestID=lab_patient_test)
                            return "".join(
                                f'<p style="margin: 3px 5px;">{obj.referral_range}</p>' for obj in related_objects)
                        if tag_name == "LabTestGroups":
                            related_objects = LabPatientFixedReportTemplate.objects.filter(
                                LabPatientTestID=lab_patient_test).order_by('ordering')
                            for obj in related_objects:
                                print(obj.parameter)

                            groups = related_objects.values_list('group', flat=True).distinct()

                            groups_content = ""

                            group = ""
                            groups_content += f'<tr><td colspan="4" style="font-size:16px;"><strong>{group}</strong></td></tr>'

                            for data in related_objects:
                                if group != data.group:
                                    group = data.group
                                    if group != "":
                                        groups_content += f'<tr><td colspan="4" style="font-size:16px; "> <br> </td></tr>'
                                        groups_content += f'<tr><td colspan="4" style="font-size:16px; "><strong>{group}</strong></td></tr>'
                                    else:
                                        groups_content += f'<tr><td colspan="4" style="font-size:16px; "> <br> </td></tr>'
                                data_content = (f'<tr style="font-size:14px; ">'
                                                f'<td style="text-align:left;width:40%;">{data.parameter}</td>'
                                                f'<td style="text-align:center;width:15%;">{data.value}</td>'
                                                f'<td style="text-align:center;width:15%;">{data.units}</td>'
                                                f'<td style="text-align:center;width:30%;">{data.referral_range}</td>'
                                                f'</tr>')

                                if data.value:
                                    groups_content += data_content

                                    if data.method:
                                        groups_content += (f'<tr>'
                                                           f'<td style="color:#333333; font-size:12px;">(<italic>METHOD:{data.method}</italic>)</td>'
                                                           f'</tr>')

                            groups_content = (f'<table border="0" cellspacing="0" style="border-collapse:collapse; '
                                              f'width:96%"><tbody>{groups_content}</tbody></table>')

                            return groups_content

                    else:
                        # Handle single item fetch and formula evaluation as before
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
                    # If the tag doesn't exist, return a placeholder indicating so
                    return f"{tag_name} not found!"

                    # New function to evaluate and replace expressions

            def evaluate_expression(match):
                expression = match.group(1)  # Capture the content without double brackets
                try:
                    # Ensure you sanitize or validate the expression if using eval() directly poses a security risk
                    result = str(eval(expression, {'__builtins__': None}, {'details': details}))
                    return result
                except Exception as eval_error:
                    print(f"Error in expression evaluation: {eval_error}")
                    return "[Error]"  # Placeholder for any evaluation error

            if not is_word_report:
                template_type = PrintTemplateType.objects.get(name='Lab Test Report (Fixed)')

            else:
                template_type = PrintTemplateType.objects.get(name='Lab Test Report (Word)')

            print_template = PrintTemplate.objects.filter(print_template_type=template_type, is_default=True).first()
            template = None
            if print_template:
                template = PrintDataTemplate.objects.get(print_template=print_template)
            else:
                return Response({"Error": "Please check whether default template is selected or not!"},
                                status=status.HTTP_400_BAD_REQUEST)

            html_content = template.data

            template_content = html_content
            # First, replace tags with their values
            intermediate_content = re.sub(search_pattern, replace_tag, template_content)

            # Then, evaluate and replace expressions
            modified_content = re.sub(expression_pattern, evaluate_expression, intermediate_content)

            # Now, add the new snippet here to replace total placeholders with actual total values
            def replace_total(match):
                tag_name = match.group(1)  # Extract the tag name
                total_value = tag_totals.get(tag_name, 0)  # Get the total value from tag_totals
                return str(total_value)  # Return the total value as a string

            # Use the regular expression to find and replace total placeholders
            final_content = re.sub(expression_pattern, replace_total, modified_content)

            # return HttpResponse(final_content)
            return Response({'html_content': final_content})


class DownloadPatientReceiptViewset(viewsets.ModelViewSet):
    serializer_class = GeneratePatientReceiptSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return []

    def list(self, request=None, patient_id=None, client_id=None, receipt_id=None, *args, **kwargs):
        if request:
            patient_id = self.request.query_params.get('p', None)
            client_id = self.request.query_params.get('c', None)
            receipt_id = self.request.query_params.get('r', None)

            patient_id = decode_id(patient_id)
            client_id = decode_id(client_id)
            receipt_id = decode_id(receipt_id)

            if client_id and (patient_id or receipt_id):
                pass
            else:
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer_data = serializer.validated_data
                patient_id = serializer_data.get('patient_id')
                client_id = serializer_data.get('client_id')
                receipt_id = serializer_data.get('receipt_id')
        else:
            pass
        client = Client.objects.get(pk=client_id)
        with schema_context(client.schema_name):
            try:
                try:
                    from weasyprint import HTML
                except ImportError as import_error:
                    HTML = None

                patient = Patient.objects.get(pk=patient_id)
                client = Client.objects.get(pk=client_id)
                bProfile = BusinessProfiles.objects.get(organization_name=client.name)
                appointment_details = AppointmentDetails.objects.filter(patient=patient).first()
                contacts = BContacts.objects.filter(b_id=bProfile, is_primary=True).first()
                labpatientinvoice = LabPatientInvoice.objects.filter(patient=patient).first()
                labpatienttests = LabPatientTests.objects.filter(patient=patient).first()
                labpatientpackages = LabPatientPackages.objects.filter(patient=patient).first()

                letterhead_settings = LetterHeadSettings.objects.filter(client=client).first()

                if receipt_id:
                    receipt = LabPatientReceipts.objects.get(pk=receipt_id)
                else:
                    receipt = LabPatientReceipts.objects.filter(invoiceid=labpatientinvoice).first()
                invoice_barcode_img = generate_barcode_image(labpatientinvoice.id)
                receipt_barcode_img = generate_barcode_image(receipt.id)

                invoice_barcode_img = (
                    f'<img  class="invoiceBarcode" alt ="invoice_barcode_img" src ="{invoice_barcode_img}" style="height:30px; min-width:100px;'
                    f'padding:0 10px 0 0"/>') if invoice_barcode_img is not None else ""

                receipt_barcode_img = (
                    f'<img  class="receiptBarcode" alt ="receipt_barcode_img" src ="{receipt_barcode_img}" style="height:30px; min-width:100px;'
                    f'padding:0 10px 0 0"/>') if receipt_barcode_img is not None else ""

                template_type = PrintTemplateType.objects.get(name='Receipt')
                print_template = PrintTemplate.objects.get(print_template_type=template_type, is_default=True)
                template = PrintDataTemplate.objects.get(print_template=print_template)

                created_by = patient.created_by

                report_printed_on = datetime.now().strftime('%d-%m-%y %I:%M %p')

                payment_status = None

                if labpatientinvoice.total_paid == 0:
                    payment_status = f"<span style='color:red;'>UNPAID</span>"
                elif 0 < labpatientinvoice.total_paid < labpatientinvoice.total_due:
                    payment_status = f"<span style='color:blue;'>PARTIALLY PAID</span>"
                elif labpatientinvoice.total_paid >= labpatientinvoice.total_due:
                    payment_status = f"<span style='color: green;'>FULLY PAID</span>"

                paid_amount_of_receipt = sum(payment.paid_amount for payment in receipt.payments.all())

                paid_amount_in_words = f"{num2words(paid_amount_of_receipt, lang='en_IN').title()} rupees only"

                details = {
                    'patient': patient,
                    'bProfile': bProfile,
                    'appointment_details': appointment_details,
                    'contacts': contacts,
                    'labpatientinvoice': labpatientinvoice,
                    'labpatienttests': labpatienttests,
                    'receipt': receipt,
                    'invoice_barcode_img': invoice_barcode_img,
                    'receipt_barcode_img': receipt_barcode_img,
                    'payment_status': payment_status,
                    "report_printed_on": report_printed_on,
                    "b_letterhead": bProfile.b_letterhead,
                    "created_by": created_by,
                    "paid_amount_of_receipt": paid_amount_of_receipt,
                    "paid_amount_in_words": paid_amount_in_words,
                    'labpatientpackages': labpatientpackages
                }

                receipts = LabPatientReceipts.objects.filter(patient=patient)

                all_tests_in_receipts = []
                all_packages_in_receipts = []
                all_payments_in_receipts = []

                if receipt.tests.exists() or receipt.packages.exists():
                    all_tests_in_receipts = receipt.tests.all()
                    all_packages_in_receipts = receipt.packages.all()
                    all_payments_in_receipts = receipt.payments.all()
                else:
                    for receipt_id in receipts:
                        tests = receipt_id.tests.all()
                        all_tests_in_receipts.extend(tests)

                        packages = receipt_id.packages.all()
                        all_packages_in_receipts.extend(packages)

                        payments = receipt_id.payments.all()
                        all_payments_in_receipts.extend(payments)

                refunds = LabPatientRefund.objects.filter(patient=patient)
                total_refund = sum(getattr(obj, 'refund', 0) for obj in refunds)

            except Exception as error:
                return Response(f"Error fetching details: {error}", status=400)

                # print(f"details : {details}")

            search_pattern = r"\{(.*?)\}"
            expression_pattern = r"\[\[(.*?)\]\]"

            # Dictionary to hold totals for tags dynamically
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
                        if tag_name == "LabTestSNo":
                            related_objects = receipt.tests.all() if receipt.tests.exists() else all_tests_in_receipts
                            test_snos = []
                            test_count = 0
                            for obj in related_objects:
                                test_count += 1
                                test_snos.append(test_count)
                            packages = receipt.packages.all() if receipt.packages.exists() else all_packages_in_receipts
                            for package in packages:
                                test_count += 1
                                test_snos.append(test_count)
                                tests = package.lab_tests.all()
                                for test in tests:
                                    test_snos.append(f"<br>")

                            return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in test_snos)

                        if tag_name == "LabTestNames":
                            related_objects = all_tests_in_receipts
                            test_names = []
                            if receipt.tests.exists() or receipt.packages.exists():
                                for obj in related_objects:
                                    test_names.append(obj.name)
                            else:
                                for obj in related_objects:
                                    if obj.status_id.name == 'Cancelled':
                                        test_names.append(f"{obj.name} ({obj.status_id.name})")
                                    else:
                                        test_names.append(obj.name)

                            packages = all_packages_in_receipts
                            if receipt.tests.exists() or receipt.packages.exists():
                                for package in packages:
                                    test_names.append(f"<strong>{package.name}</strong>")
                                    tests = package.lab_tests.all()

                                    for test in tests:
                                        test_names.append(f"{test.name}")
                            else:
                                for package in packages:
                                    tests = package.lab_tests.all()
                                    if all(test.status_id.name == "Cancelled" for test in tests):
                                        test_names.append(f"<strong>{package.name}</strong>(Cancelled)")
                                    else:
                                        test_names.append(f"<strong>{package.name}</strong>")

                                    for test in tests:
                                        test_names.append(f"{test.name}")

                            return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in test_names)

                        if tag_name == "LabTestPrice":
                            related_objects = receipt.tests.all() if receipt.tests.exists() else all_tests_in_receipts
                            test_prices = []

                            for obj in related_objects:
                                test_prices.append(obj.price)
                            packages = receipt.packages.all() if receipt.packages.exists() else all_packages_in_receipts
                            for package in packages:
                                test_prices.append(package.offer_price)
                                tests = package.lab_tests.all()
                                for test in tests:
                                    test_prices.append(f"<br>")

                            return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in test_prices)

                        if tag_name == "TotalLabTestPrice":
                            related_objects = receipt.tests.all() if receipt.tests.exists() else all_tests_in_receipts
                            total_value = 0

                            if receipt.tests.exists() or receipt.packages.exists():
                                total_value = sum(getattr(obj, 'price', 0) for obj in related_objects)
                            else:
                                total_value = sum(getattr(obj, 'price', 0) for obj in related_objects if
                                                  getattr(obj.status_id, 'name', None) != "Cancelled")

                            packages = receipt.packages.all() if receipt.packages.exists() else all_packages_in_receipts

                            if receipt.tests.exists() or receipt.packages.exists():
                                total_value += sum(getattr(obj, 'offer_price', 0) for obj in packages)
                            else:
                                for package in packages:
                                    tests = package.lab_tests.all()
                                    if all(test.status_id.name == "Cancelled" for test in tests):
                                        pass
                                    else:
                                        total_value += package.offer_price

                            accumulate_tag_totals(tag_name, total_value)
                            return str(total_value)

                        if tag_name == "SubTotalOfReceipt":
                            related_objects = receipt.tests.all() if receipt.tests.exists() else all_tests_in_receipts
                            total_value = 0

                            if receipt.tests.exists() or receipt.packages.exists():
                                total_value = sum(getattr(obj, 'price', 0) for obj in related_objects)
                            else:
                                total_value = sum(getattr(obj, 'price', 0) for obj in related_objects if
                                                  getattr(obj.status_id, 'name', None) != "Cancelled")

                            packages = receipt.packages.all() if receipt.packages.exists() else all_packages_in_receipts

                            if receipt.tests.exists() or receipt.packages.exists():
                                total_value += sum(getattr(obj, 'offer_price', 0) for obj in packages)
                            else:
                                for package in packages:
                                    tests = package.lab_tests.all()
                                    if all(test.status_id.name == "Cancelled" for test in tests):
                                        pass
                                    else:
                                        total_value += package.offer_price

                            accumulate_tag_totals(tag_name, total_value)
                            return str(total_value)

                        if tag_name == "TotalDiscountOfReceipt":
                            related_objects = receipt.tests.all() if receipt.tests.exists() else all_tests_in_receipts
                            total_value = 0

                            if receipt.tests.exists() or receipt.packages.exists():
                                total_value = sum(getattr(obj, 'discount', 0) for obj in related_objects)
                            else:
                                total_value = sum(getattr(obj, 'discount', 0) for obj in related_objects if
                                                  getattr(obj.status_id, 'name', None) != "Cancelled")

                            accumulate_tag_totals(tag_name, total_value)
                            return str(total_value)

                        if tag_name == "TotalOfReceipt":

                            related_objects = receipt.tests.all() if receipt.tests.exists() else all_tests_in_receipts
                            total_price = 0

                            if receipt.tests.exists() or receipt.packages.exists():
                                total_price = sum(getattr(obj, 'price_after_discount', 0) for obj in related_objects)
                            else:
                                total_price = sum(getattr(obj, 'price_after_discount', 0) for obj in related_objects if
                                                  getattr(obj.status_id, 'name', None) != "Cancelled")

                            packages = receipt.packages.all() if receipt.packages.exists() else all_packages_in_receipts

                            if receipt.tests.exists() or receipt.packages.exists():
                                total_price += sum(getattr(obj, 'offer_price', 0) for obj in packages)
                            else:
                                for package in packages:
                                    tests = package.lab_tests.all()
                                    if all(test.status_id.name == "Cancelled" for test in tests):
                                        pass
                                    else:
                                        total_price += package.offer_price

                            accumulate_tag_totals(tag_name, total_price)
                            return str(total_price)

                        if tag_name == "TotalPaidOfReceipt":
                            related_objects = receipt.payments.all() if (
                                    receipt.tests.exists() or receipt.packages.exists()) else all_payments_in_receipts
                            total_value = sum(getattr(obj, 'paid_amount', 0) for obj in related_objects)
                            accumulate_tag_totals(tag_name, total_value)
                            return str(total_value)

                        if tag_name == "TotalDueOfReceipt":
                            related_objects = receipt.tests.all() if receipt.tests.exists() else all_tests_in_receipts
                            total_price = 0

                            if receipt.tests.exists() or receipt.packages.exists():
                                total_price = sum(getattr(obj, 'price_after_discount', 0) for obj in related_objects)
                            else:
                                total_price = sum(getattr(obj, 'price_after_discount', 0) for obj in related_objects if
                                                  getattr(obj.status_id, 'name', None) != "Cancelled")

                            packages = receipt.packages.all() if receipt.packages.exists() else all_packages_in_receipts

                            if receipt.tests.exists() or receipt.packages.exists():
                                total_price += sum(getattr(obj, 'offer_price', 0) for obj in packages)
                            else:
                                for package in packages:
                                    tests = package.lab_tests.all()
                                    if all(test.status_id.name == "Cancelled" for test in tests):
                                        pass
                                    else:
                                        total_price += package.offer_price

                            payments = receipt.payments.all() if (
                                    receipt.tests.exists() or receipt.packages.exists()) else all_payments_in_receipts

                            total_paid = sum(getattr(obj, 'paid_amount', 0) for obj in payments)

                            if receipt.tests.exists() or receipt.packages.exists():
                                total_due = total_price - (total_paid)
                            else:
                                total_due = total_price - (total_paid - total_refund)

                            return str(total_due)

                        if tag_name == "ReceiptNo":
                            related_objects = LabPatientReceipts.objects.filter(id=receipt.id) if (
                                    receipt.tests.exists() or receipt.packages.exists()) else LabPatientReceipts.objects.filter(
                                patient=patient)
                            receipt_ids = [
                                obj.Receipt_id
                                for obj in related_objects
                                for _ in range(obj.payments.count())
                            ]
                            return "".join(f'<p style="margin: 3px 0px;">{receipt_id}</p>' for receipt_id in
                                           receipt_ids)

                        if tag_name == "PaymentMode":
                            related_objects = LabPatientReceipts.objects.filter(id=receipt.id) if (
                                    receipt.tests.exists() or receipt.packages.exists()) else LabPatientReceipts.objects.filter(
                                patient=patient)
                            payment_modes = [payment.pay_mode.name for obj in related_objects for payment in
                                             obj.payments.all()]
                            return "".join(
                                f'<p style="margin: 3px 0px;">{mode}</p>' for mode in payment_modes)

                        if tag_name == "PaymentDate":
                            related_objects = LabPatientReceipts.objects.filter(id=receipt.id) if (
                                    receipt.tests.exists() or receipt.packages.exists()) else LabPatientReceipts.objects.filter(
                                patient=patient)
                            payment_dates = [
                                obj.added_on.strftime('%d-%m-%y, %I:%M %p')
                                for obj in related_objects
                                for _ in range(obj.payments.count())
                            ]
                            return "".join(
                                f'<p style="margin: 3px 0px;">{date}</p>' for date in payment_dates)

                        if tag_name == "PaymentAmount":
                            related_objects = LabPatientReceipts.objects.filter(id=receipt.id) if (
                                    receipt.tests.exists() or receipt.packages.exists()) else LabPatientReceipts.objects.filter(
                                patient=patient)
                            payment_amounts = [
                                sum(payment.paid_amount for payment in obj.payments.filter(pay_mode=mode))
                                for obj in related_objects
                                for mode in obj.payments.values_list('pay_mode', flat=True).distinct()
                            ]
                            return "".join(
                                f'<p style="margin: 3px 0px;">{amount}</p>' for amount in payment_amounts)

                        if tag_name == "PaymentRemark":
                            related_objects = LabPatientReceipts.objects.filter(id=receipt.id) if (
                                    receipt.tests.exists() or receipt.packages.exists()) else LabPatientReceipts.objects.filter(
                                patient=patient)
                            payment_remarks = [
                                obj.remarks
                                for obj in related_objects
                                for _ in range(obj.payments.count())
                            ]
                            return "".join(
                                f'<p style="margin: 3px 0px;">{payment_remark}</p>' for payment_remark in
                                payment_remarks)



                    else:
                        if tag.tag_formula:
                            try:
                                tag_value = str(eval(tag.tag_formula, {'details': details}))
                                return tag_value
                            except Exception as eval_error:
                                print(f"{tag_name} - Error in formula evaluation: {eval_error}")
                                return " "  # If null
                        else:
                            return f"No formula for {tag_name}"

                except Tag.DoesNotExist:
                    return f"{tag_name} not found!"

                    # New function to evaluate and replace expressions

            def evaluate_expression(match):
                expression = match.group(1)  # Capture the content without double brackets
                try:
                    # Ensure you sanitize or validate the expression if using eval() directly poses a security risk
                    result = str(eval(expression, {'__builtins__': None}, {'details': details}))
                    return result
                except Exception as eval_error:
                    print(f"Error in expression evaluation: {eval_error}")
                    return "[Error]"  # Placeholder for any evaluation error

            # Now, add the new snippet here to replace total placeholders with actual total values
            def replace_total(match):
                tag_name = match.group(1)  # Extract the tag name
                total_value = tag_totals.get(tag_name, 0)  # Get the total value from tag_totals
                return str(total_value)  # Return the total value as a string

            report_name = f"{patient.name}_{receipt.Receipt_id}.pdf"

            template_content = template.data
            # First, replace tags with their values
            intermediate_content = re.sub(search_pattern, replace_tag, template_content)

            # Then, evaluate and replace expressions
            modified_content = re.sub(expression_pattern, evaluate_expression, intermediate_content)

            # Use the regular expression to find and replace total placeholders
            final_content = re.sub(expression_pattern, replace_total, modified_content)

            # Header
            template_header_content = template.header if template.header else ""
            intermediate_header_content = re.sub(search_pattern, replace_tag, template_header_content)
            modified_header_content = re.sub(expression_pattern, evaluate_expression, intermediate_header_content)
            final_header_content = re.sub(expression_pattern, replace_total, modified_header_content)

            # Footer
            template_footer_content = template.footer if template.footer else ""
            intermediate_footer_content = re.sub(search_pattern, replace_tag, template_footer_content)
            modified_footer_content = re.sub(expression_pattern, evaluate_expression, intermediate_footer_content)
            final_footer_content = re.sub(expression_pattern, replace_total, modified_footer_content)

            total_content = final_header_content + final_content + final_footer_content

            letterhead_settings = LetterHeadSettings.objects.filter(client=client).first()
            letter_head_settings_content = LetterHeadSettingsSerializer(letterhead_settings).data

            background_image_url = bProfile.b_letterhead if letterhead_settings.display_letterhead else ""
            background_image = f'''background-image: url('{background_image_url}'); background-size: cover; background-position: center top;background-repeat:repeat-y; background-size:210mm 297mm;'''
            page_padding = f'''padding: {letterhead_settings.header_height}px {letterhead_settings.margin_right}px {letterhead_settings.footer_height}px {letterhead_settings.margin_left}px;'''

            if HTML is not None:
                header = f'''<!DOCTYPE html>
                            <html>
                            <head>
                            <meta charset="UTF-8">
                            <meta http-equiv="X-UA-Compatible" content="IE=edge">
                            <meta name="viewport" content="width=device-width, initial-scale=1.0">
                            <script defer src="https://unpkg.com/pagedjs/dist/paged.polyfill.js"></script>
                            <style>
                              @media print {{
                                @page {{
                                  size: 210mm 297mm;
                                  margin: 0;
                                  {background_image}
                                }}
                                body {{
                                  {page_padding}
                                  box-sizing: border-box;
                                }}
                                @bottom-center {{
                                  content: 'Page ' counter(page) ' of ' counter(pages);
                                  font-size: 12pt;
                                  font-weight: 600;
                                  color: #000000;
                                }}

                                .pagedjs_last_page @bottom-right,
                                .not_last_page @bottom-right {{
                                  visibility: hidden;
                                }}
                              }}
                            </style>
                            <script>
                            document.addEventListener("DOMContentLoaded", function() {{
                              PagedPolyfill.on('after', (flow) => {{
                                const totalPages = flow.total;
                                const pages = document.querySelectorAll(".pagedjs_page");
                                if (pages.length > 0) {{
                                  for (let i = 0; i < pages.length; i++) {{
                                    if (i === pages.length - 1) {{
                                      pages[i].classList.add("pagedjs_last_page");
                                    }} else {{
                                      pages[i].classList.add("not_last_page");
                                    }}
                                  }}
                                }}
                              }});
                            }});
                            </script>
                            </head>
                            <body style="font-family: Arial, Helvetica, sans-serif;">
                            '''

                footer = '</body></html>'

                # Assuming final_content contains the body content
                final_content = header + final_content + footer

                pdf_file = HTML(string=final_content).write_pdf()
                # Create the HTTP response with PDF content
                # response = HttpResponse(pdf_file, content_type='application/pdf')
                # response['Content-Disposition'] = 'attachment; filename="output.pdf"'
                # return response

                pdf_base64 = f"data:application/pdf;base64,{base64.b64encode(pdf_file).decode('utf-8')}"
                # Return the Base64 string as JSON response
                return Response({"pdf": True,
                                 "report": "Receipt",
                                 "report_name": report_name,
                                 "pdf_base64": pdf_base64,
                                 "letter_head_settings_content": letter_head_settings_content})

            else:
                return Response({"pdf": False,
                                 "report": "Receipt",
                                 "report_name": report_name,
                                 "pdf_base64": "",
                                 'html_content': final_content,
                                 "header": final_header_content,
                                 "footer": final_footer_content,
                                 "letter_head_settings_content": letter_head_settings_content})
                # return HttpResponse(final_header_content + final_content + final_footer_content)



class GetPrivilegeCardView(generics.ListCreateAPIView):
    serializer_class = GetPrivilegeCardSerializer

    def get_queryset(self):
        return []

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer_data = serializer.validated_data
        membership_id = serializer_data.get('membership_id')
        client_id = serializer_data.get('client_id')

        try:

            client = Client.objects.get(pk=client_id)
            bProfile = BusinessProfiles.objects.get(organization_name=client.name)
            membership = PrivilegeCardMemberships.objects.get(pk=membership_id)

            template_type = PrintTemplateType.objects.get(name='Privilege Card')
            print_template = PrintTemplate.objects.filter(print_template_type=template_type, is_default=True).first()
            if not print_template:
                return Response({"Error": "Print Template Does n't Exist!"}, status=status.HTTP_400_BAD_REQUEST)

            template = PrintDataTemplate.objects.get(print_template=print_template)

            card_owner = membership.card_holder

            card_owner_image = f'<img class="cardOwnerImage" alt ="card_owner_image" src ="{card_owner.profile_image}>"'

            report_printed_on = datetime.now().strftime('%d-%m-%y %I:%M %p')

            details = {
                'bProfile': bProfile,
                "b_letterhead": bProfile.b_letterhead,
                "membership": membership,
                "card_owner": card_owner,
                "card_owner_image": card_owner_image,
                "report_printed_on": report_printed_on
            }

            # print(details)

        except Exception as error:
            return Response(f"Error fetching details: {error}", status=400)

        search_pattern = r"\{(.*?)\}"
        expression_pattern = r"\[\[(.*?)\]\]"

        # Dictionary to hold totals for tags dynamically
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
                    if tag.is_collection:
                        # Handle fetching and formatting of all related data

                        if tag_name == "PrivilegeMemberBenefits":
                            member_benefits = f"Benefits:"

                            department_wise_benefits = PrivilegeCardsLabDepartmentsBenefits.objects.filter(
                                card=membership.card)

                            test_wise_benefits = PrivilegeCardsLabTestBenefits.objects.filter(card=membership.card)

                            tests_discount_benefit = PrivilegeCardsMembershipApplicableBenefits.objects.filter(
                                membership=membership, benefit__name='Lab Tests Discount').first()

                            free_usages = f"{tests_discount_benefit.free_usages if tests_discount_benefit.free_usages is not None else "Limitless"}"
                            discount_usages = f"{tests_discount_benefit.discount_usages if tests_discount_benefit.discount_usages is not None else "Limitless"}"

                            discount = f"{tests_discount_benefit.discount if tests_discount_benefit.discount is not None else ""}"

                            if test_wise_benefits:
                                discount = "Discounts given based on Specific Tests"

                            if department_wise_benefits:
                                discount = "Discounts given based on Specific Departments"

                            member_benefits = f'''
                            <table><tbody><tr><td><strong>{tests_discount_benefit.benefit.name}</strong></td></tr>
                                        <tr><td>Free Usages:     {free_usages}</td></tr>
                                        <tr><td>Discount Usages: {discount_usages}</td></tr>
                                        <tr><td>Discount:        {discount}</td></tr>
                                        </tbody></table>
                                                '''

                            return member_benefits

                else:
                    # Handle single item fetch and formula evaluation as before
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
                # If the tag doesn't exist, return a placeholder indicating so
                # return f"{tag_name} not found!"
                pass

                # New function to evaluate and replace expressions

        def evaluate_expression(match):
            expression = match.group(1)  # Capture the content without double brackets
            try:
                # Ensure you sanitize or validate the expression if using eval() directly poses a security risk
                result = str(eval(expression, {'__builtins__': None}, {'details': details}))
                return result
            except Exception as eval_error:
                print(f"Error in expression evaluation: {eval_error}")
                return "[Error]"  # Placeholder for any evaluation error

                # Now, add the new snippet here to replace total placeholders with actual total values

        def replace_total(match):
            tag_name = match.group(1)  # Extract the tag name
            total_value = tag_totals.get(tag_name, 0)  # Get the total value from tag_totals
            return str(total_value)  # Return the total value as a string

        template_content = template.data
        # First, replace tags with their values
        intermediate_content = re.sub(search_pattern, replace_tag, template_content)

        # Then, evaluate and replace expressions
        modified_content = re.sub(expression_pattern, evaluate_expression, intermediate_content)

        # Use the regular expression to find and replace total placeholders
        final_content = re.sub(expression_pattern, replace_total, modified_content)

        # Header
        template_header_content = template.header if template.header else ""
        intermediate_header_content = re.sub(search_pattern, replace_tag, template_header_content)
        modified_header_content = re.sub(expression_pattern, evaluate_expression, intermediate_header_content)
        final_header_content = re.sub(expression_pattern, replace_total, modified_header_content)

        # Footer
        template_footer_content = template.footer if template.footer else ""
        intermediate_footer_content = re.sub(search_pattern, replace_tag, template_footer_content)
        modified_footer_content = re.sub(expression_pattern, evaluate_expression, intermediate_footer_content)
        final_footer_content = re.sub(expression_pattern, replace_total, modified_footer_content)

        return Response({'html_content': final_content,
                         "header": final_header_content,
                         "footer": final_footer_content})
        # print(final_header_content+final_content+final_footer_content)
        # return HttpResponse(final_header_content + final_content + final_footer_content)


class GeneratePatientMedicalCertificateViewSet(viewsets.ModelViewSet):
    serializer_class = GeneratePatientMedicalCertificateSerializer

    def get_queryset(self):
        return []

    def create(self, request=None, patient_id=None, client_id=None, *args, **kwargs):
        if request:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer_data = serializer.validated_data
            patient_id = serializer_data.get('patient_id')
            client_id = serializer_data.get('client_id')
        else:
            print(patient_id, client_id)

        try:
            patient = Patient.objects.get(pk=patient_id)
            client = Client.objects.get(pk=client_id)
            bProfile = BusinessProfiles.objects.filter(organization_name=client.name).first()
            contacts = BContacts.objects.filter(b_id=bProfile, is_primary=True).first()
            template_type = PrintTemplateType.objects.get(name='Medical Examination Certificate')
            print_template = PrintTemplate.objects.get(print_template_type=template_type, is_default=True)
            template = PrintDataTemplate.objects.get(print_template=print_template)

            report_printed_on = datetime.now().strftime('%d-%m-%y %I:%M %p')

            details = {
                'patient': patient,
                'bProfile': bProfile,
                'contacts': contacts,
                "report_printed_on": report_printed_on
            }

        except Exception as error:
            print(error)
            return Response(f"Error fetching details: {error}", status=400)

        # print(f"details : {details}")

        search_pattern = r"\{(.*?)\}"
        expression_pattern = r"\[\[(.*?)\]\]"

        # Dictionary to hold totals for tags dynamically
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
                    pass

                else:
                    # Handle single item fetch and formula evaluation as before
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
                # If the tag doesn't exist, return a placeholder indicating so
                return f"{tag_name} not found!"

                # New function to evaluate and replace expressions

        def evaluate_expression(match):
            expression = match.group(1)  # Capture the content without double brackets
            try:
                # Ensure you sanitize or validate the expression if using eval() directly poses a security risk
                result = str(eval(expression, {'__builtins__': None}, {'details': details}))
                return result
            except Exception as eval_error:
                print(f"Error in expression evaluation: {eval_error}")
                return "[Error]"  # Placeholder for any evaluation error

        html_content = template.data
        # print(html_content)
        template_content = html_content
        # First, replace tags with their values
        intermediate_content = re.sub(search_pattern, replace_tag, template_content)

        # Then, evaluate and replace expressions
        modified_content = re.sub(expression_pattern, evaluate_expression, intermediate_content)

        # Now, add the new snippet here to replace total placeholders with actual total values
        def replace_total(match):
            tag_name = match.group(1)  # Extract the tag name
            total_value = tag_totals.get(tag_name, 0)  # Get the total value from tag_totals
            return str(total_value)  # Return the total value as a string

        final_content = re.sub(expression_pattern, replace_total, modified_content)

        return Response({'html_content': final_content})
        # return HttpResponse(final_content)
        # return render(request, 'print_invoice.html', {'content': final_content})


def get_rtf_content_for_word_report(test_id=None):
    test = LabPatientTests.objects.get(pk=test_id)
    patient_id = test.patient.id
    client_id = test.patient.client.id

    template_type = PrintTemplateType.objects.get(name='Lab Test Report (Word)')

    print_template = PrintTemplate.objects.filter(print_template_type=template_type,
                                                  is_default=True).first()
    template = PrintDataTemplate.objects.get(print_template=print_template)

    rtf_content = template.rtf_content

    # return rtf_content
    if not rtf_content:
        return ""
    try:
        details = get_lab_patient_details(test_id=test_id, client_id=client_id)
        # print(details, 'details')
        if details is None:
            return Response({"error": "Failed to retrieve lab patient details."}, status=400)

        lab_patient_test = details['lab_patient_test']

    except Exception as error:
        print(error)
        return Response(f"Error fetching details: {error}", status=400)

    search_pattern = r"\\{(.*?)\\\}"

    tags_dictionary = {}

    # Function to replace tags found by regex search
    def replace_tag(match):
        tag_name = match.group(1)  # Capture the content without braces
        # print(tag_name)

        try:
            tag = Tag.objects.get(tag_name__iexact='{' + tag_name + '}')
            # print(tag_name)

            # Check if the tag requires fetching a collection of items
            if tag.is_collection:
                tag_value = get_value_of_tag(tag_name=tag_name, lab_patient_test=lab_patient_test,)
                # print(tag_name, tag_value)
                tags_dictionary[f'{tag_name}'] = tag_value
                return tag_value
            else:
                # Handle single item fetch and formula evaluation as before
                if tag.tag_formula:
                    try:
                        tag_value = str(eval(tag.tag_formula, {'details': details}))
                        tags_dictionary[f'{tag_name}'] = tag_value
                        # print(tag_name, tag_value)
                        return tag_value
                    except Exception as eval_error:
                        print(f"{tag_name} - Error in formula evaluation: {eval_error}")
                        return tag_name
                else:
                    # If no formula, return a placeholder or a default value
                    return f"{tag_name}"

        except Tag.DoesNotExist:
            # If the tag doesn't exist, return a placeholder indicating so
            return f"{tag_name}"

    # RTF content
    template_rtf_content_base64 = rtf_content
    # Step 1: Decode the Base64-encoded RTF content
    # Ensure the Base64 string has correct padding
    missing_padding = len(template_rtf_content_base64) % 4
    if missing_padding:
        template_rtf_content_base64 += '=' * (4 - missing_padding)
    template_rtf_content = base64.b64decode(template_rtf_content_base64).decode('utf-8')
    final_rtf_content = re.sub(search_pattern, replace_tag, template_rtf_content)

    # Step 3: Re-encode the modified RTF content back to Base64
    final_rtf_content_base64 = base64.b64encode(final_rtf_content.encode('utf-8')).decode('utf-8')

    return final_rtf_content_base64


class ReplaceTemplateHeaderContent(generics.CreateAPIView):
    def create(self, request, *args, **kwargs):
        serializer_data = request.data
        header = serializer_data.get('header')
        report_type = serializer_data.get('report_type')

        if report_type == 'fixed':
            fixed_report = LabPatientFixedReportTemplate.objects.last()
            lab_patient_test = fixed_report.LabPatientTestID
        else:
            word_report = LabPatientWordReportTemplate.objects.last()
            lab_patient_test = word_report.LabPatientTestID

        search_pattern = r"\{(.*?)\}"
        expression_pattern = r"\[\[(.*?)\]\]"

        try:
            details = get_lab_patient_details(test_id=lab_patient_test.id, patient_id=lab_patient_test.patient,
                                              client_id=request.client.id)

            # print(details, 'at details')

        except Exception as error:
            print(error)
            return Response(f"Error fetching details: {error}", status=400)

        def replace_tag(match):
            tag_name = match.group(1)
            try:
                tag = Tag.objects.get(tag_name='{' + tag_name + '}')
                if tag.is_collection:
                    return get_value_of_tag(tag_name=tag_name, lab_patient_test=lab_patient_test)
                else:
                    if tag.tag_formula:
                        try:
                            tag_value = str(eval(tag.tag_formula, {'details': details}))
                            return tag_value
                        except Exception as eval_error:
                            print(f"{tag_name} - Error in formula evaluation: {eval_error}")
                            return " "
                    else:
                        return f"No formula for {tag_name}"
            except Tag.DoesNotExist:
                return f"{tag_name} not found!"

        def evaluate_expression(match):
            expression = match.group(1)
            try:
                result = str(eval(expression, {'__builtins__': None}, {'details': details}))
                return result
            except Exception as eval_error:
                print(f"Error in expression evaluation: {eval_error}")
                return "[Error]"

        template_header_content = header
        intermediate_header_content = re.sub(search_pattern, replace_tag, template_header_content)
        modified_header_content = re.sub(expression_pattern, evaluate_expression, intermediate_header_content)
        final_header_content = modified_header_content

        return Response({
            "html_content": final_header_content
        })


class PatientsReportsSendingViaEmailAPIView(APIView):
    def post(self, request):
        patient_ids = self.request.data.get('patients')
        client_id = request.client.id
        date = self.request.data.get('date')
        start_date = self.request.data.get('date_range_after')
        end_date = self.request.data.get('date_range_before')
        if not self.request.query_params:
            test_ids = self.request.data.get('test_ids')
            letterhead = self.request.data.get('lh')
            print(letterhead, test_ids)
        else:
            test_ids = self.request.query_params.get('test_ids')
            letterhead = self.request.query_params.get('lh')
            print(letterhead, test_ids)

        if patient_ids:
            patients = Patient.objects.filter(id__in=patient_ids)
            tests = LabPatientTests.objects.filter(patient__id__in=patients)
            test_ids = [test.id for test in tests]
        elif test_ids:
            test_ids = test_ids.split(',')
            patients = Patient.objects.filter(labpatienttests__id__in=test_ids).distinct()

        if not patients:
            return Response({"error": "No valid patient IDs found."}, status=status.HTTP_404_NOT_FOUND)

        patient = patients.first()
        download_api = DownloadTestReportViewset()
        hashed_test_ids = ','.join(encode_id(test_id) for test_id in test_ids)

        email_config = BusinessEmailDetails.objects.first()
        print(email_config, 'email')

        if email_config is None:
            return Response({"Error": 'Email details do not exist for this Diagnostic Center.'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            download_response = download_api.list(
                test_ids=hashed_test_ids,
                client_id=encode_id(client_id),
                letterhead=letterhead
            )

            base64_pdf = download_response.data.get('pdf_base64')
            if not base64_pdf:
                return Response({"Error": "PDF data is missing from the download response."},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            patients_names = [patient.name for patient in patients]
            configuration = Configuration()
            configuration.api_key['api-key'] = settings.SENDINBLUE_API_KEY
            api_instance = TransactionalEmailsApi(ApiClient(configuration))
            print(api_instance)

            base64_pdf = re.sub(r'^data:application\/pdf;base64,', '', base64_pdf)

            if patient_ids:
                if not patient.partner.company.email:
                    return Response({"Error": 'Company email is not Provided'}, status=status.HTTP_400_BAD_REQUEST)
                attachment = SendSmtpEmailAttachment(
                    content=base64_pdf,
                    name=f'Emp Test Reports.pdf'
                )

                send_smtp_email = SendSmtpEmail(
                    to=[{"email": patient.partner.company.email}],
                    sender={"email": email_config.email},
                    subject=f'Employee Test Reports dated {start_date} to {end_date}',
                    html_content=f'<p>Greetings for the day. Below test report attachments are for following employees:{','.join(patients_names)}</p>',
                    attachment=[attachment]
                )
                # print(send_smtp_email, 'send email')
            else:
                if not patient.email:
                    return Response({"Error": 'Patient email is not Provided'}, status=status.HTTP_400_BAD_REQUEST)

                current_datetime = timezone.now()
                formatted_time = current_datetime.strftime("%I:%M %p")
                attachment = SendSmtpEmailAttachment(
                    content=base64_pdf,
                    name=f'{patient.name}_{formatted_time}.pdf'
                )

                send_smtp_email = SendSmtpEmail(
                    to=[{"email": patient.email}],
                    sender={"email": email_config.email},
                    subject=f'{patient.name} Test Reports',
                    html_content=f'<p>Greetings for the day. Below test report attachments are for Patient:{','.join(patients_names)}</p>',
                    attachment=[attachment]
                )

            try:
                response = api_instance.send_transac_email(send_smtp_email)
                print(response, 'response')
                return Response({'message': 'Email sent successfully!'})

            except Exception as e:
                return Response({'Error': "Your Business Email is not verified as sender.Kindly contact Admin"},
                                status=status.HTTP_400_BAD_REQUEST)
                # return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(f"Failed to send email for {patient.name}: {str(e)}")




