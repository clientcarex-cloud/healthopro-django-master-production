import random
import string
from django.core.cache import cache
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from geopy import Nominatim
from geopy.exc import GeocoderTimedOut
from rest_framework import viewsets, generics
from rest_framework.views import APIView
from datetime import datetime, timedelta

from accounts.models import LabExpenses
from healtho_pro_user.models.universal_models import HealthcareRegistryType, UserType
from healtho_pro_user.models.users_models import HealthOProUser, UserTenant, OTP
from healtho_pro_user.serializers.users_serializers import UserSerializer
from healtho_pro_user.views.users_views import blacklist_user_tokens
from pro_laboratory.filters import LabStaffFilter, LabStaffAttendanceDetailsFilter
from pro_laboratory.models.global_models import LabGlobalTests, LabStaff, LabDiscountType, LabReportsTemplates, \
    LabWordReportTemplate, \
    LabFixedParametersReportTemplate, LabStaffRole, LabMenuAccess, LabStaffRolePermissions, LabEmploymentType, \
    LabBranch, LabShift, LabStaffLoginAccess, LabWorkingDays, LabBloodGroup, \
    LabMaritalStatus, LabDoctorRole, Methodology, LabDepartments, BodyParts, LabGlobalPackages, DoctorAccess, \
    DefaultTestParameters, LabFixedReportNormalReferralRanges, \
    LabStaffAttendanceDetails, LabStaffJobDetails, LabStaffPayRoll, LabStaffLeaveRequest, LeavePolicy, \
    LabStaffDefaultBranch
from pro_laboratory.models.patient_models import LabPatientReceipts, LabPatientRefund
from pro_laboratory.models.sourcing_lab_models import SourcingLabRegistration
from pro_laboratory.models.universal_models import ActivityLogs, ChangesInModels
from pro_laboratory.serializers.global_serializers import LabGlobalTestsSerializer, LabStaffSerializer, \
    LabDiscountTypeSerializer, LabReportsTemplatesSerializer, LabWordReportTemplateSerializer, \
    LabFixedParametersReportTemplateSerializer, LabStaffAccessSerializer, \
    LabStaffRoleSerializer, LabMenuAccessSerializer, LabStaffRolePermissionsSerializer, \
    LabBranchSerializer, LabShiftSerializer, LabStaffLoginActionSerializer, LabWorkingDaysSerializer, \
    LabBloodGroupSerializer, LabMaritalStatusSerializer, LabDoctorRoleSerializer, \
    LabGlobalTestMethodologySerializer, LabDepartmentsSerializer, BodyPartsSerializer, LabGlobalPackagesGetSerializer, \
    LabGlobalPackagesSerializer, DoctorAccessSerializer, LabStaffDataSerializer, DefaultTestParametersSerializer, \
    LabFixedReportNormalReferralRangesSerializer, LabStaffAttendanceDetailsSerializer, \
    LabStaffAttendanceGetDetailsSerializer, LabStaffPayRollSerializer, LabStaffJobDetailsSerializer, \
    LabStaffLeaveRequestSerializer, LeavePolicySerializer, LabStaffWithPayRollSerializer, \
    LabStaffDefaultBranchSerializer
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, F, Value, DecimalField
from django.db.models.functions import Coalesce

from pro_laboratory.views.labtechnicians_views import logger
from pro_laboratory.views.universal_views import return_word_report_header
from pro_universal_data.models import LabStaffAttendanceStatus, ULabMenus
from pro_laboratory.models.marketing_models import MarketingExecutiveTargets
from pro_laboratory.views.marketing_views import calculate_target_achieved_by_marketing_executive
from pro_laboratory.serializers.global_serializers import calculate_extra_and_deficit_hours


class LabDepartmentsViewSet(viewsets.ModelViewSet):
    queryset = LabDepartments.objects.all()
    serializer_class = LabDepartmentsSerializer




class BodyPartsViewSet(viewsets.ModelViewSet):
    queryset = BodyParts.objects.all()
    serializer_class = BodyPartsSerializer


