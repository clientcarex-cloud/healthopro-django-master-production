import random
import string
from datetime import datetime, timedelta, timezone
from django.db import transaction
from django.db.models import Q, Prefetch
from django.forms import model_to_dict
from django_filters.rest_framework import DjangoFilterBackend
from django_tenants.utils import schema_context
from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from healtho_pro_user.models.business_models import BusinessProfiles, BusinessAddresses
from healtho_pro_user.models.universal_models import UserType, HealthcareRegistryType
from healtho_pro_user.models.users_models import Client, HealthOProUser, OTP, UserTenant
from healtho_pro_user.views.business_views import get_business_from_client, get_client_from_business
from healtho_pro_user.views.users_views import blacklist_user_tokens
from pro_laboratory.filters import SourcingLabTestsTrackerFilter, PatientFilter, LabTestFilter
from pro_laboratory.models.client_based_settings_models import BusinessControls, LetterHeadSettings
from pro_laboratory.models.global_models import LabGlobalTests, LabDepartments, LabStaffRole, LabStaff, LabDiscountType, \
    LabMenuAccess, LabStaffDefaultBranch
from pro_laboratory.models.labtechnicians_models import LabTechnicians
from pro_laboratory.models.patient_models import Patient, LabPatientTests, LabPatientInvoice, LabPatientPackages
from pro_laboratory.models.phlebotomists_models import LabPhlebotomist
from pro_laboratory.models.user_permissions_models import UserPermissionsAccess
from pro_laboratory.serializers.global_serializers import LabGlobalTestsSerializer, LabDepartmentsSerializer
from pro_laboratory.serializers.patient_serializers import PatientSerializer, StandardViewPatientSerializer
from pro_laboratory.serializers.sourcing_lab_serializers import BusinessProfilesSerializer, \
    SourcingLabTestsTrackerSerializer, GroupedSourcingLabTestsTrackerSerializer, \
    SourcingLabRevisedLabGlobalTestsSerializer, SourcingLabPatientReportUploadsSerializer, \
    SourcingLabPaymentsSerializer, SourcingLabLetterHeadSettingsSerializer
from pro_laboratory.models.sourcing_lab_models import SourcingLabRegistration, SourcingLabRevisedTestPrice, \
    SourcingLabTestsTracker, SourcingLabPatientReportUploads, SourcingLabPayments, SourcingLabLetterHeadSettings
from pro_laboratory.serializers.sourcing_lab_serializers import SourcingLabRevisedTestPriceSerializer, \
    SourcingLabRegistrationSerializer
from pro_laboratory.views.patient_views import get_lab_staff_from_request
from pro_laboratory.views.phlebotomists_views import LabPhlebotomistsViewSet
from pro_laboratory.views.universal_views import GeneratePatientTestReportViewset
from pro_universal_data.models import ULabPatientTitles, ULabPatientAge, ULabPatientGender, ULabPatientAttenderTitles, \
    ULabPaymentModeType, ULabTestStatus, ULabMenus
from django.db.models import F, Sum


# To get the list of all Businesses, registered as Diagnostic centre
class AvailableSouringLabsListAPIView(generics.ListAPIView):
    queryset = BusinessProfiles.objects.all()
    serializer_class = BusinessProfilesSerializer

    def get_queryset(self):
        queryset = BusinessProfiles.objects.filter(provider_type__name='Diagnostic Centre')
        client = self.request.client
        business = get_business_from_client(client)
        query = self.request.query_params.get('query', None)
        queryset = queryset.exclude(pk=business.id)

        if query is not None:
            search_query = (Q(organization_name__icontains=query) | Q(phone_number__icontains=query) | Q(
                address__icontains=query))
            queryset = queryset.filter(search_query)

        return queryset


#To get the list of tests/departments, available at Processing lab, or to see the already imported tests ids.
class GetLabGlobalTestsOfSourcingLabView(generics.ListAPIView):
    serializer_class = LabGlobalTestsSerializer

    def list(self, request, *args, **kwargs):
        b_id = self.request.query_params.get('b_id', None)
        sourcing_lab = self.request.query_params.get('sourcing_lab', None)
        query = self.request.query_params.get('query', None)
        departments = self.request.query_params.get('departments', None)
        imported = self.request.query_params.get('imported', None)

        try:
            if imported and sourcing_lab:
                sourcing_lab = SourcingLabRegistration.objects.get(pk=sourcing_lab)
                queryset = LabGlobalTests.objects.filter(is_outsourcing=True, sourcing_lab=sourcing_lab)

                if sourcing_lab.acceptor:
                    imported_ids = queryset.values_list('outsourcing_global_test_id', flat=True)
                    return Response({"imported_tests": imported_ids})
                else:
                    page = self.paginate_queryset(queryset)
                    if page is not None:
                        serializer = self.get_serializer(page, many=True)
                        return self.get_paginated_response(serializer.data)

                    serializer = self.get_serializer(queryset, many=True)
                    return Response(serializer.data)

            if b_id is None:
                return Response({"Error": "Business ID is missing!"}, status=status.HTTP_400_BAD_REQUEST)

            client_business = BusinessProfiles.objects.get(pk=b_id)
            client = Client.objects.get(name=client_business.organization_name)

            with schema_context(client.schema_name):
                queryset = LabGlobalTests.objects.all()
                queryset = queryset.filter(department__is_active=True)

                if query is not None:
                    search_query = (Q(name__icontains=query) | Q(short_code__icontains=query))
                    queryset = queryset.filter(search_query)
                if departments:
                    if departments == 'true':
                        self.serializer_class = LabDepartmentsSerializer
                        queryset = LabDepartments.objects.all()
                        page = self.paginate_queryset(queryset)
                        if page is not None:
                            serializer = LabDepartmentsSerializer(page, many=True)
                            return self.get_paginated_response(serializer.data)

                        serializer = self.get_serializer(queryset, many=True)
                        return Response(serializer.data)
                    else:
                        department_ids = [int(dep_id) for dep_id in departments.split(',')]
                        queryset = queryset.filter(department__id__in=department_ids)

                page = self.paginate_queryset(queryset)
                if page is not None:
                    serializer = self.get_serializer(page, many=True)
                    return self.get_paginated_response(serializer.data)

                serializer = self.get_serializer(queryset, many=True)
                return Response(serializer.data)
        except Exception as error:
            return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)


