import json
import logging
from time import time
import jwt
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django_tenants.utils import schema_context
from healtho_pro_user.models.users_models import Client, HealthOProUser
from pro_laboratory.models.global_models import LabStaff
from pro_laboratory.models.universal_models import ActivityLogs, ChangesInModels
from urls_models import urls_with_models

# Configure logging
logger = logging.getLogger(__name__)


def extract_model_name(url):
    for key, value in urls_with_models.items():
        if url == key:
            return value['app_name'], value['model_name']
    return "AppNamenotFound", "ModelNotFound"


class LoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Log the request before it's processed
        start_time = time()

        user = None
        client = None
        operation = None
        url = None
        model = None
        model_instance_id = None
        activity = None
        response_code = None
        duration = None
        lab_staff = None
        patient = None

        patient_related_models = ["Patient", "LabPatientInvoice", "LabPatientReceipts", "LabPatientTests",
                                  "LabPatientPackages", "LabPatientRefund",
                                  "Patient", "LabPhlebotomist", "LabTechnicians", "LabTechnicianRemarks",
                                  "LabPatientWordReportTemplate", "LabPatientFixedReportTemplate",
                                  "LabDrAuthorization", "LabDrAuthorizationRemarks","LabAppointmentForPatient"]

        patient_models_direct = ["LabPatientReceipts", "LabPatientTests", "LabPatientPackages", "LabPatientRefund"]

        patient_model = ["Patient"]

        patient_models_LabPatientTestID = ["LabPhlebotomist", "LabTechnicians",
                                           "LabTechnicianRemarks", "LabPatientWordReportTemplate",
                                           "LabPatientFixedReportTemplate", "LabDrAuthorizationRemarks",
                                           "LabDrAuthorization",
                                           "LabDrAuthorizationRemarks"]

        not_required_urls = ["/api/user/token" ]

        not_required_urls_for_post_method = ["/lab/ref_amount_for_doctor"]

        not_required_urls_for_put_method = ["/api/lab/lab_word_report_templates","/api/lab/lab_word_patient_report_list"]

        request_path = request.path

        if request.method == 'GET':
            pass
        elif 'super_admin' in request_path:
            print('skipped normal log')
            pass

        else:
            try:
                token = request.META.get('HTTP_AUTHORIZATION', '').split(' ')[-1]
                if token:
                    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                else:
                    payload = {}

                user_id = payload.get('user_id')
                client_id = payload.get('client_id')

                if user_id:
                    user = HealthOProUser.objects.get(pk=user_id)
                if client_id:
                    client = Client.objects.get(pk=client_id)

                if client and user:
                    try:
                        with schema_context(client.schema_name):
                            lab_staff = LabStaff.objects.get(mobile_number=user.phone_number)
                    except Exception as error:
                        logger.info(
                            f'Error while creating activity log,for {user},{client},{operation} Request on {url} -'
                            f'Response ({error})')

                operation = request.method
                url = request.path

                url_parts = url.split('/')
                model_for_url = '/'.join(url_parts[:4])
                url = model_for_url

                app_name, model_name = extract_model_name(model_for_url)
                model = model_name

                json_data = request.body.decode('utf-8')  # Convert bytes to string

                data_dict = json.loads(json_data)  # Parse JSON string into dictionary

                model_instance_id = data_dict.get('id')

            except Exception as error:
                logger.info(
                    f'Error while creating activity log,for {user},{client},{operation} Request on {url} -'
                    f'Response ({error})')

            try:
                content_type = ContentType.objects.get(app_label=app_name, model=model_name.lower())
                model_class = content_type.model_class()
                model = model_class.__name__

            except Exception as error:
                print(error)

        if url in not_required_urls:
            pass
        elif 'super_admin' in request_path:
            pass
        else:
            try:
                if request.method == 'PUT' or 'PATCH':
                    if model_instance_id:
                        with schema_context(client.schema_name):
                            model_object_before = model_class.objects.get(pk=model_instance_id)
                            # model_data = model_object_before.__dict__
            except Exception as error:
                logger.info(
                    f'Error while creating activity log,for {user},{client},{operation} Request on {url} -'
                    f'Response ({error})')

        response = self.get_response(request)
        response_code = response.status_code
        # Calculate response time
        duration = time() - start_time
        # print(response)

        duration = f"{duration:.2f}"

        if url in not_required_urls:
            pass
        elif 'super_admin' in request_path:
            pass
        else:
            try:
                if operation == 'POST':
                    if response.status_code == 201:
                        operation = 'POST'
                    elif response.status_code == 200:
                        operation = 'GET'

                changes = []

                if (operation == 'PUT' or 'PATCH') and response.status_code == 200:
                    if model_instance_id:
                        with schema_context(client.schema_name):
                            model_object_after = model_class.objects.get(pk=model_instance_id)
                            # model_data_after = model_object_after.__dict__

                            for field in model_class._meta.fields:
                                field_name = field.name
                                value_before = getattr(model_object_before, field_name)
                                value_after = getattr(model_object_after, field_name)
                                # print(value_before,  value_after)
                                if value_before != value_after:
                                    change = ChangesInModels.objects.create(field_name=field_name,
                                                                            before_value=value_before,
                                                                            after_value=value_after)
                                    changes.append(change)

                            try:
                                if model in patient_related_models:
                                    if model in patient_model:
                                        patient = model_object_after
                                    elif model in patient_models_direct:
                                        patient = model_object_after.patient
                                    elif model in patient_models_LabPatientTestID:
                                        patient = model_object_after.LabPatientTestID.patient
                            except Exception as error:
                                print(error)
                                patient = None

                timestamp = timezone.now().strftime('%d-%m-%y %I:%M %p')
                name = lab_staff.name if lab_staff else (user.full_name if user else None)
                if operation == 'POST':
                    activity = f"{name} created {model} on {timestamp} in {duration} seconds"
                elif operation == 'PUT' or operation == 'PATCH':
                    activity = f"{name} updated {model} on {timestamp} in {duration} seconds"
                elif operation == 'GET':
                    pass
                else:
                    activity = f"{name} made a {operation} request on {timestamp} in {duration} seconds"

                if request.method == 'GET':
                    pass
                elif request.method == 'POST' and model in patient_related_models:
                    pass
                elif request.method == 'POST' and url in not_required_urls_for_post_method:
                    pass

                elif (request.method == 'PUT' or request.method == 'PATCH') and (url not in not_required_urls_for_put_method):
                    if request.client:
                        with schema_context(client.schema_name):
                            if changes:
                                activity_log = ActivityLogs.objects.create(
                                    user=user,
                                    lab_staff=lab_staff,
                                    client=client,
                                    patient=patient,
                                    operation=operation,
                                    url=url,
                                    model=model,
                                    activity=activity,
                                    model_instance_id=model_instance_id,
                                    response_code=response_code,
                                    duration=duration
                                )

                                for change in changes:
                                    activity_log.changes.add(change)
                            else:
                                pass
                    else:
                        pass


                else:
                    if request.client:
                        with schema_context(client.schema_name):
                            activity_log = ActivityLogs.objects.create(
                                user=user,
                                lab_staff=lab_staff,
                                client=client,
                                patient=patient,
                                operation=operation,
                                url=url,
                                model=model,
                                activity=activity,
                                model_instance_id=model_instance_id,
                                response_code=response_code,
                                duration=duration
                            )

                            if changes:
                                for change in changes:
                                    activity_log.changes.add(change)

                    else:
                        pass

            except jwt.InvalidTokenError:
                payload = {}

            except Exception as error:
                logger.info(
                    f'Request {operation} {url} - Response {response_code} - Duration {duration} seconds Error:{error}')

        logger.info(
            f'Request {request.method} {request.path} - Response {response.status_code} - Duration {duration} seconds')

        return response
