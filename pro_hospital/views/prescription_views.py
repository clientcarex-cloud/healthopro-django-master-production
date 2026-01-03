import re
from logging import exception

from django.db.models import Q
from django.http import HttpResponse
from rest_framework import viewsets, generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from datetime import datetime
from healtho_pro_user.models.business_models import BusinessProfiles
from healtho_pro_user.models.users_models import Client
from pro_hospital.models.patient_wise_models import PatientDoctorConsultationDetails
from pro_hospital.models.prescription_models import PatientPrescription, VitalsInPrescription, \
    InvestigationsInPrescription, MedicinesInPrescription
from pro_hospital.serializers.prescription_serializers import PatientPrescriptionSerializer, \
    GeneratePatientPrescriptionSerializer, GetPatientDoctorConsultationsSerializer
from pro_laboratory.models.doctors_models import LabDoctors
from pro_laboratory.models.global_models import LabStaff
from pro_laboratory.models.patient_models import Patient
from pro_laboratory.models.universal_models import PrintTemplate, PrintDataTemplate
from pro_laboratory.views.universal_views import get_age_details, get_age_details_in_short_form
from pro_universal_data.models import PrintTemplateType, Tag


class PatientPrescriptionViewSet(viewsets.ModelViewSet):
    queryset = PatientPrescription.objects.all()
    serializer_class = PatientPrescriptionSerializer

    def get_queryset(self):
        queryset = PatientPrescription.objects.all()

        query = self.request.query_params.get('q', None)
        sort = self.request.query_params.get('sort', None)
        patient_id = self.request.query_params.get('patient', None)
        doctor_consultation_id = self.request.query_params.get('doctor_consultation', None)

        if patient_id:
            queryset = queryset.filter(patient__id=patient_id)
        if doctor_consultation_id:
            queryset = queryset.filter(doctor_consultation__id=doctor_consultation_id)

        if query is not None:
            search_query = (Q(patient__name__icontains=query) | Q(patient__mr_no__icontains=query) | Q(patient__visit_id__icontains=query) |
                            Q(patient__mobile_number__icontains=query))
            queryset = queryset.filter(search_query)

        if sort == '-added_on':
            queryset = queryset.order_by('-added_on')
        if sort == 'added_on':
            queryset = queryset.order_by('added_on')

        return queryset



class GeneratePatientPrescriptionViewSet(viewsets.ModelViewSet):
    serializer_class = GeneratePatientPrescriptionSerializer

    def get_queryset(self):
        return []

    def create(self, request=None, patient_id=None, client_id=None, doctor_consultation=None, *args, **kwargs):
        if request:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer_data = serializer.validated_data
            patient_id = serializer_data.get('patient_id')
            doctor_consultation = serializer_data.get('doctor_consultation')
            client_id = request.client.id
            print(patient_id, client_id)
        else:
            print(patient_id, client_id, doctor_consultation)

        try:
            patient = Patient.objects.get(pk=patient_id)
            client = Client.objects.get(pk=client_id)
            bProfile = BusinessProfiles.objects.filter(organization_name=client.name).first()
            doctor_consultation = PatientDoctorConsultationDetails.objects.get(patient=patient, id=doctor_consultation)
            prescription = PatientPrescription.objects.filter(patient=patient,
                                                              doctor_consultation=doctor_consultation).first()
            vitals = VitalsInPrescription.objects.filter(prescription=prescription).first()
            investigations = InvestigationsInPrescription.objects.filter(prescription=prescription)
            medicines_in_prescription = MedicinesInPrescription.objects.filter(prescription=prescription)
            template_type = PrintTemplateType.objects.get(name='Prescription')
            print_template = PrintTemplate.objects.get(print_template_type=template_type, is_default=True)
            template = PrintDataTemplate.objects.get(print_template=print_template)

            report_printed_on = datetime.now().strftime('%d-%m-%y %I:%M %p')

            details = {
                'patient': patient,
                'age':get_age_details(patient),
                "age_short_form":get_age_details_in_short_form(patient),
                'bProfile': bProfile,
                'prescription': prescription,
                "vitals":vitals,
                "investigations":investigations,
                "medicines_in_prescription":medicines_in_prescription,
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
                tag = Tag.objects.get(tag_name='{' + tag_name + '}')

                if tag.is_collection:
                    if tag_name == 'PrescriptionMedicineNames':
                        medicines_details = details['medicines_in_prescription']
                        medicine_names_data = []

                        if medicines_details:
                            for medicine in medicines_details:
                                medicine_names_data.append(f"<strong>{medicine.medicine.name}</strong>")

                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in medicine_names_data)

                    if tag_name == 'PrescriptionMedicineQuantity':
                        medicines_details = details['medicines_in_prescription']
                        medicine_quantity_data = []

                        if medicines_details:
                            for medicine_data in medicines_details:
                                medicine_quantity_data.append(f"<strong>{medicine_data.quantity}</strong>")

                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in medicine_quantity_data)

                    if tag_name == 'PrescriptionMedicineDuration':
                        medicines_details = details['medicines_in_prescription']
                        medicine_duration_data = []

                        if medicines_details:
                            for medicine_data in medicines_details:
                                medicine_duration_data.append(f"<strong>{medicine_data.duration}</strong>")

                        return "".join(f'<p style="margin: 3px 5px;">{x} Days</p>' for x in medicine_duration_data)

                    if tag_name == 'PrescriptionMedicineIntakeTimings':
                        medicines_details = details['medicines_in_prescription']
                        medicine_intake_timings_data = []

                        if medicines_details:
                            for medicine_data in medicines_details:
                                intake_timings = [str(timing.name) for timing in medicine_data.in_take_time.all()]
                                intake_timings_str = " & ".join(intake_timings)
                                medicine_intake_timings_data.append(
                                    f"<strong>{intake_timings_str}</strong>"
                                )

                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in medicine_intake_timings_data)

                    if tag_name == 'PrescriptionTestSNo':
                        investigation_details = details['investigations']
                        investigation_test_no_data = []
                        serial_number = 1

                        if investigation_details:
                            for investigation in investigation_details:
                                tests = investigation.tests.all()
                                if tests.exists():
                                    for test in tests:
                                        investigation_test_no_data.append(
                                            f"<strong>{serial_number}</strong>"
                                        )
                                        serial_number += 1

                                packages = investigation.packages.all()
                                if packages.exists():
                                    for package in packages:
                                        investigation_test_no_data.append(
                                            f"<strong>{serial_number}</strong>"
                                        )
                                        serial_number += 1

                                        package_tests = package.tests.all()
                                        for package_test in package_tests:
                                            investigation_test_no_data.append(
                                                f"&nbsp;&nbsp;&nbsp;<em>{serial_number - 1}.{serial_number}</em>"
                                            )
                                            serial_number += 1
                            return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in investigation_test_no_data)

                    if tag_name == 'PrescriptionTotalTests':
                        investigation_details = details['investigations']
                        investigation_test_names_data = []

                        if investigation_details:
                            for investigation in investigation_details:
                                tests = investigation.tests.all()
                                if tests.exists():
                                    for test in tests:
                                        investigation_test_names_data.append(f"<strong>{test.name}</strong>")
                                packages = investigation.packages.all()
                                if packages.exists():
                                    for package in packages:
                                        investigation_test_names_data.append(f"<strong>{package.name} (Package)</strong>")
                                        package_tests = package.tests.all()
                                        for package_test in package_tests:
                                            investigation_test_names_data.append(
                                                f"&nbsp;&nbsp;&nbsp;<em>{package_test.name}</em>")
                            return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in investigation_test_names_data)

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
                result = str(eval(expression, {'__builtins__': None}, {'details': details}))
                return result
            except Exception as eval_error:
                print(f"Error in expression evaluation: {eval_error}")
                return "[Error]"  # Placeholder for any evaluation error

        html_content = template.data
        template_content = html_content
        intermediate_content = re.sub(search_pattern, replace_tag, template_content)
        modified_content = re.sub(expression_pattern, evaluate_expression, intermediate_content)

        def replace_total(match):
            tag_name = match.group(1)  # Extract the tag name
            total_value = tag_totals.get(tag_name, 0)  # Get the total value from tag_totals
            return str(total_value)  # Return the total value as a string

        template_header_content = template.header if template.header else ""
        intermediate_header_content = re.sub(search_pattern, replace_tag, template_header_content)
        modified_header_content = re.sub(expression_pattern, evaluate_expression, intermediate_header_content)
        final_header_content = re.sub(expression_pattern, replace_total, modified_header_content)

        final_content = re.sub(expression_pattern, replace_total, modified_content)

        return Response({ "header": final_header_content,
            'html_content': final_content})
        # return HttpResponse(final_content)
        # return render(request, 'print_invoice.html', {'content': final_content})


