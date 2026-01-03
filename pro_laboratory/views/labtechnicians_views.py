import base64
import logging
from django.core.files.base import ContentFile
from django_tenants.utils import schema_context
from rest_framework import viewsets, generics
from rest_framework.views import APIView
from django.db.models import Q, Value
from healtho_pro_user.models.users_models import Client
from pro_laboratory.models.client_based_settings_models import BusinessControls
from pro_laboratory.models.doctors_models import LabDoctors, DefaultsForDepartments
from pro_laboratory.models.global_models import LabReportsTemplates, LabFixedParametersReportTemplate, \
    LabWordReportTemplate, LabStaff, LabFixedReportNormalReferralRanges, LabStaffDefaultBranch
from pro_laboratory.models.labtechnicians_models import LabTechnicians, LabTechnicianRemarks, \
    LabPatientWordReportTemplate, LabPatientFixedReportTemplate
from pro_laboratory.models.patient_models import LabPatientTests, Patient, PatientPDFs
from pro_laboratory.models.universal_models import ActivityLogs, ChangesInModels
from pro_laboratory.serializers.labtechnicians_serializers import (LabTechnicianSerializer, \
    LabTechnicianRemarksSerializer, LabPatientWordReportTemplateSerializer, LabPatientFixedReportTemplateSerializer, \
    LabPatientTestFixedReportDeletionSerializer, LabTechnicianListSerializer, \
    LabPatientTestReportGenerationSerializer, ReferralDoctorSerializer)
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta
from django.utils import timezone
from pro_laboratory.views.universal_views import generate_test_report_content, get_rtf_content_for_word_report, \
    GenerateTestReportViewset, get_pdf_content
from pro_universal_data.models import ULabTestStatus, ULabReportType, MessagingTemplates, MessagingSendType
from pro_universal_data.views import send_and_log_sms, send_and_log_whatsapp_sms


# Setup a logger for this module
logger = logging.getLogger(__name__)


class LabTechniciansViewSet(viewsets.ModelViewSet):
    queryset = LabTechnicians.objects.all()
    serializer_class = LabTechnicianSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            lab_technician_instance = serializer.save()
            access_users_list = request.data.get('access', [])  # Assuming 'access' is sent in the request data
            lab_technician_instance.access.set(access_users_list)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        lab_technician_remarks_data = validated_data.pop('lab_technician_remarks', None)
        self.perform_update(serializer)

        if lab_technician_remarks_data:
            lab_patient_test = instance.LabPatientTestID
            added_by = validated_data.get('report_created_by', None)
            lab_technician_remark, created = LabTechnicianRemarks.objects.get_or_create(
                LabPatientTestID=lab_patient_test)
            lab_technician_remark.remark = lab_technician_remarks_data.get('remark', lab_technician_remark.remark)
            lab_technician_remark.added_by = added_by
            lab_technician_remark.save()

        serializer = LabTechnicianSerializer(instance)
        return Response(serializer.data)