class SourcingLabRegistrationViewSet(viewsets.ModelViewSet):
    queryset = SourcingLabRegistration.objects.all()
    serializer_class = SourcingLabRegistrationSerializer

    def get_queryset(self):
        queryset = SourcingLabRegistration.objects.all()
        query = self.request.query_params.get('query', None)
        initiator = self.request.query_params.get('initiator', None)
        acceptor = self.request.query_params.get('acceptor', None)
        is_active = self.request.query_params.get('is_active', None)
        sort = self.request.query_params.get('sort', None)

        if query is not None:
            search_query = (Q(initiator__organization_name__icontains=query) | Q(
                initiator__phone_number__icontains=query) | Q(acceptor__organization_name__icontains=query) |
                            Q(acceptor__phone_number__icontains=query) | Q(phone_number__icontains=query) | Q(
                        organization_name__icontains=query))
            queryset = queryset.filter(search_query)

        if initiator is not None:
            queryset = queryset.filter(initiator_id=initiator)

        if acceptor is not None:
            queryset = queryset.filter(acceptor_id=acceptor)

        if is_active is not None:
            if is_active == 'true':
                queryset = queryset.filter(is_active=True)
            elif is_active == 'false':
                queryset = queryset.filter(is_active=False)

        if sort == 'organization_name':
            queryset = queryset.order_by('organization_name')
        elif sort == '-organization_name':
            queryset = queryset.order_by('-organization_name')
        else:
            queryset = queryset.order_by('organization_name')



        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            if serializer.is_valid():
                with transaction.atomic():
                    validated_data = serializer.validated_data
                    if validated_data['initiator'] and validated_data['acceptor']:
                        sourcing_lab = SourcingLabRegistration.objects.filter(
                            initiator=validated_data['initiator'], acceptor=validated_data['acceptor']).first()

                        if sourcing_lab:
                            return Response({"Error": "Same Collaboration request already exists!"},
                                            status=status.HTTP_400_BAD_REQUEST)


                    else:
                        same_business_relation = SourcingLabRegistration.objects.filter(
                            organization_name=validated_data['organization_name'],
                            is_referral_lab=validated_data['is_referral_lab']).first()

                        if same_business_relation:
                            return Response({"Error": "Same Business name already exists in a Collaboration!"},
                                            status=status.HTTP_400_BAD_REQUEST)

                    sourcing_lab = SourcingLabRegistration.objects.create(**validated_data)

                    if sourcing_lab.initiator and sourcing_lab.acceptor:
                        client = get_client_from_business(sourcing_lab.acceptor)
                        with schema_context(client.schema_name):
                            client_sourcing_lab = SourcingLabRegistration.objects.filter(
                                initiator=validated_data['initiator'], acceptor=validated_data['acceptor']).first()

                            if client_sourcing_lab:
                                pass
                            else:
                                client_sourcing_lab = SourcingLabRegistration.objects.create(**validated_data)
                                client_sourcing_lab.is_referral_lab = True
                                client_sourcing_lab.save()

                    if sourcing_lab.initiator and not sourcing_lab.acceptor:
                        copy_tests_for_manual_os_labs(sourcing_lab=sourcing_lab)

                    return Response(self.get_serializer(sourcing_lab).data, status=status.HTTP_201_CREATED)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            partial = kwargs.pop('partial', False)
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            validated_data = serializer.validated_data
            bProfile = get_business_from_client(self.request.client)

            if (bProfile == instance.initiator and instance.acceptor is None) or (
                    bProfile == instance.acceptor and instance.initiator is None):
                if validated_data['organization_name'] and validated_data['phone_number']:
                    same_business_relation = SourcingLabRegistration.objects.filter(
                        organization_name=validated_data['organization_name']).exclude(pk=instance.id)

                    if same_business_relation:
                        return Response({"Error": "Same Business name already exists in a Collaboration!"},
                                        status=status.HTTP_400_BAD_REQUEST)
                    serializer.save()
                    return Response(serializer.data, status=status.HTTP_200_OK)
                else:
                    return Response({"Error": "One of mandatory parameters is not given!"},
                                    status=status.HTTP_400_BAD_REQUEST)

            if bProfile == instance.acceptor:
                if validated_data['organization_name']:
                    same_business_relation = SourcingLabRegistration.objects.filter(
                        organization_name=validated_data['organization_name']).exclude(pk=instance.id)

                    if same_business_relation:
                        return Response({"Error": "Same Business name already exists in a Collaboration!"},
                                        status=status.HTTP_400_BAD_REQUEST)
                serializer.save()

                if instance.is_active and instance.initiator:
                    staff, created = LabStaff.objects.get_or_create(
                        name=instance.initiator.organization_name,
                        mobile_number=instance.initiator.phone_number
                    )

                    if created:
                        lab_staff_role, created = LabStaffRole.objects.get_or_create(name="SourcingLab")
                        staff.is_superadmin = False
                        staff.role = lab_staff_role
                        staff.is_login_access = False
                        staff.save()

                    client_b_id = instance.initiator

                    client = Client.objects.get(name=client_b_id.organization_name)
                    with schema_context(client.schema_name):
                        sourcing_lab = SourcingLabRegistration.objects.get(initiator=instance.initiator,
                                                                           acceptor=instance.acceptor)
                        sourcing_lab.min_paid_amount = instance.min_paid_amount
                        sourcing_lab.min_print_amount = instance.min_print_amount
                        sourcing_lab.credit_payment = instance.credit_payment
                        sourcing_lab.description = instance.description
                        sourcing_lab.is_active = instance.is_active
                        sourcing_lab.save()

                        return Response(self.get_serializer(sourcing_lab).data, status=status.HTTP_200_OK)

            else:
                return Response({
                    "Error": f"Initiator cannot change the plan, Only the Business which accepted the request can "
                             f"update the Data!"},
                    status=status.HTTP_400_BAD_REQUEST)

        except Exception as error:
            return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)

    # def destroy(self, request, *args, **kwargs):
    #     try:
    #         instance = self.get_object()
    #
    #         if instance.is_active:
    #             return Response({"Error": "Cannot delete an active Collaboration!"}, status=status.HTTP_400_BAD_REQUEST)
    #
    #         acceptor_business = instance.acceptor
    #         acceptor_client = get_client_from_business(acceptor_business)
    #
    #         with schema_context(acceptor_client.schema_name):
    #             sourcing_lab = SourcingLabRegistration.objects.filter(initiator=instance.initiator,
    #                                                                   acceptor=acceptor_business).first()
    #             if sourcing_lab:
    #                 if sourcing_lab.is_active:
    #                     return Response({"Error": "Cannot delete an active Collaboration!"},
    #                                     status=status.HTTP_400_BAD_REQUEST)
    #                 else:
    #                     sourcing_lab.delete()
    #
    #         instance.delete()
    #         return Response({"Status": "Collaboration deleted successfully!"})
    #
    #     except Exception as error:
    #         return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)