class LabGlobalTestsViewSet(viewsets.ModelViewSet):
    serializer_class = LabGlobalTestsSerializer

    def get_queryset(self):
        queryset = LabGlobalTests.objects.all()
        query = self.request.query_params.get('q', None)
        departments = self.request.query_params.get('departments', None)
        sourcing_lab = self.request.query_params.get('sourcing_lab', None)
        if query is not None:
            search_query = ((Q(name__icontains=query) | Q(short_code__icontains=query)) & Q(department__is_active=True))
            queryset = queryset.filter(search_query)
        if departments:
            department_ids = [int(dep_id) for dep_id in departments.split(',')]
            queryset = queryset.filter(department__id__in=department_ids)
        if sourcing_lab:
            if sourcing_lab == 'false':
                queryset = queryset.filter(sourcing_lab__isnull=True)
            else:
                sourcing_lab_ids = [int(id) for id in sourcing_lab.split(',')]
                queryset = queryset.filter(sourcing_lab__id__in=sourcing_lab_ids)

        queryset = queryset.filter(department__is_active=True)
        queryset = queryset.order_by('department__id', 'added_on')
        return queryset

    def perform_create(self, serializer):
        serializer.save()
        instance = serializer.instance

        if instance.is_outsourcing and instance.sourcing_lab is None:
            sourcing_labs = SourcingLabRegistration.objects.filter(initiator__isnull=False, acceptor__isnull=True)
            test = instance

            for sourcing_lab in sourcing_labs:
                created_test = LabGlobalTests.objects.create(
                    name=test.name,
                    department=test.department,
                    is_outsourcing=True,
                    sourcing_lab=sourcing_lab,
                    price=test.price,
                    short_code=test.short_code,
                    inventory_cost=test.inventory_cost,
                    total_cost=test.total_cost,
                    is_active=test.is_active,
                    is_accreditation=test.is_accreditation,
                    target_tat=test.target_tat,
                    sample=test.sample,
                    sample_volume=test.sample_volume,
                    clinical_information=test.clinical_information,
                    is_authorization=test.is_authorization,
                    expense_for_outsourcing=test.expense_for_outsourcing,
                    test_image=test.test_image)
        self.invalidate_cache()



    def perform_update(self, serializer):
        super().perform_update(serializer)
        self.invalidate_cache()

    def perform_destroy(self, instance):
        super().perform_destroy(instance)
        self.invalidate_cache()

    def invalidate_cache(self):
        client_id = self.request.client
        try:
            if client_id:
                cache_key_prefix = f'master_search_for_tests_{client_id}_'
                keys_to_delete = [key for key in cache.keys(f'{cache_key_prefix}*')]
                for key in keys_to_delete:
                    cache.delete(key)
                    print(f'Deleted cache key: {key}')
        except Exception as e:
            print(f"Cache invalidation failed: {e}")


class LabStaffViewSet(viewsets.ModelViewSet):
    serializer_class = LabStaffSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = LabStaffFilter

    def get_queryset(self):
        try:
            queryset = LabStaff.objects.all().order_by('id')
            query = self.request.query_params.get('q', None)
            sort = self.request.query_params.get('sort', None)
            role = self.request.query_params.get('role', None)

            client = self.request.client
            cache_key = f'lab_staff_{client}_{query}_{sort}_{role}'
            cache_data = cache.get(cache_key)
            if cache_data:
                print('cache data of labstaff',cache_data)
                return cache_data
            print('normal data of labstaff, not cache')
            if query is not None:
                search_query = Q(name__icontains=query) | Q(branch__name__icontains=query) | Q(
                    mobile_number__icontains=query)
                queryset = queryset.filter(search_query)
            if role is not None:
                queryset = queryset.filter(role__name='MarketingExecutive')

            if sort == '-added_on':
                queryset = queryset.order_by('-added_on')
            if sort == 'added_on':
                queryset = queryset.order_by('added_on')
            cache.set(cache_key, queryset)
            return queryset
        except Exception as e:
            print('in exception of labstaff',e)
            queryset = LabStaff.objects.all().order_by('id')
            query = self.request.query_params.get('q', None)
            sort = self.request.query_params.get('sort', None)
            role = self.request.query_params.get('role', None)

            if query is not None:
                search_query = Q(name__icontains=query) | Q(branch__name__icontains=query) | Q(
                    mobile_number__icontains=query)
                queryset = queryset.filter(search_query)

            if role is not None:
                queryset = queryset.filter(role__name='MarketingExecutive')

            if sort == '-added_on':
                queryset = queryset.order_by('-added_on')
            if sort == 'added_on':
                queryset = queryset.order_by('added_on')
            return queryset

    def perform_update(self, serializer):
        client = self.request.client
        serializer.context['client'] = client
        super().perform_update(serializer)

        try:
            base_cache_key = f'lab_staff_{client}_'
            for key in cache.iter_keys(f'{base_cache_key}*'):  # Use a wildcard to find matching keys
                cache.delete(key)
        except Exception as e:
            print(f"Error occurred while invalidating cache: {str(e)}")

    def perform_destroy(self, instance):
        client = self.request.client
        try:
            base_cache_key = f'lab_staff_{client}_'
            for key in cache.iter_keys(f'{base_cache_key}*'):  # Use a wildcard to find matching keys
                cache.delete(key)
            super().perform_destroy(instance)
        except Exception as e:
            print(f"Error occurred while invalidating cache: {str(e)}")