class GetPatientPrescriptionsListAPIView(generics.ListAPIView):
    serializer_class = GetPatientDoctorConsultationsSerializer

    def get_queryset(self):
        query = self.request.query_params.get('q')
        status_ids = self.request.query_params.get('status_id', None)
        date = self.request.query_params.get('date', None)
        date_range_after = self.request.query_params.get('date_range_after', None)
        date_range_before = self.request.query_params.get('date_range_before', None)
        lab_doctor = self.request.query_params.get('doctor_id', None)
        lab_staff_id = self.request.query_params.get('lab_staff', None)
        queryset = PatientDoctorConsultationDetails.objects.all()

        if query:
            queryset = queryset.filter(patient__name__icontains=query)
        if lab_doctor:
            queryset = queryset.filter(consultation__labdoctors__id=lab_doctor)

        if lab_staff_id:
            lab_staff = LabStaff.objects.get(id=lab_staff_id)
            doctor = LabDoctors.objects.filter(mobile_number=lab_staff.mobile_number).first()
            queryset = queryset.filter(consultation__labdoctors=doctor)


        if status_ids:
            status_ids = list(map(int, status_ids.split(',')))
            queryset = queryset.filter(status_id__in=status_ids)

        if date:
            try:
                date = datetime.strptime(date, "%Y-%m-%d").date()
                queryset = queryset.filter(added_on__date=date)
            except ValueError:
                raise ValidationError({"Error": "Invalid date format. Use YYYY-MM-DD."})

        if date_range_after and date_range_before:
            try:
                date_range_after = datetime.strptime(date_range_after, "%Y-%m-%d").date()
                date_range_before = datetime.strptime(date_range_before, "%Y-%m-%d").date()
                queryset = queryset.filter(added_on__date__range=(date_range_after, date_range_before))
            except Exception as Error:
                raise ValidationError({"Error": "Invalid date format. Use YYYY-MM-DD."})
        elif date_range_after:
            try:
                date_range_after = datetime.strptime(date_range_after, "%Y-%m-%d").date()
                queryset = queryset.filter(added_on__date__gte=date_range_after)
            except Exception as Error:
                raise ValidationError({"date": "Invalid date format. Use YYYY-MM-DD."})
        elif date_range_before:
            try:
                date_range_before = datetime.strptime(date_range_before, "%Y-%m-%d").date()
                queryset = queryset.filter(added_on__date__lte=date_range_before)
            except Exception as Error:
                raise ValidationError({"date": "Invalid date format. Use YYYY-MM-DD."})

        return queryset

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