class CreateSourcedLabTestsView(generics.ListCreateAPIView):
    def post(self, request, *args, **kwargs):
        try:
            sourcing_lab = self.request.query_params.get('sourcing_lab', None)
            test_ids = self.request.query_params.get('test_ids', None)
            client = self.request.client
            b_id = get_business_from_client(client)
            client_b_id = None
            if b_id:
                sourcing_lab = SourcingLabRegistration.objects.get(pk=sourcing_lab)

                if not (sourcing_lab.initiator and sourcing_lab.acceptor):
                    return Response({"Error": "This action can be only done between HealthOPro users!"},
                                    status=status.HTTP_400_BAD_REQUEST)

                if b_id == sourcing_lab.initiator:
                    if sourcing_lab.is_active:
                        client_b_id = sourcing_lab.acceptor
                    else:
                        return Response({"Error": "Your collaboration is not yet Accepted by the other party, so you "
                                                  "can't view their tests!"}, status=status.HTTP_400_BAD_REQUEST)

                elif b_id == sourcing_lab.acceptor:
                    return Response({
                        "Error": "You're the Acceptor, and can't view the Tests of the other Lab. To view these tests, create a collaboration as an initiator!"},
                        status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({"Error": "You're not a member in the Collaboration!"},
                                    status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                if test_ids:
                    test_ids = list(map(int, test_ids.split(',')))

                client = get_client_from_business(client_b_id)

                created_tests_list = []
                for id in test_ids:
                    client_test_obj = None
                    client_test_department = None
                    client_test_flow = None
                    with schema_context(client.schema_name):
                        client_test_obj = LabGlobalTests.objects.get(pk=id)
                        client_test_department = client_test_obj.department.name
                        client_test_flow = client_test_obj.department.department_flow_type

                        client_sourcing_lab = SourcingLabRegistration.objects.filter(initiator=sourcing_lab.initiator,
                                                                                     acceptor=sourcing_lab.acceptor).first()

                        revised_price, created = SourcingLabRevisedTestPrice.objects.get_or_create(
                            sourcing_lab=client_sourcing_lab,
                            LabGlobalTestId=client_test_obj)
                        if created:
                            revised_price.revised_price = client_test_obj.price
                            revised_price.save()

                    department, created = LabDepartments.objects.get_or_create(name=client_test_department,
                                                                               department_flow_type=client_test_flow)

                    created_test, created = LabGlobalTests.objects.get_or_create(
                        name=client_test_obj.name,
                        department=department,
                        is_outsourcing=True,
                        outsourcing_global_test_id=client_test_obj.id,
                        sourcing_lab=sourcing_lab
                    )

                    if created:
                        created_test.price = client_test_obj.price
                        created_test.short_code = client_test_obj.short_code
                        created_test.inventory_cost = client_test_obj.inventory_cost
                        created_test.total_cost = client_test_obj.total_cost
                        created_test.is_active = client_test_obj.is_active
                        created_test.is_accreditation = client_test_obj.is_accreditation
                        created_test.target_tat = client_test_obj.target_tat
                        created_test.sample = client_test_obj.sample
                        created_test.sample_volume = client_test_obj.sample_volume
                        created_test.clinical_information = client_test_obj.clinical_information
                        created_test.is_authorization = client_test_obj.is_authorization
                        created_test.test_image = client_test_obj.test_image
                        created_test.save()

                    created_tests_list.append(created_test)

                serializer = LabGlobalTestsSerializer(created_tests_list, many=True, context={"request": self.request})

                return Response(serializer.data)
        except Exception as error:
            return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)


def copy_tests_for_manual_os_labs(sourcing_lab=None):
    tests_to_copy = LabGlobalTests.objects.filter(is_outsourcing=True, is_active=True, sourcing_lab__isnull=True)

    for test in tests_to_copy:
        try:
            created_test = LabGlobalTests.objects.create(
                name=test.name,
                department=test.department,
                is_outsourcing=True,
                sourcing_lab=sourcing_lab,
                price = test.price,
                short_code = test.short_code,
                inventory_cost = test.inventory_cost,
                total_cost = test.total_cost,
                is_active = test.is_active,
                is_accreditation = test.is_accreditation,
                target_tat = test.target_tat,
                sample = test.sample,
                sample_volume = test.sample_volume,
                clinical_information = test.clinical_information,
                is_authorization = test.is_authorization,
                expense_for_outsourcing=test.expense_for_outsourcing,
                test_image = test.test_image)

        except Exception as error:
            print(error)



class SourcingLabRevisedTestPriceViewSet(viewsets.ModelViewSet):
    queryset = SourcingLabRevisedTestPrice.objects.all()
    serializer_class = SourcingLabRevisedTestPriceSerializer

    def list(self, request, *args, **kwargs):
        sourcing_lab = self.request.query_params.get('sourcing_lab')
        query = self.request.query_params.get('query', None)
        departments = self.request.query_params.get('departments', None)
        page_size = self.request.query_params.get('page_size', None)

        if not sourcing_lab:
            return Response({"Error": "Sourcing lab is not provided!"}, status=status.HTTP_400_BAD_REQUEST)

        sourcing_lab = SourcingLabRegistration.objects.get(pk=sourcing_lab)

        if sourcing_lab.initiator and sourcing_lab.acceptor:
            initiator_client = get_client_from_business(sourcing_lab.initiator)

            imported_ids = []

            with schema_context(initiator_client.schema_name):
                client_sourcing_lab = SourcingLabRegistration.objects.filter(initiator=sourcing_lab.initiator,
                                                                             acceptor=sourcing_lab.acceptor).first()
                tests = LabGlobalTests.objects.filter(is_outsourcing=True, sourcing_lab=client_sourcing_lab)

                imported_ids = list(tests.values_list('outsourcing_global_test_id', flat=True))

            queryset = LabGlobalTests.objects.filter(id__in=imported_ids)

        else:
            queryset = LabGlobalTests.objects.filter(sourcing_lab__isnull=True)

        if departments:
            department_ids = [int(dep_id) for dep_id in departments.split(',')]
            queryset = queryset.filter(department__id__in=department_ids)

        if query is not None:
            search_query = (Q(name__icontains=query) | Q(short_code__icontains=query))
            queryset = queryset.filter(search_query)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = SourcingLabRevisedLabGlobalTestsSerializer(page, many=True,
                                                                    context={"sourcing_lab": sourcing_lab})
            return self.get_paginated_response(serializer.data)

        serializer = SourcingLabRevisedLabGlobalTestsSerializer(queryset, many=True,
                                                                context={"sourcing_lab": sourcing_lab})
        return Response(serializer.data)


class SourcingLabTestsTrackerViewset(viewsets.ModelViewSet):
    queryset = SourcingLabTestsTracker.objects.all()
    serializer_class = SourcingLabTestsTrackerSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = SourcingLabTestsTrackerFilter

    def get_queryset(self):
        patient_wise = self.request.query_params.get('patient_wise', None)
        query = self.request.query_params.get('query', None)
        sort = self.request.query_params.get('sort', None)

        if patient_wise:
            queryset = SourcingLabTestsTracker.objects.distinct('patient_id', 'sourcing_lab')
            self.serializer_class = GroupedSourcingLabTestsTrackerSerializer
        else:
            queryset = SourcingLabTestsTracker.objects.all()

        if query:
            search_query = (Q(name__icontains=query) | Q(mr_no__icontains=query) | Q(visit_id__icontains=query) | Q(
                labpatienttests__name__icontains=query) | Q(labpatienttests__short_code__icontains=query))

            patient_ids = queryset.values_list('patient_id', flat=True)
            patients = Patient.objects.filter(id__in=patient_ids)

            patients = patients.filter(search_query)

            matched_patient_ids = patients.values_list('id', flat=True)

            queryset = queryset.filter(patient_id__in=matched_patient_ids)

        if sort == '-added_on' or sort is None:
            queryset = queryset.order_by('-added_on')
        if sort == 'added_on':
            queryset = queryset.order_by('added_on')

        return queryset

    def get_same_group_tests(self, instance=None, initiator_client=None):
        with schema_context(initiator_client.schema_name):
            same_group_test_ids = [instance.lab_patient_test]

            test = LabPatientTests.objects.get(pk=instance.lab_patient_test)

            if test.department.department_flow_type.name == "Transcriptor":
                tests = LabPatientTests.objects.filter(is_outsourcing=True, patient__id=instance.patient_id)
                sourcing_lab = SourcingLabRegistration.objects.filter(initiator=instance.sourcing_lab.initiator,
                                                                      acceptor=instance.sourcing_lab.acceptor).first()

                if tests:
                    tests = tests.filter(department__department_flow_type__name="Transcriptor",
                                         sourcing_lab=sourcing_lab)
                    same_group_test_ids = list(tests.values_list('id', flat=True))

            else:
                instance_phlebomist = LabPhlebotomist.objects.filter(LabPatientTestID=test).last()

                if instance_phlebomist:
                    instance_sample = instance_phlebomist.assession_number

                    same_sample_phlebotomists = LabPhlebotomist.objects.filter(
                        LabPatientTestID__patient__id=instance.patient_id,
                        assession_number=instance_sample)

                    same_sample_phlebotomists_test_ids = list(
                        same_sample_phlebotomists.values_list('LabPatientTestID', flat=True))

                    same_group_test_ids = list(
                        same_sample_phlebotomist for same_sample_phlebotomist in same_sample_phlebotomists_test_ids)

            return same_group_test_ids

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        present_business_client = request.client
        present_business = get_business_from_client(present_business_client)
        initiator_business = instance.sourcing_lab.initiator
        acceptor_business = instance.sourcing_lab.acceptor

        initiator_client = get_client_from_business(initiator_business)

        is_sent = validated_data.get('is_sent')
        sent_at = validated_data.get('sent_at')
        if is_sent and not sent_at:
            validated_data['sent_at'] = datetime.now()

        is_received = validated_data.get('is_received')
        received_at = validated_data.get('received_at')
        if is_received and not received_at:
            validated_data['received_at'] = datetime.now()

        is_cancelled = validated_data.get('is_cancelled')
        cancelled_at = validated_data.get('cancelled_at')
        if is_cancelled and not cancelled_at:
            validated_data['cancelled_at'] = datetime.now()

        serializer.save()

        same_group_test_ids = self.get_same_group_tests(instance=instance, initiator_client=initiator_client)

        same_group_trackers = SourcingLabTestsTracker.objects.filter(sourcing_lab=instance.sourcing_lab,
                                                                     patient_id=instance.patient_id,
                                                                     lab_patient_test__in=same_group_test_ids)

        remaining_group_ids = same_group_test_ids.copy()

        remaining_group_ids.remove(instance.lab_patient_test)

        if remaining_group_ids:
            trackers = SourcingLabTestsTracker.objects.filter(sourcing_lab=instance.sourcing_lab,
                                                              patient_id=instance.patient_id,
                                                              lab_patient_test__in=remaining_group_ids)

            if trackers:
                for obj in trackers:
                    if is_sent and not sent_at:
                        obj.is_sent = True
                        obj.sent_at = instance.sent_at
                        obj.save()

                    if is_received and not received_at:
                        obj.is_received = True
                        obj.received_at = instance.received_at
                        obj.save()

                    if is_cancelled and not cancelled_at:
                        obj.is_cancelled = True
                        obj.cancelled_at = instance.cancelled_at
                        obj.save()

        if not acceptor_business:
            return Response(serializer.data)

        acceptor_client = get_client_from_business(acceptor_business)

        client_business = initiator_business if present_business == acceptor_business else acceptor_business
        client = get_client_from_business(client_business)

        with schema_context(client.schema_name):
            client_sourcing_lab = SourcingLabRegistration.objects.filter(initiator=initiator_business,
                                                                         acceptor=acceptor_business).first()

            for test in same_group_test_ids:
                tracker_at_client, created = SourcingLabTestsTracker.objects.get_or_create(
                    sourcing_lab=client_sourcing_lab,
                    lab_patient_test=test,
                    patient_id=instance.patient_id)

                if instance.to_send and instance.is_sent and not instance.is_received:
                    tracker_at_client.to_send = False
                    tracker_at_client.is_sent = True
                    tracker_at_client.sent_at = datetime.now()
                    tracker_at_client.sent_remarks = instance.sent_remarks
                    tracker_at_client.save()

                if not instance.to_send and instance.is_sent and instance.is_received:
                    tracker_at_client.is_received = True
                    tracker_at_client.received_at = datetime.now()
                    tracker_at_client.received_remarks = instance.received_remarks
                    tracker_at_client.save()

                if instance.is_cancelled:
                    tracker_at_client.is_cancelled = True
                    tracker_at_client.cancelled_at = datetime.now()
                    tracker_at_client.cancellation_remarks = instance.cancellation_remarks
                    tracker_at_client.save()

        return Response(serializer.data)


class GetAndCreatePatientForSourcingLab(generics.ListAPIView):
    def post(self, request, *args, **kwargs):
        sourcing_lab = self.request.query_params.get('sourcing_lab')
        patient_ids = self.request.query_params.get('patient_ids')

        if not patient_ids:
            return Response({"Error": "Patients IDs are mandatory!"}, status=status.HTTP_400_BAD_REQUEST)

        patient_ids = [patient_id.strip() for patient_id in patient_ids.split(',') if patient_id.strip()]

        sourcing_lab = SourcingLabRegistration.objects.get(pk=sourcing_lab)

        present_business_client = request.client
        present_business = get_business_from_client(present_business_client)
        initiator_business = sourcing_lab.initiator
        acceptor_business = sourcing_lab.acceptor

        client_business = initiator_business if present_business == acceptor_business else acceptor_business

        client = get_client_from_business(client_business)

        initiator_client = get_client_from_business(initiator_business)
        acceptor_client = get_client_from_business(acceptor_business)

        trackers = SourcingLabTestsTracker.objects.filter(is_received=False, is_cancelled=False,
                                                          sourcing_lab=sourcing_lab, patient_id__in=patient_ids)

        if trackers:
            return Response({"Status": "Some tests are pending to be collected or cancelled!"})

        for patient_id in patient_ids:
            patient_data = None
            lab_tests = []
            phlebotomists_data = []
            transcriptor_data = []
            lab_staff = LabStaff.objects.get(name=client_business.organization_name)

            with schema_context(initiator_client.schema_name):
                client_outsourcing_lab = SourcingLabRegistration.objects.filter(
                    initiator=initiator_business, acceptor=acceptor_business).first()

                trackers = SourcingLabTestsTracker.objects.filter(sourcing_lab=client_outsourcing_lab,
                                                                  patient_id=patient_id, is_received=True,
                                                                  is_cancelled=False)

                for track in trackers:
                    test = LabPatientTests.objects.get(pk=track.lab_patient_test)
                    global_test_id = test.LabGlobalTestId.outsourcing_global_test_id
                    if not test.department.department_flow_type.name == "Transcriptor":
                        phlebotomist = LabPhlebotomist.objects.filter(LabPatientTestID=test).last()
                        phlebotomist_dictionary = model_to_dict(phlebotomist)
                        necessary_fields = ['is_collected', 'collected_at']
                        phlebotomist_dictionary = {key: value for key, value in phlebotomist_dictionary.items() if
                                                   key in necessary_fields}
                        phlebotomist_dictionary['LabGlobalTestId'] = global_test_id

                        phlebotomists_data.append(phlebotomist_dictionary)
                    else:
                        transcriptor_data.append({"LabGlobalTestId": global_test_id})

                patient = Patient.objects.get(pk=patient_id)
                patient_dictionary = model_to_dict(patient)
                necessary_fields = ['title', 'name', 'age', 'dob', 'ULabPatientAge', 'gender', 'attender_name',
                                    'attender_relationship_title', 'area', 'address']

                patient_dictionary = {key: value for key, value in patient_dictionary.items() if
                                      key in necessary_fields}
                patient_dictionary['mobile_number'] = lab_staff.mobile_number
                patient_dictionary['created_by'] = lab_staff
                patient_dictionary['last_updated_by'] = lab_staff

                patient_dictionary['is_sourcing_lab'] = True

                patient_dictionary['title'] = ULabPatientTitles.objects.get(pk=patient_dictionary['title'])
                patient_dictionary['ULabPatientAge'] = ULabPatientAge.objects.get(
                    pk=patient_dictionary['ULabPatientAge'])
                patient_dictionary['gender'] = ULabPatientGender.objects.get(pk=patient_dictionary['gender'])
                if patient_dictionary['attender_relationship_title']:
                    patient_dictionary['attender_relationship_title'] = ULabPatientAttenderTitles.objects.get(
                        pk=patient_dictionary['attender_relationship_title'])

                patient_dictionary['client'] = present_business_client

                patient_data = patient_dictionary

            for data in phlebotomists_data:
                data['LabGlobalTestId'] = LabGlobalTests.objects.get(pk=data['LabGlobalTestId'])
                lab_tests.append({"LabGlobalTestId": data['LabGlobalTestId'], "sourcing_lab": sourcing_lab})

            for data in transcriptor_data:
                data['LabGlobalTestId'] = LabGlobalTests.objects.get(pk=data['LabGlobalTestId'])
                lab_tests.append(
                    {"LabGlobalTestId": data['LabGlobalTestId'], "status_id": 2, "sourcing_lab": sourcing_lab})

            patient_data['lab_tests'] = lab_tests

            patient = PatientSerializer.create(self=None, validated_data=None, patient_data=patient_data)

            sourcing_lab = SourcingLabRegistration.objects.filter(initiator=initiator_business,
                                                                  acceptor=acceptor_business).first()

            for test in patient.labpatienttests_set.all():
                if sourcing_lab:
                    test.sourcing_lab = sourcing_lab
                    test.save()

                global_test = test.LabGlobalTestId
                department_flow_type = test.department.department_flow_type.name

                if department_flow_type == "Transcriptor":
                    # LabTechnicians.objects.create(LabPatientTestID=test)
                    pass
                else:
                    for phlebotomist in phlebotomists_data:
                        if global_test == phlebotomist['LabGlobalTestId']:
                            phlebotomist_data = {"LabPatientTestID": test,
                                                 "is_collected": True,
                                                 "collected_at": phlebotomist['collected_at'],
                                                 "collected_by": lab_staff,
                                                 "received_at": datetime.now(),
                                                 "received_by": lab_staff
                                                 }
                            lab = LabPhlebotomistsViewSet()
                            lab.create(phlebotomist_data=phlebotomist_data)

                    phlebotomists = LabPhlebotomist.objects.filter(LabPatientTestID__patient=patient)

                    for phlebotomist in phlebotomists:
                        phlebotomist.is_received = True
                        phlebotomist.received_by = get_lab_staff_from_request(request)
                        phlebotomist.save()

            with schema_context(initiator_client.schema_name):
                client_outsourcing_lab = SourcingLabRegistration.objects.filter(initiator=initiator_business,
                                                                                acceptor=acceptor_business).last()

                trackers = SourcingLabTestsTracker.objects.filter(sourcing_lab=client_outsourcing_lab,
                                                                  patient_id=patient_id)

                if trackers:
                    for tracker in trackers:
                        tracker.patient_id_at_client = patient.id
                        tracker.save()

            with schema_context(acceptor_client.schema_name):
                client_outsourcing_lab = SourcingLabRegistration.objects.filter(initiator=initiator_business,
                                                                                acceptor=acceptor_business).last()

                trackers = SourcingLabTestsTracker.objects.filter(sourcing_lab=client_outsourcing_lab,
                                                                  patient_id=patient_id)

                if trackers:
                    for tracker in trackers:
                        tracker.patient_id_at_client = patient.id
                        tracker.save()

        return Response({"Status": "Patient Data Added successfully!"})


class GetPatientTestsStatusFromSourcingLab(viewsets.ModelViewSet):
    serializer_class = StandardViewPatientSerializer

    def list(self, request, *args, **kwargs):
        try:
            sourcing_lab = self.request.query_params.get('sourcing_lab', None)
            patient_ids = self.request.query_params.get('patient_ids', [])
            date = self.request.query_params.get('date', None)
            date_range_after = self.request.query_params.get('date_range_after', None)
            date_range_before = self.request.query_params.get('date_range_before', None)
            sort = self.request.query_params.get('sort', None)
            query = self.request.query_params.get('query', None)
            payment_status = self.request.query_params.get('payment_status', None)
            departments_details = self.request.query_params.get('departments_details', None)
            page_size = self.request.query_params.get('page_size', None)

            if not sourcing_lab:
                return Response({"Error": "Sourcing lab is required"}, status=status.HTTP_400_BAD_REQUEST)

            sourcing_lab = SourcingLabRegistration.objects.get(pk=sourcing_lab)

            if sourcing_lab.initiator and sourcing_lab.acceptor:
                client = get_client_from_business(sourcing_lab.acceptor)

                with schema_context(client.schema_name):
                    lab_staff = LabStaff.objects.filter(name=sourcing_lab.initiator.organization_name).first()

                    if lab_staff:
                        pass
                    else:
                        return Response([])
                    queryset = Patient.objects.filter(created_by=lab_staff).distinct().prefetch_related(
                        Prefetch('labpatienttests_set', queryset=LabPatientTests.objects.all().order_by('id')),
                    ).select_related('labpatientinvoice')

                    if date:
                        date = datetime.strptime(date, '%Y-%m-%d').date()
                        start_date = datetime.combine(date, datetime.min.time())
                        end_date = start_date + timedelta(days=1) - timedelta(seconds=1)
                        queryset = queryset.filter(added_on__range=(start_date, end_date))

                    if date_range_after or date_range_before:
                        if date_range_after:
                            date_after = datetime.strptime(date_range_after, '%Y-%m-%d').date()
                            start_date = datetime.combine(date_after, datetime.min.time())
                        else:
                            start_date = None

                        if date_range_before:
                            date_before = datetime.strptime(date_range_before, '%Y-%m-%d').date()
                            end_date = datetime.combine(date_before, datetime.max.time())
                        else:
                            end_date = None

                        if start_date and end_date:
                            queryset = queryset.filter(added_on__range=(start_date, end_date))
                        elif start_date:
                            queryset = queryset.filter(added_on__gte=start_date)
                        elif end_date:
                            queryset = queryset.filter(added_on__lte=end_date)

                    if payment_status == 'paid':
                        queryset = queryset.filter(labpatientinvoice__total_paid__gt=0, labpatientinvoice__total_due=0)
                    elif payment_status == 'due':
                        queryset = queryset.filter(labpatientinvoice__total_due__gt=0)
                    elif payment_status == 'partial':
                        queryset = queryset.filter(labpatientinvoice__total_due__gt=0,
                                                   labpatientinvoice__total_paid__gt=0)

                    if departments_details:
                        departments = [department.strip() for department in departments_details.split(',') if
                                       department.strip()]
                        department_query = Q(labpatienttests__department__id__in=departments)

                        queryset = queryset.filter(department_query)

                    if query is not None:
                        search_query = (
                                Q(name__icontains=query) | Q(mr_no__icontains=query) | Q(visit_id__icontains=query) | Q(
                            labpatienttests__name__icontains=query) | Q(
                            labpatienttests__short_code__icontains=query) | Q(
                            mobile_number__icontains=query))

                        queryset = queryset.filter(search_query)

                    if sort == '-added_on':
                        queryset = queryset.order_by('-added_on')
                    if sort == 'added_on':
                        queryset = queryset.order_by('added_on')

                    if page_size == 'all':
                        serializer = StandardViewPatientSerializer(self.queryset, many=True)
                        return Response(serializer.data)

                    page = self.paginate_queryset(queryset)
                    if page is not None:
                        serializer = StandardViewPatientSerializer(page, many=True)
                        return self.get_paginated_response(serializer.data)

                    serializer = StandardViewPatientSerializer(self.queryset, many=True)
                    return Response(serializer.data)

            else:
                if sourcing_lab.initiator:
                    trackers = SourcingLabTestsTracker.objects.filter(sourcing_lab=sourcing_lab, to_send=True,
                                                                      is_sent=True)

                    lab_patient_test_list = list(trackers.values_list('lab_patient_test', flat=True))

                    lab_tests_queryset = LabPatientTests.objects.filter(id__in=lab_patient_test_list).order_by('id')

                    if lab_tests_queryset:
                        queryset = Patient.objects.filter(
                            labpatienttests__in=lab_tests_queryset
                        ).distinct().prefetch_related(
                            Prefetch('labpatienttests_set', queryset=lab_tests_queryset),
                        ).select_related('labpatientinvoice')
                    else:
                        return Response([])

                    if date:
                        date = datetime.strptime(date, '%Y-%m-%d').date()
                        start_date = datetime.combine(date, datetime.min.time())
                        end_date = start_date + timedelta(days=1) - timedelta(seconds=1)
                        queryset = queryset.filter(added_on__range=(start_date, end_date))

                    if date_range_after or date_range_before:
                        if date_range_after:
                            date_after = datetime.strptime(date_range_after, '%Y-%m-%d').date()
                            start_date = datetime.combine(date_after, datetime.min.time())
                        else:
                            start_date = None

                        if date_range_before:
                            date_before = datetime.strptime(date_range_before, '%Y-%m-%d').date()
                            end_date = datetime.combine(date_before, datetime.max.time())
                        else:
                            end_date = None

                        if start_date and end_date:
                            queryset = queryset.filter(added_on__range=(start_date, end_date))
                        elif start_date:
                            queryset = queryset.filter(added_on__gte=start_date)
                        elif end_date:
                            queryset = queryset.filter(added_on__lte=end_date)

                    if payment_status == 'paid':
                        queryset = queryset.filter(labpatientinvoice__total_paid__gt=0, labpatientinvoice__total_due=0)
                    elif payment_status == 'due':
                        queryset = queryset.filter(labpatientinvoice__total_due__gt=0)
                    elif payment_status == 'partial':
                        queryset = queryset.filter(labpatientinvoice__total_due__gt=0,
                                                   labpatientinvoice__total_paid__gt=0)

                    if departments_details:
                        departments = [department.strip() for department in departments_details.split(',') if
                                       department.strip()]
                        department_query = Q(labpatienttests__department__id__in=departments)

                        queryset = queryset.filter(department_query)

                    if query is not None:
                        search_query = (
                                Q(name__icontains=query) | Q(mr_no__icontains=query) | Q(visit_id__icontains=query) | Q(
                            labpatienttests__name__icontains=query) | Q(
                            labpatienttests__short_code__icontains=query) | Q(
                            mobile_number__icontains=query))

                        queryset = queryset.filter(search_query)

                    if sort == '-added_on':
                        queryset = queryset.order_by('-added_on')
                    if sort == 'added_on':
                        queryset = queryset.order_by('added_on')

                    if page_size == 'all':
                        serializer = StandardViewPatientSerializer(self.queryset, many=True)
                        return Response(serializer.data)

                    page = self.paginate_queryset(queryset)
                    if page is not None:
                        serializer = StandardViewPatientSerializer(page, many=True)
                        return self.get_paginated_response(serializer.data)

                    serializer = StandardViewPatientSerializer(self.queryset, many=True)
                    return Response(serializer.data)
                else:
                    # trackers = SourcingLabTestsTracker.objects.filter(sourcing_lab=sourcing_lab, to_send=True,
                    #                                                   is_sent=True)
                    #
                    # lab_patient_test_list = list(trackers.values_list('lab_patient_test', flat=True))
                    #
                    # lab_tests_queryset = LabPatientTests.objects.filter(id__in=lab_patient_test_list).order_by('id')

                    queryset = Patient.objects.filter(
                        referral_lab=sourcing_lab
                    ).distinct().prefetch_related(
                        Prefetch('labpatienttests_set'),
                    ).select_related('labpatientinvoice')

                    if queryset:
                        pass
                    else:
                        return Response([])

                    if date:
                        date = datetime.strptime(date, '%Y-%m-%d').date()
                        start_date = datetime.combine(date, datetime.min.time())
                        end_date = start_date + timedelta(days=1) - timedelta(seconds=1)
                        queryset = queryset.filter(added_on__range=(start_date, end_date))

                    if date_range_after or date_range_before:
                        if date_range_after:
                            date_after = datetime.strptime(date_range_after, '%Y-%m-%d').date()
                            start_date = datetime.combine(date_after, datetime.min.time())
                        else:
                            start_date = None

                        if date_range_before:
                            date_before = datetime.strptime(date_range_before, '%Y-%m-%d').date()
                            end_date = datetime.combine(date_before, datetime.max.time())
                        else:
                            end_date = None

                        if start_date and end_date:
                            queryset = queryset.filter(added_on__range=(start_date, end_date))
                        elif start_date:
                            queryset = queryset.filter(added_on__gte=start_date)
                        elif end_date:
                            queryset = queryset.filter(added_on__lte=end_date)

                    if payment_status == 'paid':
                        queryset = queryset.filter(labpatientinvoice__total_paid__gt=0,
                                                   labpatientinvoice__total_due=0)
                    elif payment_status == 'due':
                        queryset = queryset.filter(labpatientinvoice__total_due__gt=0)
                    elif payment_status == 'partial':
                        queryset = queryset.filter(labpatientinvoice__total_due__gt=0,
                                                   labpatientinvoice__total_paid__gt=0)

                    if departments_details:
                        departments = [department.strip() for department in departments_details.split(',') if
                                       department.strip()]
                        department_query = Q(labpatienttests__department__id__in=departments)

                        queryset = queryset.filter(department_query)

                    if query is not None:
                        search_query = (
                                Q(name__icontains=query) | Q(mr_no__icontains=query) | Q(
                            visit_id__icontains=query) | Q(
                            labpatienttests__name__icontains=query) | Q(
                            labpatienttests__short_code__icontains=query) | Q(
                            mobile_number__icontains=query))
                if query is not None:
                    search_query = (
                            Q(name__icontains=query) | Q(mr_no__icontains=query) | Q(visit_id__icontains=query) |
                            Q(labpatienttests__name__icontains=query) | Q(
                        labpatienttests__short_code__icontains=query) |
                            Q(mobile_number__icontains=query))

                    queryset = queryset.filter(search_query)

                    if sort == '-added_on':
                        queryset = queryset.order_by('-added_on')
                    if sort == 'added_on':
                        queryset = queryset.order_by('added_on')

                    if page_size == 'all':
                        serializer = StandardViewPatientSerializer(self.queryset, many=True)
                        return Response(serializer.data)

                    page = self.paginate_queryset(queryset)
                    if page is not None:
                        serializer = StandardViewPatientSerializer(page, many=True)
                        return self.get_paginated_response(serializer.data)

                    serializer = StandardViewPatientSerializer(self.queryset, many=True)
                    return Response(serializer.data)

            # patient_ids_list = []
            #
            # if patient_ids:
            #     patient_ids = [patient_id.strip() for patient_id in patient_ids.split(',') if patient_id.strip()]
            #
            #     trackers = SourcingLabTestsTracker.objects.filter(sourcing_lab=sourcing_lab, is_received=True,
            #                                                       patient_id__in=patient_ids)
            #     if trackers:
            #         patient_ids_list = list(trackers.values_list('patient_id_at_client', flat=True))
            #         print(patient_ids_list)


        except Exception as error:
            return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)