class LabStaffAccessViewSet(viewsets.ModelViewSet):
    serializer_class = LabStaffAccessSerializer

    def get_queryset(self):
        mobile_number = self.request.query_params.get('mobile_number', None)
        if mobile_number is not None:
            queryset = LabStaff.objects.filter(mobile_number=mobile_number)
            return queryset
        else:
            return LabStaff.objects.none()

    def retrieve(self, request, *args, **kwargs):
        return Response({'Error': 'Method not Allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)



class LabStaffPageGuardView(generics.ListAPIView):
    def get(self, request, *args, **kwargs):
        lab_staff_id=self.request.query_params.get('lab_staff')
        menu_id = self.request.query_params.get('menu')

        if lab_staff_id and menu_id:
            try:
                lab_staff = LabStaff.objects.get(pk=lab_staff_id)
                lab_menu_access = LabMenuAccess.objects.filter(lab_staff=lab_staff).first()
                lab_staff_details = {"is_superadmin":lab_staff.is_superadmin}

                if lab_staff.is_active and lab_staff.is_login_access:
                    can_access = lab_menu_access.lab_menu.filter(id=menu_id).exists()
                    if can_access:
                        lab_staff_details['can_access']=True
                        lab_staff_details['route'] = ""
                    else:
                        route = lab_menu_access.lab_menu.first()
                        lab_staff_details['can_access']=False
                        lab_staff_details['route'] = route.link if route else "/noaccess"

                else:
                    lab_staff_details['can_access'] = False
                    lab_staff_details['route'] = "/noaccess"

                return Response(lab_staff_details)
            except Exception as error:
                print(error)
                return Response({"Error":f"{error}"}, status=status.HTTP_400_BAD_REQUEST)

        else:
            return Response({"Error":"Lab Staff or Menu details are missing!"}, status=status.HTTP_400_BAD_REQUEST)



class LabStaffAttendanceDetailsViewSet(viewsets.ModelViewSet):
    queryset = LabStaffAttendanceDetails.objects.all()
    serializer_class = LabStaffAttendanceDetailsSerializer

    def perform_create(self, serializer):
        instance = serializer.save()
        self.calculate_attendance_status(instance)
        instance.save()

    def perform_update(self, serializer):
        instance = serializer.save()
        self.calculate_attendance_status(instance)
        instance.save()

    def calculate_attendance_status(self, instance):
        if not instance.shift_start_time or not instance.shift_end_time:
            job_details = LabStaffJobDetails.objects.filter(labstaff=instance.lab_staff).first()
            if job_details:
                instance.shift_start_time = job_details.shift_start_time
                instance.shift_end_time = job_details.shift_end_time

        if instance.shift_start_time and instance.shift_end_time:
            if instance.check_in_time and instance.check_out_time:
                instance.total_worked_hours = instance.check_out_time - instance.check_in_time

                shift_duration = timedelta(
                    hours=instance.shift_end_time.hour, minutes=instance.shift_end_time.minute
                ) - timedelta(
                    hours=instance.shift_start_time.hour, minutes=instance.shift_start_time.minute
                )

                half_day_duration = shift_duration // 2
                total_hours = instance.total_worked_hours.total_seconds() / 3600

                if total_hours >= (shift_duration.total_seconds() / 3600) * 0.75:
                    attendance_status = LabStaffAttendanceStatus.objects.get(name="Present")
                elif total_hours >= half_day_duration.total_seconds() / 3600:
                    attendance_status = LabStaffAttendanceStatus.objects.get(name="Half-Day")
                else:
                    attendance_status = LabStaffAttendanceStatus.objects.get(name="Absent")
                instance.attendance_status = attendance_status
            elif not instance.check_in_time:
                instance.attendance_status = LabStaffAttendanceStatus.objects.get(name="Absent")
        else:
            pass
        if instance.check_in_lat and instance.check_in_lon:
            instance.check_in_address = self.get_address(instance.check_in_lat, instance.check_in_lon)
        if instance.check_out_lat and instance.check_out_lon:
            instance.check_out_address = self.get_address(instance.check_out_lat, instance.check_out_lon)

    def get_address(self, latitude, longitude):
        try:
            geolocator = Nominatim(user_agent="HealthOPro")
            location = geolocator.reverse(f"{latitude}, {longitude}")
            if location and location.raw:
                address = location.raw.get('address', {})

                area = address.get('road') or address.get('neighbourhood') or address.get('suburb')
                city = address.get('town') or address.get('city') or address.get('village')
                pincode = address.get('postcode')
                return f"{area}, {city}, {pincode}" if area or city or pincode else None
        except GeocoderTimedOut:
            print("Geocoding service timed out.")
        return None


class LabDiscountTypeViewSet(viewsets.ModelViewSet):
    queryset = LabDiscountType.objects.all()
    serializer_class = LabDiscountTypeSerializer


class LabGlobalTestMethodologyViewSet(viewsets.ModelViewSet):
    queryset = Methodology.objects.all()
    serializer_class = LabGlobalTestMethodologySerializer


class LabStaffRoleViewSet(viewsets.ModelViewSet):
    queryset = LabStaffRole.objects.all()
    serializer_class = LabStaffRoleSerializer

    def destroy(self, request, *args, **kwargs):
        return Response({'Error': 'Method not Allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


class LabDoctorRoleViewSet(viewsets.ModelViewSet):
    queryset = LabDoctorRole.objects.all()
    serializer_class = LabDoctorRoleSerializer


class LabMenuAccessViewSet(viewsets.ModelViewSet):
    serializer_class = LabMenuAccessSerializer

    def get_queryset(self):
        queryset = LabMenuAccess.objects.all()
        lab_staff = self.request.query_params.get('lab_staff', None)
        if lab_staff is not None:
            queryset = LabMenuAccess.objects.filter(lab_staff=lab_staff)
        return queryset

    def destroy(self, request, *args, **kwargs):
        return Response({'Error': 'Method not Allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


class LabStaffRolePermissionsViewset(viewsets.ModelViewSet):
    queryset = LabStaffRolePermissions.objects.all()
    serializer_class = LabStaffRolePermissionsSerializer

    def get_queryset(self):
        lab_staff_role = self.request.query_params.get('lab_staff_role', None)
        if lab_staff_role is not None:
            queryset = LabStaffRolePermissions.objects.filter(lab_staff_role=lab_staff_role)
            return queryset
        else:
            return LabStaffRolePermissions.objects.none()

    def destroy(self, request, *args, **kwargs):
        return Response({'Error': 'Method not Allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


class LabStaffLoginActionViewSet(viewsets.ModelViewSet):
    serializer_class = LabStaffLoginActionSerializer

    def get_queryset(self):
        return LabStaffLoginAccess.objects.none()

    def create(self, request=None,client=None,lab_staff=None, can_login=None, *args, **kwargs):
        if request:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer_data = serializer.validated_data
            lab_staff = serializer_data.get('lab_staff')
            client = serializer_data.get('client')
            can_login = serializer_data.get('can_login', None)

        # try:
        #     lab_staff = LabStaff.objects.get(pk=lab_staff.id)
        # except Exception as error:
        #     return Response({"Error": f"{error}"})

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
            print(error)
            otp_code = ''.join(random.choices(string.digits, k=4))
            OTP.objects.create(pro_user_id=user, otp_code=otp_code)

        if lab_staff.is_active:
            user_tenant, created = UserTenant.objects.get_or_create(
                user=user,
                client=client
            )
            if can_login is not None:
                if can_login:
                    user_tenant.is_active = True
                    user_tenant.save()
                    lab_staff.is_login_access = True
                    lab_staff.save()
                    return Response({"Status": "UserTenant Is Now Active!",
                                     "user_tenant_id": user_tenant.id,
                                     "user_tenant.isactive": user_tenant.is_active})
                else:
                    user_tenant.is_active = False
                    user_tenant.save()
                    lab_staff.is_login_access = False
                    lab_staff.save()

                    blacklist_user_tokens(user)
                    return Response({"Status": "UserTenant Is Now Deactived!",
                                     "user_tenant_id": user_tenant.id,
                                     "user_tenant.isactive": user_tenant.is_active})

            else:
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
        else:
            return Response({"Error": "LabStaff Is Not Active!"})


class LabReportsTemplatesViewSet(viewsets.ModelViewSet):
    queryset = LabReportsTemplates.objects.all()
    serializer_class = LabReportsTemplatesSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        report_type = instance.report_type.id

        if report_type == 1:
            try:
                parameters = LabFixedParametersReportTemplate.objects.filter(LabReportsTemplate=instance,
                                                                             is_active=True).order_by(
                    'ordering')
                serializer = LabFixedParametersReportTemplateSerializer(parameters, many=True)
                return Response(serializer.data)
            except LabFixedParametersReportTemplate.DoesNotExist:
                return Response({"message": "No parameters found for this lab report template and report type"},
                                status=status.HTTP_404_NOT_FOUND)
        elif report_type == 2:
            try:
                report_details = LabWordReportTemplate.objects.get(LabReportsTemplate=instance)
                report_details.save()
                report_details.header = return_word_report_header()
                serializer = LabWordReportTemplateSerializer(report_details)
                return Response(serializer.data)
            except LabWordReportTemplate.DoesNotExist:
                return Response({"message": "Report details not found for this lab report template and report type"},
                                status=status.HTTP_404_NOT_FOUND)

        return Response({"message": "Report type not supported"}, status=status.HTTP_404_NOT_FOUND)

    def list(self, request, *args, **kwargs):
        queryset = self.queryset
        global_test_id = request.query_params.get('global_test_id')
        departments = request.query_params.get('departments')
        type = request.query_params.get('type')

        if type:
            queryset = queryset.filter(report_type=type)

        if global_test_id:
            queryset = queryset.filter(LabGlobalTestID=global_test_id)
        if departments:
            department_ids = [int(dep_id) for dep_id in departments.split(',')]
            queryset = queryset.filter(LabGlobalTestID__department__id__in=department_ids)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class LabWordReportTemplateViewSet(viewsets.ModelViewSet):
    queryset = LabWordReportTemplate.objects.all()
    serializer_class = LabWordReportTemplateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        pages = validated_data.pop('pages',[])

        template = LabWordReportTemplate.objects.create(**validated_data)

        # if pages:
        #     for page_data in pages:
        #         page = LabWordReportTemplatePageWiseContent.objects.create(page_content=page_data['page_content'])
        #         template.pages.add(page)

        serializer = LabWordReportTemplateSerializer(template)

        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        pages = validated_data.pop('pages', [])

        existing_report_content = instance.report
        serializer.save()
        updated_report_content = instance.report

        # if pages:
        #     for page in instance.pages.all():
        #         page.delete()
        #     for page_data in pages:
        #         page = LabWordReportTemplatePageWiseContent.objects.create(page_content=page_data['page_content'])
        #         instance.pages.add(page)

        if existing_report_content != updated_report_content:
            try:
                activity_log = ActivityLogs.objects.create(
                    user=request.user,
                    lab_staff=instance.last_updated_by,
                    client=request.client,
                    patient=None,
                    operation="PUT",
                    url="lab/lab_word_report_templates",
                    model="LabWordReportTemplate",
                    activity=f"Word Template Report updated for {instance.LabReportsTemplate.name} by {instance.last_updated_by.name} on {instance.last_updated_on.strftime('%d-%m-%y %I:%M %p')}",
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
                    f"Error Creating Activitylog for word_report {instance.LabReportsTemplate.name} for on {instance.added_on.strftime('%d-%m-%y %I:%M %p')}: {error}",
                    exc_info=True)

        serializer = LabWordReportTemplateSerializer(instance)
        return Response(serializer.data)


class LabFixedParametersReportTemplateViewSet(viewsets.ModelViewSet):
    queryset = LabFixedParametersReportTemplate.objects.all()
    serializer_class = LabFixedParametersReportTemplateSerializer


class LabFixedReportNormalReferralRangesViewSet(viewsets.ModelViewSet):
    queryset = LabFixedReportNormalReferralRanges.objects.all()
    serializer_class = LabFixedReportNormalReferralRangesSerializer


class LabBranchViewSet(viewsets.ModelViewSet):
    queryset = LabBranch.objects.all()
    serializer_class = LabBranchSerializer


class LabShiftViewSet(viewsets.ModelViewSet):
    queryset = LabShift.objects.all()
    serializer_class = LabShiftSerializer


class LabWorkingDaysViewSet(viewsets.ModelViewSet):
    queryset = LabWorkingDays.objects.all()
    serializer_class = LabWorkingDaysSerializer


class LabBloodGroupViewSet(viewsets.ModelViewSet):
    queryset = LabBloodGroup.objects.all()
    serializer_class = LabBloodGroupSerializer


class LabMaritalStatusViewSet(viewsets.ModelViewSet):
    queryset = LabMaritalStatus.objects.all()
    serializer_class = LabMaritalStatusSerializer


class LabGlobalPackagesViewSet(viewsets.ModelViewSet):
    serializer_class = LabGlobalPackagesSerializer

    def get_queryset(self):
        queryset = LabGlobalPackages.objects.all()
        query = self.request.query_params.get('q', None)
        sort = self.request.query_params.get('sort', None)

        if query is not None:
            search_query = (Q(name__icontains=query) | Q(total_amount__icontains=query) | Q(
                total_discount__icontains=query) | Q(offer_price__icontains=query))
            queryset = queryset.filter(search_query)

        if sort == '-added_on':
            queryset = queryset.order_by('-added_on')
        if sort == 'added_on':
            queryset = queryset.order_by('added_on')

        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        lab_tests = request.data.get('lab_tests')
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        package = LabGlobalPackages.objects.create(**validated_data)

        if lab_tests:
            for test in lab_tests:
                package.lab_tests.add(test)
        serializer = LabGlobalPackagesSerializer(package)

        return Response(serializer.data)

    def update(self, request, pk=None, *args, **kwargs):
        instance = self.get_object()
        instance.id = pk  # Update the ID in case it's passed in the URL
        serializer = self.get_serializer(instance, data=request.data)

        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Update lab tests if provided
        lab_tests = request.data.get('lab_tests')
        if lab_tests:
            instance.lab_tests.clear()
            instance.save()
            for test in lab_tests:
                instance.lab_tests.add(test)

        serializer = LabGlobalPackagesSerializer(instance)
        return Response(serializer.data)


class LabGlobalPackagesListView(generics.ListAPIView):
    serializer_class = LabGlobalPackagesGetSerializer

    def get_queryset(self):
        queryset = LabGlobalPackages.objects.all()
        query = self.request.query_params.get('q', None)
        sort = self.request.query_params.get('sort', None)

        if query is not None:
            search_query = (Q(name__icontains=query) | Q(total_amount__icontains=query) | Q(
                total_discount__icontains=query) | Q(offer_price__icontains=query))
            queryset = queryset.filter(search_query)

        if sort == '-added_on':
            queryset = queryset.order_by('-added_on')
        if sort == 'added_on':
            queryset = queryset.order_by('added_on')

        return queryset


class DoctorAcessViewset(viewsets.ModelViewSet):
    serializer_class = DoctorAccessSerializer

    def get_queryset(self):
        queryset = DoctorAccess.objects.all()
        mobile_number = self.request.query_params.get('mobile_number')

        if mobile_number is not None:
            queryset = DoctorAccess.objects.filter(doctor__phone_number__icontains=mobile_number)

        return queryset


class SearchForHealthcareProfessional(generics.ListAPIView):
    serializer_class = UserSerializer

    def get_queryset(self):
        queryset = HealthOProUser.objects.filter(user_type=2)
        name = self.request.query_params.get('name', None)
        mobile_number = self.request.query_params.get('mobile_number', None)

        if mobile_number is not None:
            queryset = queryset.filter(username__icontains=mobile_number)

        if name is not None:
            queryset = queryset.filter(Q(full_name__icontains=name))

        if not (mobile_number or name):
            queryset = HealthOProUser.objects.none()

        return queryset


class UserCollectionsAPIView(generics.ListAPIView):
    def get_serializer_class(self):
        pass  # Implement this if you have a specific serializer class to use

    def list(self, request, *args, **kwargs):
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if start_date or end_date:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            if not end_date:
                end_date = datetime.combine(start_date, datetime.max.time())
            else:
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            receipts = LabPatientReceipts.objects.filter(
                added_on__date__gte=start_date,
                added_on__date__lte=end_date)
            refunds = LabPatientRefund.objects.filter(
                added_on__date__gte=start_date,
                added_on__date__lte=end_date)

            expenses = LabExpenses.objects.filter(
                added_on__date__gte=start_date,
                added_on__date__lte=end_date)

        else:
            receipts = LabPatientReceipts.objects.all()
            refunds = LabPatientRefund.objects.all()
            expenses = LabExpenses.objects.all()

        # Prefetch related data to reduce the number of queries
        receipts = receipts.select_related('created_by').prefetch_related('payments__pay_mode')
        refunds = refunds.select_related('created_by').prefetch_related('refund_mode')

        staff_queryset = LabStaff.objects.filter(
            Q(labpatientreceipts__in=receipts) | Q(labpatientrefund__in=refunds)| Q(labexpenses__in=expenses)
        ).distinct()

        staff_data = []
        for staff in staff_queryset:
            receipts_for_staff = receipts.filter(created_by=staff)
            refunds_for_staff = refunds.filter(created_by=staff)
            expenses_for_staff = expenses.filter(authorized_by=staff)

            total_cash_collection = receipts_for_staff.aggregate(
                sum_cash=Coalesce(Sum('payments__paid_amount', filter=Q(payments__pay_mode__name='Cash')),
                                  Value(0, output_field=DecimalField()))
            )['sum_cash'] or 0

            total_online_collection = receipts_for_staff.aggregate(
                sum_online=Coalesce(Sum('payments__paid_amount', filter=~Q(payments__pay_mode__name='Cash')),
                                    Value(0, output_field=DecimalField()))
            )['sum_online'] or 0

            total_cash_refund = refunds_for_staff.aggregate(
                sum_cash_refund=Coalesce(Sum('refund', filter=Q(refund_mode__name='Cash')),
                                         Value(0, output_field=DecimalField()))
            )['sum_cash_refund'] or 0

            total_online_refund = refunds_for_staff.aggregate(
                sum_online_refund=Coalesce(Sum('refund', filter=~Q(refund_mode__name='Cash')),
                                           Value(0, output_field=DecimalField()))
            )['sum_online_refund'] or 0

            total_cash_expenses = expenses_for_staff.aggregate(
                sum_cash_expenses=Coalesce(Sum('amount', filter=Q(pay_mode__name='Cash')),
                                         Value(0, output_field=DecimalField()))
            )['sum_cash_expenses'] or 0

            total_online_expenses = expenses_for_staff.aggregate(
                sum_online_expenses=Coalesce(Sum('amount', filter=~Q(pay_mode__name='Cash')),
                                           Value(0, output_field=DecimalField()))
            )['sum_online_expenses'] or 0



            net_cash_collection = total_cash_collection - total_cash_refund - total_cash_expenses
            net_online_collection = total_online_collection - total_online_refund - total_online_expenses

            staff_data.append({
                'staff': LabStaffDataSerializer(staff).data,
                'total_cash_collection': total_cash_collection,
                'total_online_collection': total_online_collection,
                'total_cash_refund': total_cash_refund,
                'total_online_refund': total_online_refund,
                'total_cash_expenses': total_cash_expenses,
                'total_online_expenses': total_online_expenses,
                'net_cash_collection': net_cash_collection,
                'net_online_collection': net_online_collection,
            })

        # Paginate the results
        page = self.paginate_queryset(staff_data)
        if page is not None:
            return self.get_paginated_response(page)

        return Response(staff_data)


class DefaultTestParametersViewSet(viewsets.ModelViewSet):
    serializer_class = DefaultTestParametersSerializer

    def get_queryset(self):
        queryset = DefaultTestParameters.objects.all()
        parameter = self.request.query_params.get('parameter')
        test_id = self.request.query_params.get('test')

        if test_id is not None:
            queryset = queryset.filter(LabGlobalTestId=test_id)

        if parameter is not None:
            queryset = queryset.filter(parameter__icontains=parameter)
        return queryset


class LabStaffAttendanceDetailsListView(generics.ListAPIView):
    queryset = LabStaffAttendanceDetails.objects.all()
    serializer_class = LabStaffAttendanceGetDetailsSerializer

    def get_queryset(self):
        lab_staff_id = self.request.query_params.get('lab_staff', None)
        date = self.request.query_params.get('date', None)
        query = self.request.query_params.get('q', None)
        queryset = self.queryset

        if query is not None:
            queryset = queryset.filter(lab_staff__name__icontains=query)

        if lab_staff_id:
            queryset = queryset.filter(lab_staff_id=lab_staff_id)
        if date:
            queryset = queryset.filter(date=date)

        return queryset


class LabStaffPayRollViewSet(viewsets.ModelViewSet):
    queryset = LabStaffPayRoll.objects.all()
    serializer_class = LabStaffPayRollSerializer

    def perform_create(self, serializer):
        instance = serializer.save()
        pay_roll = self.calculate_deductions_and_overtime(instance.lab_staff)
        instance.commission = pay_roll['commissions'] if pay_roll['commissions'] else None
        instance.incentive = pay_roll['incentives'] if pay_roll['incentives'] else None
        instance.deductions = pay_roll['deductions'] if pay_roll['deductions'] else None
        instance.overtime_payment = pay_roll['overtime_payment'] if pay_roll['overtime_payment'] else None
        instance.save()

    def perform_update(self, serializer):
        instance = serializer.save()
        pay_roll = self.calculate_deductions_and_overtime(instance.lab_staff)
        instance.commission = pay_roll['commissions'] if pay_roll['commissions'] else None
        instance.incentive = pay_roll['incentives'] if pay_roll['incentives'] else None
        instance.deductions = pay_roll['deductions'] if pay_roll['deductions'] else None
        instance.overtime_payment = pay_roll['overtime_payment'] if pay_roll['overtime_payment'] else None
        instance.save()

    def calculate_deductions_and_overtime(self, lab_staff):
        attendances = LabStaffAttendanceDetails.objects.filter(lab_staff=lab_staff)
        target = MarketingExecutiveTargets.objects.filter(labstaff=lab_staff).first()
        if target:
            target_achieved = calculate_target_achieved_by_marketing_executive(target)['total_price'] or 0
            target_revenue = target.target_revenue or 0
        else:
            target_achieved = 0
            target_revenue = 0

        total_deficit_minutes = 0
        total_extra_minutes = 0

        for attendance in attendances:
            extra_deficit = calculate_extra_and_deficit_hours(attendance)

            # Handle deficit_hours
            if extra_deficit['deficit_hours']:
                deficit_str = extra_deficit['deficit_hours'].replace(' mins', '').replace(' minutes', '')
                total_deficit_minutes += int(deficit_str) if deficit_str.isdigit() else 0

            # Handle extra_hours
            if extra_deficit['extra_hours']:
                extra_str = extra_deficit['extra_hours'].replace(' mins', '').replace(' minutes', '')
                total_extra_minutes += int(extra_str) if extra_str.isdigit() else 0

        total_deficit_hours = int(total_deficit_minutes) // 60
        total_extra_hours = int(total_extra_minutes) // 60
        job_details = LabStaffJobDetails.objects.filter(labstaff=lab_staff).first()

        if job_details:
            incentive_rate = job_details.incentive_rate or 0
            commission_rate = job_details.commission_rate or 0
            incentives = (target_achieved - target_revenue) * (incentive_rate // 100)
            commissions = target_achieved * (commission_rate // 100)
            deduction_rate = job_details.salary_deduction or 0
            total_deductions = total_deficit_hours * deduction_rate
            extra_hours_pay = job_details.extra_hours_pay or 0
            total_overtime_payment = total_extra_hours * extra_hours_pay
            return {
                'deductions': round(total_deductions, 2),
                'overtime_payment': round(total_overtime_payment, 2),
                'incentives': incentives,
                'commissions': commissions
            }

        else:
            return {'deductions': 0, 'overtime_payment': 0, 'incentives': 0, 'commissions': 0}


class LabStaffJobDetailsViewSet(viewsets.ModelViewSet):
    serializer_class = LabStaffJobDetailsSerializer

    def get_queryset(self):
        queryset = LabStaffJobDetails.objects.all()
        staff = self.request.query_params.get('lab_staff')
        if staff is not None:
            queryset = queryset.filter(labstaff=staff)
        return queryset


class LabStaffLeaveRequestViewSet(viewsets.ModelViewSet):
    queryset = LabStaffLeaveRequest.objects.all()
    serializer_class = LabStaffLeaveRequestSerializer

    def perform_update(self, serializer):
        instance = serializer.save()
        if instance and instance.status.id == 2:
            leave_status = LabStaffAttendanceStatus.objects.get(id=3)
            current_date = instance.from_date
            while current_date <= instance.to_date:
                attendance = LabStaffAttendanceDetails.objects.create(
                    lab_staff=instance.lab_staff,
                    date=current_date,
                    attendance_status=leave_status
                )
                attendance.save()
                current_date += timedelta(days=1)
        instance.save()

    def get_queryset(self):
        queryset = LabStaffLeaveRequest.objects.all()
        lab_staff = self.request.query_params.get('lab_staff')
        status = self.request.query_params.get('status')
        is_active = self.request.query_params.get('is_active')

        if is_active is not None and is_active.lower():
            queryset = queryset.filter(is_active=is_active.capitalize())

        if lab_staff is not None:
            queryset = queryset.filter(lab_staff=lab_staff)
        if status is not None:
            queryset = queryset.filter(status=status)
        return queryset


class LeavePolicyViewSet(viewsets.ModelViewSet):
    queryset = LeavePolicy.objects.all()
    serializer_class = LeavePolicySerializer

    def get_queryset(self):
        queryset = LeavePolicy.objects.all()
        if queryset:
            pass
        else:
            LeavePolicy.objects.create(no_of_paid_leaves=0)

        return queryset


class LabStaffPayRollAPIView(generics.ListAPIView):
    queryset = LabStaff.objects.all()
    serializer_class = LabStaffWithPayRollSerializer

    def get_queryset(self):
        queryset = LabStaff.objects.all()
        role = self.request.query_params.get('role')
        query = self.request.query_params.get('q')
        if role is not None:
            queryset = queryset.filter(role__name=role)

        if query is not None:
            queryset = queryset.filter(name__icontains=query)
        return queryset


class LeaveStatisticsAPIView(APIView):
    def get(self, request):
        lab_staff_id = request.query_params.get('lab_staff')
        date_range_after = request.query_params.get('date_range_after')
        date_range_before = request.query_params.get('date_range_before')
        if not lab_staff_id or not date_range_after or not date_range_before:
            return Response({'error': 'Missing required parameters.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from_date = datetime.strptime(date_range_after, '%Y-%m-%d').date()
            to_date = datetime.strptime(date_range_before, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        leave_policy = LeavePolicy.objects.first()
        if not leave_policy:
            return Response({'error': 'Leave policy not found.'}, status=status.HTTP_404_NOT_FOUND)

        total_paid_leaves = leave_policy.no_of_paid_leaves
        leaves = LabStaffLeaveRequest.objects.filter(
            lab_staff_id=lab_staff_id,
            is_cancel=False,
            status__id=2,
            from_date__gte=from_date,
            to_date__lte=to_date
        ).aggregate(total_days=Sum('no_of_days'))
        print(LabStaffLeaveRequest.objects.filter(
            lab_staff_id=lab_staff_id,
            is_cancel=False,
            status__id=2,
            from_date__gte=from_date,
            to_date__lte=to_date
        ).values())
        total_leaves_taken = leaves['total_days'] if leaves['total_days'] else 0

        balance_leaves = total_paid_leaves - total_leaves_taken

        data = {
            'total_paid_leaves': total_paid_leaves,
            'total_leaves_taken': total_leaves_taken,
            'balance_leaves': balance_leaves
        }

        return Response(data, status=status.HTTP_200_OK)



class LabStaffDefaultBranchViewSet(viewsets.ModelViewSet):
    queryset = LabStaffDefaultBranch.objects.all()
    serializer_class = LabStaffDefaultBranchSerializer

    def get_queryset(self):
        queryset = LabStaffDefaultBranch.objects.all()
        lab_staff=self.request.query_params.get('lab_staff')

        if lab_staff:
            obj=queryset.filter(lab_staff__id=lab_staff)

            if obj:
                pass
            else:
                lab_staff = LabStaff.objects.get(pk=lab_staff)
                obj=LabStaffDefaultBranch.objects.create(lab_staff=lab_staff)

        return queryset




    def perform_update(self, serializer):
        client = self.request.client
        super().perform_update(serializer)
        staff_id = serializer.instance.lab_staff.id
        try:
            cache_key = f'lab_staff_{client}_{staff_id}'
            if cache_key:
                cache.delete(cache_key)
        except Exception as e:
            print(f"Error occurred while invalidating cache: {str(e)}")

    def perform_destroy(self, instance):
        client = self.request.client
        staff_id = instance.id
        try:
            cache_key = f'lab_staff_{client}_{staff_id}'
            if cache_key:
                cache.delete(cache_key)
            super().perform_destroy(instance)
        except Exception as e:
            print(f"Error occurred while deleting instancce and invalidating cache: {str(e)}")