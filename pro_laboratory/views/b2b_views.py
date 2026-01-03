import re
from datetime import datetime

from OpenSSL.rand import status
from django.db.models import Sum, Q, Prefetch
from django.forms import model_to_dict
from django.http import HttpResponse
from num2words import num2words
from rest_framework import viewsets, generics
from rest_framework.response import Response

from healtho_pro_user.models.business_models import BusinessProfiles
from healtho_pro_user.models.users_models import Client
from pro_laboratory.filters import LabTestFilter
from pro_laboratory.models.b2b_models import Company, CompanyRevisedPrices, CompanyWorkPartnership
from pro_laboratory.models.global_models import LabGlobalTests, LabGlobalPackages
from pro_laboratory.models.patient_models import Patient, LabPatientTests, LabPatientInvoice, LabPatientReceipts, \
    LabPatientPackages
from pro_laboratory.models.universal_models import PrintTemplate, PrintDataTemplate
from pro_laboratory.serializers.b2b_serializers import CompanySerializer, CompanyRevisedPricesSerializer, \
    CompanyWorkPartnershipSerializer, LabGlobalTestsRevisedPricesSerializer, GenerateCompanyInvoiceSerializer, \
    LabGlobalPackagesRevisedPricesSerializer
from pro_laboratory.serializers.patient_serializers import StandardViewPatientSerializer
from pro_universal_data.models import PrintTemplateType, Tag


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer


class CompanyRevisedPricesViewSet(viewsets.ModelViewSet):
    queryset = CompanyRevisedPrices.objects.all()
    serializer_class = CompanyRevisedPricesSerializer

    def list(self, request, *args, **kwargs):
        company = self.request.query_params.get('company')
        departments_details = self.request.query_params.get('departments')
        query = self.request.query_params.get('query')
        package = self.request.query_params.get('package')

        if not company:
            return Response({"Error": "company is not provided!"})

        # Fetch from the database if no cache is found
        lab_tests_queryset = LabGlobalTests.objects.filter(
            (Q(name__icontains=query) | Q(short_code__icontains=query)) &
            Q(is_active=True) &
            Q(department__is_active=True) & Q(is_outsourcing = False)
        )
        lab_packages_queryset = LabGlobalPackages.objects.filter(
            Q(name__icontains=query) &
            Q(is_active=True))

        if departments_details:
            departments = [department.strip() for department in departments_details.split(',') if
                           department.strip()]
            department_query = Q(labpatienttests__department__id__in=departments)
            lab_tests_queryset = lab_tests_queryset.filter(department_query)


        tests_page = self.paginate_queryset(lab_tests_queryset)
        if tests_page is not None:
            lab_test_serializer = LabGlobalTestsRevisedPricesSerializer(tests_page, many=True, context={'company': company})
            tests_data = self.get_paginated_response(lab_test_serializer.data).data
        else:
            lab_test_serializer = LabGlobalTestsRevisedPricesSerializer(lab_tests_queryset, many=True,
                                                                        context={'company': company})
            tests_data = lab_test_serializer.data



        lab_packages_serializer = LabGlobalPackagesRevisedPricesSerializer(lab_packages_queryset, many=True,
                                                              context={'company': company})
        packages_data = lab_packages_serializer.data

        response_data = {
            'lab_tests': tests_data,
            'lab_packages': packages_data
        }

        return Response(response_data)



class CompanyWorkPartnershipViewSet(viewsets.ModelViewSet):
    queryset = CompanyWorkPartnership.objects.all()
    serializer_class = CompanyWorkPartnershipSerializer


class GetPatientsFromCompanyAPIView(generics.ListAPIView):
    def get(self, request, *args, **kwargs):
        company = self.request.query_params.get('company', None)
        date = self.request.query_params.get('date', None)
        start_date = self.request.query_params.get('date_range_after', None)
        end_date = self.request.query_params.get('date_range_before', None)
        patient_ids = self.request.query_params.get('patient_ids', [])
        partner = self.request.query_params.get('partner')

        lab_tests_queryset = LabPatientTests.objects.filter(patient__partner__isnull=False).order_by('id')

        lab_tests_filter = LabTestFilter(self.request.GET, queryset=lab_tests_queryset)
        if not lab_tests_filter.is_valid():
            return Response({"Error":"Invalid filter parameters for lab tests."}, status=400)

        filtered_lab_tests_qs = lab_tests_filter.qs

        if filtered_lab_tests_qs.exists():
            patients = Patient.objects.filter(
                labpatienttests__in=filtered_lab_tests_qs
            ).distinct().prefetch_related(
                Prefetch('labpatienttests_set', queryset=filtered_lab_tests_qs),
            ).select_related('labpatientinvoice')
        else:
            patients = Patient.objects.none()

        # patients = Patient.objects.all()
        if partner:
            patients = patients.filter(partner=partner)
        elif company:
            patients = patients.filter(partner__company=company)

        if date:
            patients = patients.filter(added_on__date=date)

        if start_date and end_date:
            patients = patients.filter(added_on__date__range=[start_date, end_date])
        page = self.paginate_queryset(patients)

        if page is not None:
            serializer = StandardViewPatientSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = StandardViewPatientSerializer(patients, many=True)
        return Response(serializer.data)


class GenerateCompanyInvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = GenerateCompanyInvoiceSerializer

    def get_queryset(self):
        return []

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer_data = serializer.validated_data
        patient_ids = serializer_data.get('patient_ids')
        partner_id = serializer_data.get('partner_id')

        try:
            partner = CompanyWorkPartnership.objects.get(pk=partner_id)
            patients = Patient.objects.filter(id__in=patient_ids).order_by('id')
            total_patients_count = patients.count()
            first_patient = patients.first()
            last_patient = patients.last()
            packages = LabPatientPackages.objects.filter(patient=first_patient)
            total_paid_amount = 0
            total_tests_price = 0
            for patient in patients:
                receipts = LabPatientReceipts.objects.filter(patient=patient)
                for receipt in receipts:
                    payments = receipt.payments.all()
                    total_paid_amount += payments.aggregate(total=Sum('paid_amount'))['total'] or 0

            packages = LabPatientPackages.objects.filter(patient=first_patient)
            for package in packages:
                total_tests_price = package.offer_price

            tests = LabPatientTests.objects.filter(patient=first_patient, is_package_test=False)
            test_names = [test.name for test in tests]
            for test in tests:
                total_tests_price += test.price


            company = partner.company
            company.print_count += 1
            company.save()


            report_printed_on = datetime.now().strftime('%d-%m-%y %I:%M %p')

            paid_amount_in_words = f"{num2words(total_tests_price, lang='en_IN').title()} Rupees Only"

            details = {
                'partner': partner,
                'total_patients_count': total_patients_count,
                'total_paid_amount': total_paid_amount,
                "paid_amount_in_words":paid_amount_in_words,
                'total_tests_price': total_tests_price,
                'tests': tests,
                "packages":packages,
                "report_printed_on":report_printed_on
            }
            print(model_to_dict(partner.company))
        except Exception as error:
            print(error)
            return Response(f"Error fetching details: {error}", status=400)

        template_type = PrintTemplateType.objects.get(name='B2B Invoice')
        print_template = PrintTemplate.objects.get(print_template_type=template_type, is_default=True)
        template = PrintDataTemplate.objects.get(print_template=print_template)

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
                    if tag_name == 'LabTestSNo':
                        packages_details = details['packages']
                        tests_details = details['tests']
                        serial_no_data = []
                        counter=1

                        if packages_details:
                            for package in packages_details:
                                serial_no_data.append(f"{counter}")
                                counter+=1

                        if tests_details:
                            for test in tests_details:
                                serial_no_data.append(f"{counter}")
                                counter+=1


                        # return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in serial_no_data)

                        # Join all items into a single string with paragraph tags for each item
                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' if isinstance(x,
                                                                                            str) else f'<p style="margin: 3px 5px;"></p>'
                                       for x in serial_no_data)
                    if tag_name == 'TotalTests':
                        packages_details = details['packages']
                        tests_details = details['tests']
                        test_names_data = []

                        if packages_details:
                            for package in packages_details:
                                test_names_data.append(f"<strong>{package.name}</strong>")
                                # tests = package.lab_tests.all()

                                # for test in tests:
                                #     test_names_data.append(f"{test.name}")
                                # test_names_data.append("<p style='margin: 10px 0;'></p>")

                        if tests_details:
                            for test in tests_details:
                                test_names_data.append(f"{test.name}")

                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in test_names_data)


                    if tag_name == 'B2BPatientSNos':
                        return "".join(f'<p class="B2BPatientSNos" style="margin:4px 0; border-bottom:1px solid black;">{index}</p>' for index, patient in enumerate(patients, start=1))

                    if tag_name == 'B2BPatientNames':
                        return "".join(f'<p class="B2BPatientNames" style="margin:4px 0; border-bottom:1px solid black;">{patient.name}</p>' for patient in patients)

                    if tag_name == 'B2BPatientVisitIDs':
                        return "".join(f'<p class="B2BPatientVisitIDs" style="margin:4px 0; border-bottom:1px solid black;">{patient.visit_id}</p>' for patient in patients)

                    if tag_name == 'B2BPatientRegDates':
                        return "".join(f'<p class="B2BPatientRegDates" style="margin:4px 0; border-bottom:1px solid black;">{patient.added_on.strftime('%d-%m-%y')}</p>' for patient in patients)

                    if tag_name == 'B2BPatientStartDate':
                        return f'<span class="B2BPatientStartDate" style="">{first_patient.added_on.strftime('%d-%m-%y')}</span>'

                    if tag_name == 'B2BPatientEndDate':
                        return f'<span class="B2BPatientEndDate" style="">{last_patient.added_on.strftime('%d-%m-%y')}</span>'

                    if tag_name == 'B2BPatientDetails':
                        content=f'''<tr><th class="B2BPatientSNosHead" style="text-align:center;border:1px solid black; border-top:0px;">S.No</th>
                                <th class="B2BPatientVisitIDsHead" style="text-align:center;border:1px solid black; border-top:0px;">Visit ID</th>
                                <th class="B2BPatientRegDatesHead" style="text-align:center;border:1px solid black; border-top:0px;">Reg. Date</th>
                                <th class="B2BPatientNamesHead" style="text-align:center;border:1px solid black; border-top:0px;">Patient Name</th>
                                </tr>'''
                        for index, patient in enumerate(patients, start=1):
                            content+=f'''<tr><td class="B2BPatientSNos" style="text-align:center;border:1px solid black;">{index}</td>
                                <td class="B2BPatientVisitIDs" style="text-align:center;border:1px solid black;">{patient.visit_id}</td>
                                <td class="B2BPatientRegDates" style="text-align:center;border:1px solid black;">{patient.added_on.strftime('%d-%m-%y')}</td>
                                <td class="B2BPatientNames" style="text-align:center;border:1px solid black;">{patient.name}</td>
                                </tr>'''
                        content =  f'''<table cellspacing="0" style="border-collapse:collapse;width:100%;">
                                            <tbody>
                                                {content}
                                            <tbody>
                                        </table>'''
                        return content

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

        # Use the regular expression to find and replace total placeholders
        final_content = re.sub(expression_pattern, replace_total, modified_content)

        return Response({'html_content': final_content})
        # return HttpResponse(final_content)
        # return render(request, 'print_invoice.html', {'content': final_content})