class GetPrintOfLabPatientTests(generics.ListAPIView):
    def get(self, request, *args, **kwargs):
        try:
            sourcing_lab = self.request.query_params.get('sourcing_lab', None)
            test_ids = self.request.query_params.get('test_ids', None)
            if test_ids:
                test_ids = list(map(int, test_ids.split(',')))
            patient_id = self.request.query_params.get('patient_id', None)

            sourcing_lab = SourcingLabRegistration.objects.get(pk=sourcing_lab)

            present_client = self.request.client
            present_business = get_business_from_client(present_client)

            client_business = None

            if present_business == sourcing_lab.initiator:
                client_business = sourcing_lab.acceptor
            elif present_business == sourcing_lab.acceptor:
                # return Response([])
                client_business = sourcing_lab.acceptor
            client = get_client_from_business(client_business)

            with schema_context(client.schema_name):
                patient = Patient.objects.get(pk=patient_id)

                if sourcing_lab.credit_payment:
                    pass
                else:
                    paid_percentage = patient.labpatientinvoice.total_paid / patient.labpatientinvoice.total_price * 100

                    percentage_to_be_paid = sourcing_lab.min_print_amount
                    if paid_percentage >= percentage_to_be_paid:
                        pass
                    else:
                        return Response({"Error": f"Minimum payment to print({int(percentage_to_be_paid)}%) is not paid!"},
                                        status=status.HTTP_400_BAD_REQUEST)

                test_report = GeneratePatientTestReportViewset()
                print = test_report.create(patient_id=patient_id, client_id=client.id, test_ids=test_ids, sourcing_lab_for_settings=sourcing_lab)

                return Response(print.data)
        except Exception as error:
            return Response({"Error": f"{error}"})