class LabTechniciansListView(generics.ListAPIView):
    serializer_class = LabTechnicianListSerializer

    def get_queryset(self):
        query = self.request.query_params.get('q', None)
        sort = self.request.query_params.get('sort', None)
        id = self.request.query_params.get('id')
        status_ids = self.request.query_params.get('status_id')
        departments_details = self.request.query_params.get('departments', [])
        department_flowtype_query = self.request.query_params.get('department_flowtype')
        ref_doctor = self.request.query_params.get('ref_doctor', None)
        date = self.request.query_params.get('date', None)
        date_range_after = self.request.query_params.get('date_range_after', None)
        date_range_before = self.request.query_params.get('date_range_before', None)

        user = self.request.user

        controls = BusinessControls.objects.first()
        if controls and controls.multiple_branches:
            default_branch_obj = LabStaffDefaultBranch.objects.get(lab_staff__mobile_number=user.phone_number)
            default_branch = default_branch_obj.default_branch.all()
            queryset = LabTechnicians.objects.filter(LabPatientTestID__branch__in=default_branch)

        else:
            queryset = LabTechnicians.objects.all()

        if id:
            queryset=queryset.filter(pk=id)

        if status_ids:
            status_ids_list = status_ids.split(',')
            queryset = queryset.filter(LabPatientTestID__status_id__in=status_ids_list)

        if query:
            search_query = (
                    Q(LabPatientTestID__patient__name__icontains=query) |
                    Q(LabPatientTestID__name__icontains=query) |
                    Q(LabPatientTestID__phlebotomist__assession_number__icontains=query) |
                    Q(LabPatientTestID__patient__mr_no__icontains=query) |
                    Q(LabPatientTestID__patient__visit_id__icontains=query)

            )
            queryset = queryset.filter(search_query)

        if departments_details:
            departments = [department.strip() for department in departments_details.split(',') if department.strip()]
            department_query = Q(LabPatientTestID__department__id__in=departments)
            queryset = queryset.filter(department_query)

        if department_flowtype_query:
            department_flowtype = Q(LabPatientTestID__department__department_flow_type__name=department_flowtype_query)
            queryset = queryset.filter(department_flowtype)

        if date:
            queryset = queryset.filter(LabPatientTestID__patient__added_on__date=date)
        if date_range_after and date_range_before:
            try:
                start_date = datetime.strptime(date_range_after, "%Y-%m-%d")
                end_date = datetime.strptime(date_range_before, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
                queryset = queryset.filter(
                    LabPatientTestID__patient__added_on__range=[start_date, end_date]
                )
            except ValueError:
                pass

        if ref_doctor:
            queryset = queryset.filter(LabPatientTestID__patient__referral_doctor=ref_doctor)

        if sort == '-added_on':
            queryset = queryset.order_by('-added_on')
        elif sort == 'added_on':
            queryset = queryset.order_by('added_on')

        return queryset.distinct()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        paginator = self.pagination_class()  # Initialize pagination class
        page = paginator.paginate_queryset(queryset, request)

        serializer = self.get_serializer(page, many=True)

        patient_ids = list(set([item['LabPatientTestID']['patient']['id'] for item in serializer.data]))

        # Query referral doctors for these patients
        referral_doctors = LabDoctors.objects.filter(patient__in=patient_ids).distinct()
        referral_doctor_serializer = ReferralDoctorSerializer(referral_doctors, many=True)


        # Construct final response data
        response_data = {
            'count': paginator.page.paginator.count,
            'next': paginator.get_next_link(),
            'previous': paginator.get_previous_link(),
            'results': serializer.data,
            'referral_doctors': referral_doctor_serializer.data
        }

        return Response(response_data)


class LabTechnicianRemarksViewSet(viewsets.ModelViewSet):
    queryset = LabTechnicianRemarks.objects.all()
    serializer_class = LabTechnicianRemarksSerializer


class LabPatientWordReportTemplateViewSet(viewsets.ModelViewSet):
    queryset = LabPatientWordReportTemplate.objects.all()
    serializer_class = LabPatientWordReportTemplateSerializer


class LabPatientFixedReportTemplateViewSet(viewsets.ViewSet):
    def list(self, request):
        LabPatientTestID = request.query_params.get('LabPatientTestID', None)
        if LabPatientTestID is not None:
            queryset = LabPatientFixedReportTemplate.objects.filter(LabPatientTestID=LabPatientTestID)
            serializer = LabPatientFixedReportTemplateSerializer(queryset, many=True)
            return Response(serializer.data)
        else:
            return Response({'Error': 'LabPatientTestID is required'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


# **** we need to use this api to show the list and to do the update fixed parameters instead of using two seperate apis list and update *****
# class LabPatientFixedReportTemplateViewSet(viewsets.ModelViewSet):
#     queryset = LabPatientFixedReportTemplate.objects.all()
#     serializer_class = LabPatientFixedReportTemplateSerializer
#
#     def list(self, request):
#         LabPatientTestID = request.query_params.get('LabPatientTestID', None)
#         if LabPatientTestID is not None:
#             queryset = LabPatientFixedReportTemplate.objects.filter(LabPatientTestID=LabPatientTestID)
#             serializer = LabPatientFixedReportTemplateSerializer(queryset, many=True)
#             return Response(serializer.data)
#         else:
#             return Response({'Error': 'LabPatientTestID is required'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
#
#     def create(self, request, *args, **kwargs):
#         return Response({'Status': 'POST not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
#
#     def destroy(self, request, *args, **kwargs):
#         return Response({'Status': 'DELETE not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

#     def update(self, request, *args, **kwargs):
#         instance = self.get_object()
#         partial = kwargs.pop('partial', False)
#         serializer = self.get_serializer(instance, data=request.data, partial=partial)
#         serializer.is_valid(raise_exception=True)
#
#         labpatienttest = instance.LabPatientTestID
#         globaltest = instance.LabGlobalTestID
#
#         labtechnician = LabTechnicians.objects.filter(LabPatientTestID=labpatienttest).first()
#
#         self.perform_update(serializer)
#
#         if labtechnician.is_report_finished:
#             if labpatienttest.status_id.name == 'Processing':
#                 if labpatienttest.is_authorization:
#                     labpatienttest.status_id = ULabTestStatus.objects.get(name='Authorization Pending')
#                     labpatienttest.save()
#
#                 else:
#                     labpatienttest.status_id = ULabTestStatus.objects.get(name='Completed')
#                     labpatienttest.save()
#                     send_report_ready_sms(labpatienttest)
#
#             elif labpatienttest.status_id.name == 'Emergency (Processing)':
#                 if labpatienttest.is_authorization:
#                     labpatienttest.status_id = ULabTestStatus.objects.get(name='Emergency (Authorization Pending)')
#                     labpatienttest.save()

#                 else:
#                     labpatienttest.status_id = ULabTestStatus.objects.get(name='Emergency (Completed)')
#                     labpatienttest.save()
#                     send_report_ready_sms(labpatienttest)

#             elif labpatienttest.status_id.name == 'Urgent (Processing)':
#                 if labpatienttest.is_authorization:
#                     labpatienttest.status_id = ULabTestStatus.objects.get(name='Urgent (Authorization Pending)')
#                     labpatienttest.save()

#                 else:
#                     labpatienttest.status_id = ULabTestStatus.objects.get(name='Urgent (Completed)')
#                     labpatienttest.save()
#                     send_report_ready_sms(labpatienttest)

#         return Response(serializer.data)



class LabPatientFixedReportTemplateUpdateViewSet(viewsets.ModelViewSet):
    queryset = LabPatientFixedReportTemplate.objects.all()
    serializer_class = LabPatientFixedReportTemplateSerializer

    def list(self, request, *args, **kwargs):
        return Response({'Status': 'GET not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def create(self, request, *args, **kwargs):
        return Response({'Status': 'POST not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, *args, **kwargs):
        return Response({'Status': 'DELETE not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        labpatienttest = instance.LabPatientTestID
        globaltest = instance.LabGlobalTestID
        labtechnician = LabTechnicians.objects.filter(LabPatientTestID=labpatienttest).first()

        self.perform_update(serializer)

        if labtechnician.is_report_finished:
            if labpatienttest.status_id.name == 'Processing':
                if labpatienttest.is_authorization:
                    labpatienttest.status_id = ULabTestStatus.objects.get(name='Authorization Pending')
                    labpatienttest.save()

                else:
                    labpatienttest.status_id = ULabTestStatus.objects.get(name='Completed')
                    labpatienttest.save()

            elif labpatienttest.status_id.name == 'Emergency (Processing)':
                if labpatienttest.is_authorization:
                    labpatienttest.status_id = ULabTestStatus.objects.get(name='Emergency (Authorization Pending)')
                    labpatienttest.save()

                else:
                    labpatienttest.status_id = ULabTestStatus.objects.get(name='Emergency (Completed)')
                    labpatienttest.save()

            elif labpatienttest.status_id.name == 'Urgent (Processing)':
                if labpatienttest.is_authorization:
                    labpatienttest.status_id = ULabTestStatus.objects.get(name='Urgent (Authorization Pending)')
                    labpatienttest.save()

                else:
                    labpatienttest.status_id = ULabTestStatus.objects.get(name='Urgent (Completed)')
                    labpatienttest.save()

        return Response(serializer.data)


class LabPatientTestFixedReportDeletionView(APIView):
    serializer_class = LabPatientTestFixedReportDeletionSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer_data = serializer.data
        lab_patient_test_id = serializer_data.get('lab_patient_test_id')

        try:
            technician = LabTechnicians.objects.filter(LabPatientTestID=lab_patient_test_id).first()

            if not technician.is_word_report:
                try:
                    lab_patient_test = LabPatientTests.objects.get(pk=lab_patient_test_id)
                    reports_to_delete = LabPatientFixedReportTemplate.objects.filter(
                        LabPatientTestID=lab_patient_test_id)
                    reports_to_delete.delete()

                    #For tests in processing
                    if lab_patient_test.status_id.name == 'Processing':
                        lab_patient_test.status_id = ULabTestStatus.objects.get(name='Sample Collected')
                        lab_patient_test.save()
                    elif lab_patient_test.status_id.name == 'Emergency (Processing)':
                        lab_patient_test.status_id = ULabTestStatus.objects.get(name='Emergency (Sample Collected)')
                        lab_patient_test.save()
                    elif lab_patient_test.status_id.name == 'Urgent (Processing)':
                        lab_patient_test.status_id = ULabTestStatus.objects.get(name='Urgent (Sample Collected)')
                        lab_patient_test.save()

                    # For tests in Authorization Pending
                    elif lab_patient_test.status_id.name == 'Authorization Pending':
                        lab_patient_test.status_id = ULabTestStatus.objects.get(name='Sample Collected')
                        lab_patient_test.save()
                    elif lab_patient_test.status_id.name == 'Emergency (Authorization Pending)':
                        lab_patient_test.status_id = ULabTestStatus.objects.get(name='Emergency (Sample Collected)')
                        lab_patient_test.save()
                    elif lab_patient_test.status_id.name == 'Urgent (Authorization Pending)':
                        lab_patient_test.status_id = ULabTestStatus.objects.get(name='Urgent (Sample Collected)')
                        lab_patient_test.save()

                    #For tests in Completed
                    elif lab_patient_test.status_id.name == 'Completed':
                        lab_patient_test.status_id = ULabTestStatus.objects.get(name='Sample Collected')
                        lab_patient_test.save()
                    elif lab_patient_test.status_id.name == 'Emergency (Completed)':
                        lab_patient_test.status_id = ULabTestStatus.objects.get(name='Emergency (Sample Collected)')
                        lab_patient_test.save()
                    elif lab_patient_test.status_id.name == 'Urgent (Completed)':
                        lab_patient_test.status_id = ULabTestStatus.objects.get(name='Urgent (Sample Collected)')
                        lab_patient_test.save()

                    technician = LabTechnicians.objects.filter(LabPatientTestID=lab_patient_test).first()
                    technician.is_word_report = False
                    technician.is_completed = False
                    technician.is_report_generated = False
                    technician.is_report_finished = False
                    technician.is_report_printed = False
                    technician.save()

                    return Response({"Status": "Results deleted!"}, status=status.HTTP_200_OK)

                except LabPatientFixedReportTemplate.DoesNotExist:
                    return Response({"Error": "Results not found for the given LabPatientTestID"},
                                    status=status.HTTP_404_NOT_FOUND)

            else:
                try:
                    lab_patient_test = LabPatientTests.objects.get(pk=lab_patient_test_id)
                    reports_to_delete = LabPatientWordReportTemplate.objects.filter(
                        LabPatientTestID=lab_patient_test_id)
                    reports_to_delete.delete()

                    # For tests in Authorization Pending
                    if lab_patient_test.status_id.name == 'Authorization Pending':
                        lab_patient_test.status_id = ULabTestStatus.objects.get(name='Processing')
                        lab_patient_test.save()
                    elif lab_patient_test.status_id.name == 'Emergency (Authorization Pending)':
                        lab_patient_test.status_id = ULabTestStatus.objects.get(name='Emergency Processing')
                        lab_patient_test.save()
                    elif lab_patient_test.status_id.name == 'Urgent (Authorization Pending)':
                        lab_patient_test.status_id = ULabTestStatus.objects.get(name='Urgent Processing')
                        lab_patient_test.save()

                    # For tests in Completed
                    elif lab_patient_test.status_id.name == 'Completed':
                        lab_patient_test.status_id = ULabTestStatus.objects.get(name='Processing')
                        lab_patient_test.save()
                    elif lab_patient_test.status_id.name == 'Emergency (Completed)':
                        lab_patient_test.status_id = ULabTestStatus.objects.get(name='Emergency Processing')
                        lab_patient_test.save()
                    elif lab_patient_test.status_id.name == 'Urgent (Completed)':
                        lab_patient_test.status_id = ULabTestStatus.objects.get(name='Urgent Processing')
                        lab_patient_test.save()

                    technician = LabTechnicians.objects.filter(LabPatientTestID=lab_patient_test).first()
                    technician.is_word_report = False
                    technician.is_completed = False
                    technician.is_report_generated = False
                    technician.is_report_finished = False
                    technician.is_report_printed = False
                    technician.save()
                    return Response({"Status": "Results deleted!"}, status=status.HTTP_200_OK)

                except LabPatientWordReportTemplate.DoesNotExist:
                    return Response({"Error": "Results not found for the given LabPatientTestID"},
                                    status=status.HTTP_404_NOT_FOUND)

        except Exception as error:
            return Response({"Error": f"{error}"}, status=status.HTTP_404_NOT_FOUND)


class LabPatientWordReportTemplateListViewSet(viewsets.ModelViewSet):
    queryset = LabPatientWordReportTemplate.objects.all()
    serializer_class = LabPatientWordReportTemplateSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.queryset
        LabPatientTestID = self.request.query_params.get('LabPatientTestID', None)
        if LabPatientTestID is not None:
            queryset = queryset.filter(LabPatientTestID=LabPatientTestID)
            template = LabPatientWordReportTemplate.objects.filter(LabPatientTestID=LabPatientTestID).last()
            template.save()

            header, signature_content = generate_test_report_content(test_id=LabPatientTestID)
            rtf_content_header = get_rtf_content_for_word_report(test_id=LabPatientTestID)

            queryset = queryset.annotate(header=Value(header), rtf_content_header=Value(rtf_content_header),
                                                                signature_content=Value(signature_content))

            serializer = LabPatientWordReportTemplateSerializer(queryset, many=True)
            return Response(serializer.data)
        else:
            serializer = LabPatientWordReportTemplateSerializer(queryset, many=True)
            return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            partial = kwargs.pop('partial', False)
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            validated_data = serializer.validated_data
            pages = validated_data.pop('pages', [])

            existing_report_content = instance.report
            serializer.save()

            header, signature_content = generate_test_report_content(test_id=instance.LabPatientTestID.id)
            rtf_content_header = get_rtf_content_for_word_report(test_id=instance.LabPatientTestID.id)

            instance.header = header
            instance.signature_content = signature_content
            instance.rtf_content_header = rtf_content_header

            updated_report_content = instance.report

            # if pages:
            #     for page in instance.pages.all():
            #         page.delete()
            #     for page_data in pages:
            #         page = LabPatientWordReportTemplatePageWiseContent.objects.create(
            #             page_content=page_data['page_content'])
            #         instance.pages.add(page)

            labpatienttest = instance.LabPatientTestID
            labtechnician = LabTechnicians.objects.filter(LabPatientTestID=labpatienttest).first()

            if labtechnician.is_report_finished:
                if labpatienttest.status_id.name == 'Processing':
                    if labpatienttest.is_authorization:
                        labpatienttest.status_id = ULabTestStatus.objects.get(name='Authorization Pending')
                        labpatienttest.save()
                    else:
                        labpatienttest.status_id = ULabTestStatus.objects.get(name='Completed')
                        labpatienttest.save()

                elif labpatienttest.status_id.name == 'Emergency (Processing)':
                    if labpatienttest.is_authorization:
                        labpatienttest.status_id = ULabTestStatus.objects.get(name='Emergency (Authorization Pending)')
                        labpatienttest.save()

                    else:
                        labpatienttest.status_id = ULabTestStatus.objects.get(name='Emergency (Completed)')
                        labpatienttest.save()

                elif labpatienttest.status_id.name == 'Urgent (Processing)':
                    if labpatienttest.is_authorization:
                        labpatienttest.status_id = ULabTestStatus.objects.get(name='Urgent (Authorization Pending)')
                        labpatienttest.save()

                    else:
                        labpatienttest.status_id = ULabTestStatus.objects.get(name='Urgent (Completed)')
                        labpatienttest.save()

            if existing_report_content != updated_report_content:
                patient = instance.LabPatientTestID.patient
                try:
                    activity_log = ActivityLogs.objects.create(
                        user=request.user,
                        lab_staff=instance.last_updated_by,
                        client=request.client,
                        patient=patient,
                        operation="PUT",
                        url="lab/lab_word_patient_report_list",
                        model="LabPatientWordReportTemplate",
                        activity=f"Word Template Report updated for Patient {patient.name} for {instance.LabPatientTestID.name} by {instance.last_updated_by.name} on {instance.last_updated_on.strftime('%d-%m-%y %I:%M %p')}",
                        model_instance_id=instance.id,
                        response_code=200,
                        duration="",
                    )

                    change = ChangesInModels.objects.create(field_name='report',
                                                            before_value=existing_report_content,
                                                            after_value=updated_report_content)
                    activity_log.changes.add(change)

                except Exception as error:
                    logger.error(
                        f"Error Creating Activitylog for word_report for {patient.name}  for {instance.LabPatientTestID.name} in {instance.client} on {instance.added_on.strftime('%d-%m-%y %I:%M %p')}: {error}",
                        exc_info=True)

            return Response(serializer.data)
        except Exception as error:
            return Response({"Error":error}, status=status.HTTP_400_BAD_REQUEST)


class LabPatientTestReportGenerationViewset(viewsets.ModelViewSet):
    serializer_class = LabPatientTestReportGenerationSerializer

    def get_queryset(self):
        return []


    def get_age_in_days_for_patient(self, patient=None):
        patient_age_in_days = 0
        patient_age = patient.age
        patient_age_units = patient.ULabPatientAge.name

        if patient_age_units == "Days":
            patient_age_in_days = patient_age
        elif patient_age_units == "Months":
            patient_age_in_days = patient_age * 30
            print(patient_age_in_days, 'months')
        elif patient_age_units == "Years":
            patient_age_in_days = patient_age * 365
            print(patient_age_in_days,'dasdddsa')
        elif patient_age_units == "DOB":
            today = datetime.now().date()
            print(today, 'today')
            print(patient.dob, 'dob')

            patient_age_in_days = (today-patient.dob).days
            print(patient_age_in_days, 'days age')

        return patient_age_in_days

    def get_ref_range_for_patient(self, patient_gender=None, patient_age_in_days=None, parameter=None):
        normal_ref_range = ""

        if parameter.referral_range:
            normal_ref_range = parameter.referral_range
        else:
            genders_to_check = ["Both", f"{patient_gender}"]
            normal_ranges = LabFixedReportNormalReferralRanges.objects.filter(parameter_id=parameter,
                                                                              gender__name__in=genders_to_check,
                                                                              age_min_in_days__lte=patient_age_in_days,
                                                                              age_max_in_days__gte=patient_age_in_days
                                                                              )

            if normal_ranges:
                normal_range = normal_ranges.first()
                normal_ref_range = f"{normal_range.value_min}-{normal_range.value_max}"

        return normal_ref_range


    def create(self, request=None,lab_patient_test_id=None, created_by=None, template_id=None, *args, **kwargs):
        if request:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer_data = serializer.validated_data
            lab_patient_test_id = serializer_data.get('lab_patient_test_id')
            created_by_id = serializer_data.get('created_by')
            template_id = serializer_data.get('template_id')
        else:
            lab_patient_test_id = lab_patient_test_id
            created_by_id = created_by
            template_id = template_id

        lab_patient_test = LabPatientTests.objects.get(pk=lab_patient_test_id)
        created_by = LabStaff.objects.get(pk=created_by_id) if created_by_id is not None else None
        global_test_id = lab_patient_test.LabGlobalTestId

        patient = lab_patient_test.patient
        patient_gender = patient.gender.name
        patient_age_in_days = self.get_age_in_days_for_patient(patient=patient)

        lab_reports_template = LabReportsTemplates.objects.get(
            LabGlobalTestID=global_test_id,
            is_default=True
        )

        if template_id:
            lab_reports_template = LabReportsTemplates.objects.get(pk=template_id)

        if lab_reports_template.report_type == ULabReportType.objects.get(pk=1):
            fixed_parameters_report_template_set = LabFixedParametersReportTemplate.objects.filter(
                LabReportsTemplate=lab_reports_template, is_active=True)

            try:
                test_report_data = []

                for fixed_parameters_report_template in fixed_parameters_report_template_set:
                    referral_range = self.get_ref_range_for_patient(patient_gender=patient_gender,
                                                                       patient_age_in_days=patient_age_in_days,
                                                                       parameter=fixed_parameters_report_template)
                    lab_patient_fixed_report_template, created = LabPatientFixedReportTemplate.objects.get_or_create(
                        LabGlobalTestID=global_test_id,
                        LabPatientTestID=lab_patient_test,
                        template=fixed_parameters_report_template,
                        ordering=fixed_parameters_report_template.ordering,
                        group=fixed_parameters_report_template.group,
                        method=fixed_parameters_report_template.method,
                        parameter=fixed_parameters_report_template.parameter,
                        units=fixed_parameters_report_template.units,
                        formula=fixed_parameters_report_template.formula,
                        referral_range=referral_range,
                        is_value_bold=fixed_parameters_report_template.is_value_bold,
                        is_value_only=fixed_parameters_report_template.is_value_only
                    )

                    if created:
                        lab_patient_fixed_report_template.value=fixed_parameters_report_template.value
                        lab_patient_fixed_report_template.created_by = created_by
                        lab_patient_fixed_report_template.last_updated_by = created_by
                        lab_patient_fixed_report_template.save()

                    test_report_data.append(lab_patient_fixed_report_template)

                serializer = LabPatientFixedReportTemplateSerializer(test_report_data, many=True)

                if lab_patient_test.status_id.name == 'Sample Collected':
                    lab_patient_test.status_id = ULabTestStatus.objects.get(name='Processing')
                    lab_patient_test.save()
                elif lab_patient_test.status_id.name == 'Emergency (Sample Collected)':
                    lab_patient_test.status_id = ULabTestStatus.objects.get(name='Emergency (Processing)')
                    lab_patient_test.save()
                elif lab_patient_test.status_id.name == 'Urgent (Sample Collected)':
                    lab_patient_test.status_id = ULabTestStatus.objects.get(name='Urgent (Processing)')
                    lab_patient_test.save()

                lab_technician = LabTechnicians.objects.filter(LabPatientTestID=lab_patient_test).first()
                lab_technician.is_report_generated = True
                lab_technician.is_report_printed = False

                try:
                    department_defaults = DefaultsForDepartments.objects.filter(department=lab_patient_test.department).first()

                    if department_defaults and department_defaults.doctor:
                        default_doctor = department_defaults.doctor

                        lab_technician.consulting_doctor = default_doctor

                except Exception as error:
                    print(error)

                lab_technician.save()

                response_data = {
                    "type": "fixed",
                    'count': len(serializer.data),  # Add the count of results
                    'results': serializer.data
                }
                return Response(response_data)

            except Exception as error:
                return Response({"Status": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)

        elif lab_reports_template.report_type == ULabReportType.objects.get(pk=2):
            lab_word_report_template = LabWordReportTemplate.objects.filter(
                LabReportsTemplate=lab_reports_template).first()

            try:
                lab_patient_word_report_template, created = LabPatientWordReportTemplate.objects.get_or_create(
                    LabPatientTestID=lab_patient_test)
                lab_patient_word_report_template.report = lab_word_report_template.report
                lab_patient_word_report_template.rtf_content_report = lab_word_report_template.rtf_content
                lab_patient_word_report_template.created_by = created_by
                lab_patient_word_report_template.last_updated_by = created_by
                lab_patient_word_report_template.save()

                rtf_content_header = get_rtf_content_for_word_report(test_id=lab_patient_test_id)
                header, signature_content = generate_test_report_content(test_id=lab_patient_test.id)

                test_report_data = LabPatientWordReportTemplate.objects.filter(
                    LabPatientTestID=lab_patient_test).annotate(header=Value(header),
                                                                rtf_content_header=Value(rtf_content_header),
                                                                signature_content=Value(signature_content))

                serializer = LabPatientWordReportTemplateSerializer(test_report_data, many=True)

                if lab_patient_test.status_id.name == 'Sample Collected':
                    lab_patient_test.status_id = ULabTestStatus.objects.get(name='Processing')
                    lab_patient_test.save()
                elif lab_patient_test.status_id.name == 'Emergency (Sample Collected)':
                    lab_patient_test.status_id = ULabTestStatus.objects.get(name='Emergency (Processing)')
                    lab_patient_test.save()
                elif lab_patient_test.status_id.name == 'Urgent (Sample Collected)':
                    lab_patient_test.status_id = ULabTestStatus.objects.get(name='Urgent (Processing)')
                    lab_patient_test.save()

                lab_technician = LabTechnicians.objects.filter(LabPatientTestID=lab_patient_test).first()
                lab_technician.is_word_report = True
                lab_technician.is_report_generated = True
                lab_technician.is_report_printed = False

                try:
                    department_defaults = DefaultsForDepartments.objects.filter(
                        department=lab_patient_test.department).first()

                    if department_defaults and department_defaults.doctor:
                        default_doctor = department_defaults.doctor

                        lab_technician.consulting_doctor = default_doctor

                except Exception as error:
                    print(error)

                lab_technician.save()
                response_data = {
                    "type": "word",
                    'count': len(serializer.data),  # Add the count of results
                    'results': serializer.data
                }
                return Response(response_data)

            except Exception as error:
                return Response({"Status": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)


class SendTestReportInWhatsappView(APIView):
    def post(self, request, *args, **kwargs):
        patient_id = self.request.query_params.get('patient_id', None)
        client_id = self.request.query_params.get('client_id', None)
        test_ids = request.query_params.get('test_ids')
        reports_ready = request.query_params.get('reports_ready')
        letterhead = self.request.query_params.get('lh')

        if not ((test_ids and client_id) or (patient_id and reports_ready)):
            return Response({"Error": "One or more mandatory parameters are missing!"},
                            status=status.HTTP_400_BAD_REQUEST)

        client = Client.objects.get(pk=client_id) if client_id else None
        messaging_send_type = MessagingSendType.objects.get(pk=1)
        send_reports_template = MessagingTemplates.objects.get(pk=11)

        response = None
        message_type = 'whatsapp'

        if test_ids:
            test_ids = test_ids.split(',')
            test_ids = [test_id.strip() for test_id in test_ids if test_id.strip()]

            with schema_context(client.schema_name):
                tests = LabPatientTests.objects.filter(id__in=test_ids)
                if LabPatientTests.objects.filter(id__in=test_ids).exclude(status_id__in=[3, 13, 17]).exists():
                    return Response({"Error": "One or more tests are not completed in the selected tests!"},
                                    status=status.HTTP_400_BAD_REQUEST)

                patient = tests.first().patient

                if patient.referral_lab:
                    sourcing_lab = patient.referral_lab
                    if sourcing_lab.credit_payment:
                        pass
                    else:
                        paid_percentage = patient.labpatientinvoice.total_paid / patient.labpatientinvoice.total_price * 100
                        if paid_percentage >= sourcing_lab.min_print_amount:
                            pass
                        else:
                            amount_to_be_paid = patient.labpatientinvoice.total_price * (sourcing_lab.min_print_amount/100)
                            return Response({"Error": f"Minimum payment to print{amount_to_be_paid}  is not paid!"},
                                            status=status.HTTP_400_BAD_REQUEST)

                else:
                    pass
                pdf_base64 = get_pdf_content(test_ids, client_id, letterhead)
                pdf_base64 = pdf_base64.split(",", 1)[1]

                pdf_binary = base64.b64decode(pdf_base64)
                current_datetime = timezone.now()
                formatted_datetime = current_datetime.strftime("%I:%M %p")
                report_name = f"{patient.name}_{formatted_datetime}.pdf"
                patient_pdf = PatientPDFs.objects.create(
                    pdf_file=ContentFile(pdf_binary, name=report_name)
                )
                file_location = PatientPDFs.objects.last()
                file_location = file_location.pdf_file


                response = send_and_log_whatsapp_sms(
                    client=client,
                    search_id=patient.id,
                    numbers=patient.mobile_number,
                    mwa_template=send_reports_template,
                    messaging_send_type=messaging_send_type,
                    test_ids=test_ids,
                    letterhead=letterhead,
                    file_location=file_location
                )

        elif reports_ready:
            patient = Patient.objects.get(pk=patient_id)
            client = patient.client
            sms_template = MessagingTemplates.objects.get(pk=2)
            whatsapp_template = MessagingTemplates.objects.get(pk=13)

            if reports_ready == 'whatsapp':
                response = send_and_log_whatsapp_sms(search_id=patient.id, numbers=patient.mobile_number,
                                                     mwa_template=whatsapp_template,
                                                     messaging_send_type=messaging_send_type,
                                                     client=client)

            elif reports_ready == 'sms':
                response = send_and_log_sms(search_id=patient.id, numbers=patient.mobile_number,
                                            sms_template=sms_template, messaging_send_type=messaging_send_type,
                                            client=client)
                message_type = 'sms'

            else:
                pass

        response_code = response.data.get('response_code')
        response_error = response.data.get('Error')
        content = response.data.get('content')
        send_reports_type = response.data.get('send_reports_type')

        if response_code == 200:
            return Response({"Status": "Message sent successfully", "content": content,
                             "message_type": message_type, "send_reports_type": send_reports_type})
        else:
            return Response({"Error": f"{response_error}"}, status=status.HTTP_400_BAD_REQUEST)


def send_sms_when_reports_completed(patient=None):
    try:
        tests = LabPatientTests.objects.filter(patient=patient)
        if LabPatientTests.objects.filter(patient=patient).exclude(
                status_id__id__in=[3, 13, 17, 9, 21]).exists():
            print('Cannot sent reports ready, as some tests are still pending!')
        else:
            sms_template = MessagingTemplates.objects.get(pk=2)
            messaging_send_type = MessagingSendType.objects.get(pk=1)
            client = patient.client

            sms_template = MessagingTemplates.objects.get(pk=2)
            whatsapp_template = MessagingTemplates.objects.get(pk=13)

            send_and_log_whatsapp_sms(search_id=patient.id, numbers=patient.mobile_number,
                                      mwa_template=whatsapp_template,
                                      messaging_send_type=messaging_send_type,
                                      client=client,send_reports_type='Automatic'
                                      )

            send_and_log_sms(search_id=patient.id, numbers=patient.mobile_number,
                             sms_template=sms_template, messaging_send_type=messaging_send_type,
                             client=client)
            print('reports sent as tests are completed')

    except Exception as error:
        logger.error(f"Unexpected error sending sms: {error}", exc_info=True)

class PreviousVisitReportsAPIView(APIView):
    def get(self, request, *args, **kwargs):
        mr_no = self.request.query_params.get('mr_no', None)
        global_test_id = self.request.query_params.get('test_id', None)
        client_id = request.client.id

        if not mr_no:
            return Response({"error": "mr_no is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch patients and related data
        patients = Patient.objects.filter(mr_no=mr_no)
        if not patients.exists():
            return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)

        # Fetch tests in bulk with related data
        tests = LabPatientTests.objects.filter(
            LabGlobalTestId=global_test_id, patient__in=patients
        ).select_related('patient')

        if not tests.exists():
            return Response({"error": "No tests found for the given parameters."}, status=status.HTTP_404_NOT_FOUND)

        # Group tests by visit_id
        visit_reports = {}
        for test in tests:
            visit_id = test.patient.visit_id
            if visit_id not in visit_reports:
                visit_reports[visit_id] = {"visit_id": visit_id, "tests": []}
            visit_reports[visit_id]["tests"].append(test)

        # Process reports
        reports = []
        for visit_id, data in visit_reports.items():
            visit_tests = data["tests"]
            visit_tests_data = []

            for test in visit_tests:
                try:
                    test_report_api = GenerateTestReportViewset()
                    response = test_report_api.create(test_id=test.id, client_id=client_id)

                    html_content = response.data.get('html_content', '')
                    header = response.data.get('header', '')
                    footer = response.data.get('footer', '')

                    base64_pdf = get_pdf_content(
                        test.id, client_id, letterhead=None, water_mark=True
                    )

                    visit_tests_data.append({
                        "html_content": html_content,
                        "header": header,
                        "footer": footer,
                        "base64_pdf": base64_pdf,
                    })
                except Exception as error:
                    return Response(
                        {"error": f"Failed to generate report for test {test.id}: {str(error)}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            reports.append({
                "visit_id": visit_id,
                "tests": visit_tests_data
            })

        return Response({
            "mr_no": mr_no,
            "reports": reports
        }, status=status.HTTP_200_OK)


