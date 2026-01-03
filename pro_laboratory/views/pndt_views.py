from datetime import datetime

from rest_framework import viewsets
from rest_framework.response import Response
import re
from healtho_pro_user.models.business_models import BusinessProfiles, BContacts
from healtho_pro_user.models.users_models import Client
from pro_laboratory.models.patient_models import Patient
from pro_laboratory.models.pndtform_models import PNDTResults, FamilyGeneticHistory, PrenatalScreening, MTPInfo, \
    RecommendedTests, ProceduresPerformed
from pro_laboratory.models.universal_models import PrintTemplate, PrintDataTemplate
from pro_laboratory.serializers.pndt_serializers import PNDTResultsSerializer, GeneratePndtpdfSerializer
from pro_laboratory.views.universal_views import get_age_details, get_age_details_in_short_form
from pro_universal_data.models import Tag, PrintTemplateType


class PatientPNDTViewSet(viewsets.ModelViewSet):
    queryset = PNDTResults.objects.all()
    serializer_class = PNDTResultsSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        patient_id = self.request.query_params.get('patient_id', None)
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        return queryset


class GeneratePatientPndtViewSet(viewsets.ModelViewSet):
    serializer_class = GeneratePndtpdfSerializer

    def get_queryset(self):
        return []

    def create(self, request=None, patient_id=None, client_id=None, *args, **kwargs):
        if request:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer_data = serializer.validated_data
            patient_id = serializer_data.get('patient_id')
            client_id = serializer_data.get('client_id')
            print(patient_id, client_id)
        else:
            print(patient_id, client_id)

        try:
            patient = Patient.objects.get(pk=patient_id)
            client = Client.objects.get(pk=client_id)
            bProfile = BusinessProfiles.objects.filter(organization_name=client.name).first()
            family_genetic_history = FamilyGeneticHistory.objects.filter(patient=patient).first()
            prenatal_screening = PrenatalScreening.objects.filter(patient=patient).first()
            mtpinfo = MTPInfo.objects.filter(patient=patient).first()
            recommendedtests = RecommendedTests.objects.filter(patient=patient).first()
            procedures_performed = ProceduresPerformed.objects.filter(patient=patient).first()
            pndt_results = PNDTResults.objects.filter(patient=patient).first()
            contacts = BContacts.objects.filter(b_id=bProfile, is_primary=True).first()
            template_type = PrintTemplateType.objects.get(name='P N  D T')
            print_template = PrintTemplate.objects.get(print_template_type=template_type, is_default=True)
            template = PrintDataTemplate.objects.get(print_template=print_template)

            report_printed_on = datetime.now().strftime('%d-%m-%y %I:%M %p')

            details = {
                'patient': patient,
                'age':get_age_details(patient),
                "age_short_form":get_age_details_in_short_form(patient),
                'bProfile': bProfile,
                'family_genetic_history': family_genetic_history,
                'prenatal_screening': prenatal_screening,
                'mtpinfo': mtpinfo,
                'recommendedtests': recommendedtests,
                'procedures_performed': procedures_performed,
                'pndt_results': pndt_results,
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

        # Use the regular expression to find and replace total placeholders
        final_content = re.sub(expression_pattern, replace_total, modified_content)

        return Response({'html_content': final_content})
        # return HttpResponse(final_content)
        # return render(request, 'print_invoice.html', {'content': final_content})