class SourcingLabPatientReportUploadsViewset(viewsets.ModelViewSet):
    queryset = SourcingLabPatientReportUploads.objects.all()
    serializer_class = SourcingLabPatientReportUploadsSerializer

    def get_queryset(self):
        queryset = SourcingLabPatientReportUploads.objects.all()
        patient = self.request.query_params.get('patient', None)
        if patient:
            queryset = queryset.filter(patient__id=patient)

        return queryset


class CheckPaymentForReferralPatients(generics.CreateAPIView):
    serializer_class = PatientSerializer

    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            validated_data = serializer.validated_data

            referral_lab = validated_data['referral_lab']

            if referral_lab:
                pass
            else:
                return Response({"Error": "No referral lab is selected!"}, status=status.HTTP_400_BAD_REQUEST)

            discount_amt = validated_data.pop('discount_amt', 0)
            lab_discount_type_id = validated_data.pop('lab_discount_type_id', None)
            lab_tests_data = validated_data.pop('lab_tests', [])
            payments = validated_data.pop('payments', [])
            client = validated_data.pop('client', None)
            lab_packages_data = validated_data.pop('lab_packages', [])

            total_cost = 0

            if lab_packages_data:
                for lab_package_data in lab_packages_data:
                    lab_package_data = lab_package_data['LabGlobalPackageId']

                    total_cost += lab_package_data.offer_price

            if lab_tests_data:
                for lab_test_data in lab_tests_data:
                    revised_price_instance = SourcingLabRevisedTestPrice.objects.filter(
                        sourcing_lab=validated_data['referral_lab'],
                        LabGlobalTestId=lab_test_data['LabGlobalTestId']
                    ).first()

                    if revised_price_instance:
                        total_cost += revised_price_instance.revised_price
                    else:
                        global_instance = lab_test_data['LabGlobalTestId']
                        total_cost += global_instance.price

            discount = 0
            paid_amount = 0

            if payments:
                for payment in payments:
                    paid_amount += payment['paid_amount']

            total_due = total_cost

            if discount_amt:
                discount += discount_amt
            elif lab_discount_type_id:
                discount_type = LabDiscountType.objects.get(id=lab_discount_type_id)
                if discount_type.is_percentage:
                    discount += total_due * (discount_type.number / 100)
                elif not discount_type.is_percentage:
                    discount += discount_type.number

            if referral_lab.type == 'Credit':
                return Response({"Status": "Minimum payment is not necessary!"})
            else:
                min_payment_required = (referral_lab.min_paid_amount/100) * (total_due - discount)
                if min_payment_required <= paid_amount:
                    return Response({"Status": "Minimum payment received!"})
                else:
                    return Response({"Error": f"Minimum payment of Rs.{min_payment_required:.2f} is required!"},
                                    status=status.HTTP_400_BAD_REQUEST)

        except Exception as error:
            return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)





class ReferralLabLoginActionView(generics.CreateAPIView):
    def create(self, request, *args, **kwargs):
        try:
            data=request.data
            sourcing_lab_id = data.get('sourcing_lab')
            sourcing_lab = SourcingLabRegistration.objects.get(pk=sourcing_lab_id)

            lab_staff, created = LabStaff.objects.get_or_create(name=sourcing_lab.organization_name,mobile_number=sourcing_lab.phone_number)

            referral_lab_role, created = LabStaffRole.objects.get_or_create(name='SourcingLab')

            lab_staff.role = referral_lab_role
            lab_staff.save()

            lab_menu_access, created = LabMenuAccess.objects.get_or_create(lab_staff=lab_staff)
            menus = ULabMenus.objects.filter(label__in=['Sourcing Patients'])
            lab_menu_access.lab_menu.set(menus)

            user_permissions, created = UserPermissionsAccess.objects.get_or_create(lab_staff=lab_staff)

            controls = BusinessControls.objects.first()
            if controls and controls.multiple_branches:
                default_branch_obj, created = LabStaffDefaultBranch.objects.get_or_create(lab_staff=lab_staff)
                if created:
                    client = request.client
                    business = BusinessProfiles.objects.filter(organization_name=client.name)
                    branches = BusinessAddresses.objects.filter(b_id=business)
                    default_branch_obj.default_branch.set(branches)

            try:
                user = HealthOProUser.objects.get(phone_number=lab_staff.mobile_number)

            except HealthOProUser.DoesNotExist:
                user = HealthOProUser.objects.create(
                    full_name=lab_staff.name,
                    phone_number=lab_staff.mobile_number,
                    user_type=UserType.objects.get(pk=2),
                    HealthcareRegistryType=HealthcareRegistryType.objects.get(pk=1)
                )


            try:
                otp = OTP.objects.get(pro_user_id=user)
            except Exception as error:
                otp_code = ''.join(random.choices(string.digits, k=4))
                OTP.objects.create(pro_user_id=user, otp_code=otp_code)

            user_tenant, created = UserTenant.objects.get_or_create(
                user=user,
                client=request.client
            )

            if user_tenant.is_active:
                user_tenant.is_active = False
                user_tenant.save()

                lab_staff.is_login_access = False
                lab_staff.save()

                blacklist_user_tokens(user)
                return Response({"Status": "UserTenant Is Now Deactived!",
                                 "user_tenant_id": user_tenant.id,
                                 "user_tenant.isactive": user_tenant.is_active})
            else:
                user_tenant.is_active = True
                user_tenant.save()
                lab_staff.is_login_access = True
                lab_staff.save()
                return Response({"Status": "UserTenant Is Now Active!",
                                 "user_tenant_id": user_tenant.id,
                                 "user_tenant.isactive": user_tenant.is_active})


        except Exception as error:
            return Response({"Error": f"{error}"},status=status.HTTP_400_BAD_REQUEST)



class SyncRevisedPriceOfReferralLabsView(generics.CreateAPIView):
    def create(self, request, *args, **kwargs):
        data = request.data
        source = data.get('source')
        target = data.get('target')

        source_lab = SourcingLabRegistration.objects.get(pk=source)
        target_lab = SourcingLabRegistration.objects.get(pk=target)

        if source_lab.is_referral_lab and target_lab.is_referral_lab:
            pass
        else:
            if not source_lab.is_referral_lab:
                return Response({"Error" : "Selected Source lab is not a Referral Lab!"},status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"Error" : "Selected Target lab is not a Referral Lab!"},status=status.HTTP_400_BAD_REQUEST)

        revised_prices_of_source = SourcingLabRevisedTestPrice.objects.filter(sourcing_lab=source_lab)

        for revised_price_obj in revised_prices_of_source:
            revised_price_at_target, created = SourcingLabRevisedTestPrice.objects.get_or_create(sourcing_lab=target_lab, LabGlobalTestId=revised_price_obj.LabGlobalTestId)
            revised_price_at_target.revised_price = revised_price_obj.revised_price
            revised_price_at_target.save()

        return Response({"Status":"Revised prices are synced!"})


class GetSourcingLabFromLabStaff(generics.ListAPIView):
    def get(self, request, *args, **kwargs):
        try:
            lab_staff_id = self.request.query_params.get('lab_staff')
            lab_staff = LabStaff.objects.get(pk=lab_staff_id)

            sourcing_lab = SourcingLabRegistration.objects.filter(organization_name=lab_staff.name,
                                                                  phone_number=lab_staff.mobile_number,
                                                                  is_referral_lab=True).first()

            if sourcing_lab:
                serializer = SourcingLabRegistrationSerializer(sourcing_lab)
                return Response(serializer.data)
            else:
                return Response({"Error":"Sourcing Lab does not exist!"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as error:
            return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)




class SourcingLabPaymentsViewSet(viewsets.ModelViewSet):
    queryset = SourcingLabPayments.objects.all()
    serializer_class = SourcingLabPaymentsSerializer

    def get_queryset(self):
        queryset = SourcingLabPayments.objects.all().order_by('-id')
        sourcing_lab = self.request.query_params.get('sourcing_lab', None)

        if sourcing_lab is not None:
            queryset = queryset.filter(sourcing_lab__id=sourcing_lab)

        return queryset

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer_data = serializer.validated_data
            sourcing_lab = serializer_data.get('sourcing_lab')
            paid_amount = serializer_data.get('paid_amount')

            previous_balance = sourcing_lab.available_balance
            available_balance = previous_balance + paid_amount
            sourcing_lab.available_balance = available_balance
            sourcing_lab.save()

            serializer_data['previous_balance'] = previous_balance
            serializer_data['available_balance'] = available_balance

            serializer.save()

            return Response(serializer.data)

        except Exception as error:
            print(error)
            return Response({"Error":f"{error}"}, status=status.HTTP_400_BAD_REQUEST)




class SourcingLabLetterHeadSettingsViewSet(viewsets.ModelViewSet):
    queryset = SourcingLabLetterHeadSettings.objects.all()
    serializer_class = SourcingLabLetterHeadSettingsSerializer


    def get_queryset(self):
        queryset = SourcingLabLetterHeadSettings.objects.all()
        sourcing_lab = self.request.query_params.get('sourcing_lab', None)

        client = self.request.client

        client_letterhead_settings = LetterHeadSettings.objects.filter(client=client).first()

        b_id = BusinessProfiles.objects.get(organization_name=client.name)

        if sourcing_lab is not None:
            queryset = SourcingLabLetterHeadSettings.objects.filter(sourcing_lab__id=sourcing_lab)

            if queryset:
                pass
            else:
                obj = SourcingLabLetterHeadSettings.objects.create(sourcing_lab=SourcingLabRegistration.objects.get(pk=sourcing_lab),
                                                                header_height = client_letterhead_settings.header_height,
                                                                footer_height = client_letterhead_settings.footer_height,
                                                                display_letterhead = client_letterhead_settings.display_letterhead,
                                                                letterhead = b_id.b_letterhead,
                                                                margin_left = client_letterhead_settings.margin_left,
                                                                margin_right = client_letterhead_settings.margin_right,
                                                                display_page_no = client_letterhead_settings.display_page_no,
                                                                default_font = client_letterhead_settings.default_font)

        return queryset

