from bisect import insort
from datetime import datetime

from rest_framework import serializers

from healtho_pro_user.models.business_models import BusinessAddresses
from healtho_pro_user.models.users_models import Client
from pro_hospital.models.universal_models import GlobalRoom
from pro_hospital.serializers.universal_serializers import DoctorConsultationDetailsSerializer, GlobalRoomSerializer, \
    GlobalServicesSerializer
from pro_laboratory.models.doctors_models import DefaultsForDepartments
from pro_laboratory.models.global_models import LabGlobalTests, LabStaff, LabDiscountType, LabReportsTemplates, \
    LabWordReportTemplate, LabFixedParametersReportTemplate, LabWorkingDays, LabStaffPersonalDetails, \
    LabStaffIdentificationDetails, LabMenuAccess, LabStaffRole, LabStaffRolePermissions, LabBranch, \
    LabShift, LabBloodGroup, LabMaritalStatus, LabDoctorRole, Methodology, LabDepartments, BodyParts, LabGlobalPackages, \
    DoctorAccess, DefaultTestParameters, LabFixedReportNormalReferralRanges, \
    LabStaffAttendanceDetails, LabStaffJobDetails, LabStaffPayRoll, LabStaffLeaveRequest, LeavePolicy, \
    LabStaffDefaultBranch
from django.contrib.auth import get_user_model

from pro_laboratory.models.marketing_models import LabStaffVehicleDetails, MarketingExecutiveLocationTracker
from pro_laboratory.serializers.doctors_serializers import DefaultsForDepartmentsSerializer
from pro_laboratory.serializers.marketing_serializers import LabStaffVehicleDetailsSerializer, \
    calculate_total_worked_hours, MarketingExecutiveLocationTrackerSerializer
from pro_laboratory.serializers.sourcing_lab_serializers import SourcingLabRegistrationSerializer

User = get_user_model()


class LabDepartmentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabDepartments
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['department_flow_type'] = instance.department_flow_type.name if instance.department_flow_type else None
        defaults = DefaultsForDepartments.objects.filter(department=instance).first()
        representation['defaults'] = DefaultsForDepartmentsSerializer(defaults).data if defaults else None
        return representation


class BodyPartsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BodyParts
        fields = '__all__'


class LabGlobalTestsSerializer(serializers.ModelSerializer):

    class Meta:
        model = LabGlobalTests
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['department'] = instance.department.name if instance.department else None
        if instance.sourcing_lab:
            request = self.context.get('request')
            representation['sourcing_lab'] = SourcingLabRegistrationSerializer(instance.sourcing_lab, context={"request": request}).data
        return representation


class LabWorkingDaysSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabWorkingDays
        fields = '__all__'


class LabStaffPersonalDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabStaffPersonalDetails
        fields = '__all__'


class LabStaffIdentificationDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabStaffIdentificationDetails
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        salary_payment_mode = instance.salary_payment_mode
        if 'salary_payment_mode' in representation:
            representation['salary_payment_mode'] = {
                'id': representation['salary_payment_mode'],
                'name': instance.salary_payment_mode.name if instance.salary_payment_mode else None
            }
        return representation


class LabStaffJobDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabStaffJobDetails
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if 'payment_type' in representation:
            representation['payment_type'] = {
                'id': representation['payment_type'],
                'name': instance.payment_type.name if instance.payment_type else None
            }
        return representation


class LabStaffSerializer(serializers.ModelSerializer):
    lab_working_days = serializers.PrimaryKeyRelatedField(queryset=LabWorkingDays.objects.all(), many=True,
                                                          required=False)
    lab_staff_personal_details = LabStaffPersonalDetailsSerializer(required=False, allow_null=True)
    lab_staff_identification_details = LabStaffIdentificationDetailsSerializer(required=False, allow_null=True)
    lab_staff_vehicle_details = LabStaffVehicleDetailsSerializer(required=False, allow_null=True)
    lab_staff_job_details = LabStaffJobDetailsSerializer(required=False, allow_null=True)
    branches_data =  serializers.PrimaryKeyRelatedField(queryset=BusinessAddresses.objects.all(), many=True,
                                                          required=False)

    class Meta:
        model = LabStaff
        fields = '__all__'

    def create(self, validated_data):
        lab_working_days_data = validated_data.pop('lab_working_days', [])
        lab_staff_personal_details_data = validated_data.pop('lab_staff_personal_details', None)
        lab_staff_identification_details_data = validated_data.pop('lab_staff_identification_details', None)
        lab_staff_vehicle_details_data = validated_data.pop('lab_staff_vehicle_details', None)
        lab_staff_job_details_data = validated_data.pop('lab_staff_job_details', None)
        branches_data = validated_data.pop('branches', [])

        lab_staff = LabStaff.objects.create(**validated_data)

        for day in lab_working_days_data:
            lab_staff.lab_working_days.add(day)

        if branches_data:
            lab_staff.branches.set(branches_data)
            default_branch = LabStaffDefaultBranch.objects.create(lab_staff=lab_staff)
            default_branch.default_branch.set(branches_data)

        if lab_staff_personal_details_data:
            LabStaffPersonalDetails.objects.create(labstaff=lab_staff, **lab_staff_personal_details_data)

        if lab_staff_identification_details_data:
            LabStaffIdentificationDetails.objects.create(labstaff=lab_staff, **lab_staff_identification_details_data)

        if lab_staff_vehicle_details_data:
            LabStaffVehicleDetails.objects.create(labstaff=lab_staff, **lab_staff_vehicle_details_data)

        if lab_staff_job_details_data:
            LabStaffJobDetails.objects.create(labstaff=lab_staff, **lab_staff_job_details_data)

        return lab_staff

    def update(self, instance, validated_data):
        lab_working_days_data = validated_data.pop('lab_working_days', None)
        lab_staff_personal_details_data = validated_data.pop('lab_staff_personal_details', None)
        lab_staff_identification_details_data = validated_data.pop('lab_staff_identification_details', None)
        lab_staff_vehicle_details_data = validated_data.pop('lab_staff_vehicle_details', None)
        lab_staff_job_details_data = validated_data.pop('lab_staff_job_details', None)
        branches_data = validated_data.pop('branches', [])

        old_mobile_number = instance.mobile_number
        instance = super().update(instance, validated_data)
        new_mobile_number = instance.mobile_number

        # Update many-to-many relationships
        if lab_working_days_data is not None:
            instance.lab_working_days.set(lab_working_days_data)

        # Update many-to-many relationships
        if branches_data:
            instance.branches.set(branches_data)
            default_branch, created = LabStaffDefaultBranch.objects.get_or_create(lab_staff=instance)
            default_branch.default_branch.set(branches_data)

        # Update lab_staff_personal_details if it exists
        if lab_staff_personal_details_data is not None:
            personal_details_instance = instance.labstaffpersonaldetails_set.first()
            if personal_details_instance is not None:
                for attr, value in lab_staff_personal_details_data.items():
                    setattr(personal_details_instance, attr, value)
                personal_details_instance.save()
            else:
                LabStaffPersonalDetails.objects.create(labstaff=instance, **lab_staff_personal_details_data)

        if lab_staff_identification_details_data is not None:
            identification_instance = instance.labstaffidentificationdetails_set.first()
            if identification_instance:
                for attr, value in lab_staff_identification_details_data.items():
                    setattr(identification_instance, attr, value)
                identification_instance.save()
            else:
                LabStaffIdentificationDetails.objects.create(labstaff=instance, **lab_staff_identification_details_data)

        if lab_staff_vehicle_details_data is not None:
            vehicle_instance = instance.labstaffvehicledetails_set.first()
            if vehicle_instance:
                for attr, value in lab_staff_vehicle_details_data.items():
                    setattr(vehicle_instance, attr, value)
                vehicle_instance.save()
            else:
                LabStaffVehicleDetails.objects.create(labstaff=instance, **lab_staff_vehicle_details_data)

        if lab_staff_job_details_data is not None:
            job_details_instance = instance.labstaffjobdetails_set.first()
            if job_details_instance:
                for attr, value in lab_staff_job_details_data.items():
                    setattr(job_details_instance, attr, value)
                job_details_instance.save()
            else:
                LabStaffJobDetails.objects.create(labstaff=instance, **lab_staff_job_details_data)

        if old_mobile_number != new_mobile_number:
            # Call LabStaffLoginActionViewSet to give login access
            from pro_laboratory.views.global_views import LabStaffLoginActionViewSet
            lab_staff_login_access_api = LabStaffLoginActionViewSet()
            staff_login_access = lab_staff_login_access_api.create(
                client=self.context.get('client'),
                lab_staff=instance
            )

        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        if 'role' in representation:
            representation['role'] = {
                'id': representation['role'],
                'name': instance.role.name if instance.role else None
            }
        if 'department' in representation:
            representation['department'] = {
                'id': representation['department'],
                'name': instance.department.name if instance.department else None
            }
        if 'branch' in representation:
            representation['branch'] = {
                'id': representation['branch'],
                'name': instance.branch.name if instance.branch else None
            }
        if 'employement_type' in representation:
            representation['employement_type'] = {
                'id': representation['employement_type'],
                'name': instance.employement_type.name if instance.employement_type else None
            }

        lab_staff_personal_details = instance.labstaffpersonaldetails_set.first()
        lab_staff_identification_details = instance.labstaffidentificationdetails_set.first()
        lab_staff_vehicle_details = instance.labstaffvehicledetails_set.first()
        lab_staff_job_details = instance.labstaffjobdetails_set.first()

        if lab_staff_personal_details:
            representation['lab_staff_personal_details'] = LabStaffPersonalDetailsSerializer(
                lab_staff_personal_details).data

        if lab_staff_identification_details:
            representation['lab_staff_identification_details'] = LabStaffIdentificationDetailsSerializer(
                lab_staff_identification_details).data

        if lab_staff_vehicle_details:
            representation['lab_staff_vehicle_details'] = LabStaffVehicleDetailsSerializer(
                lab_staff_vehicle_details).data
        if lab_staff_job_details:
            representation['lab_staff_job_details'] = LabStaffJobDetailsSerializer(lab_staff_job_details).data

        marketing_tracker = getattr(instance, 'marketingexecutivelocationtracker', None)

        if marketing_tracker is None:
            if instance.role.name=='MarketingExecutive':
                marketing_tracker = MarketingExecutiveLocationTracker.objects.create(lab_staff=instance)

        last_seen = MarketingExecutiveLocationTrackerSerializer(marketing_tracker).data if marketing_tracker else ""

        representation['last_seen'] = last_seen

        from healtho_pro_user.serializers.business_serializers import BusinessAddressesSerializer
        representation['branches'] = BusinessAddressesSerializer(instance.branches, many=True).data if instance.branches else None

        default_branch = LabStaffDefaultBranch.objects.filter(lab_staff=instance).first()

        representation['default_branch'] = LabStaffDefaultBranchSerializer(default_branch).data if default_branch else None

        return representation


class LabStaffAttendanceDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabStaffAttendanceDetails
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        lab_staff = instance.lab_staff
        if lab_staff:
            representation['lab_staff'] = {"id": lab_staff.id, "name": lab_staff.name}
        return representation


class LabStaffAccessSerializer(serializers.ModelSerializer):
    business_name = serializers.SerializerMethodField()
    business_logo = serializers.SerializerMethodField()
    staff_role = serializers.SerializerMethodField()
    provider_type = serializers.SerializerMethodField()

    class Meta:
        model = LabStaff
        fields = ['business_name', 'business_logo', 'id', 'name', 'is_superadmin', 'staff_role', 'provider_type']

    def get_business_name(self, obj):
        return obj.b_id.organization_name

    def get_business_logo(self, obj):
        return obj.b_id.b_logo.url if obj.b_id.b_logo else None

    def get_staff_role(self, obj):
        if obj.role:
            return obj.role.name if obj.role.name else obj.role.pk

    def get_provider_type(self, obj):
        return obj.b_id.provider_type.name


class LabDiscountTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabDiscountType
        fields = '__all__'


class LabGlobalTestMethodologySerializer(serializers.ModelSerializer):
    class Meta:
        model = Methodology
        fields = '__all__'


class LabStaffRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabStaffRole
        fields = '__all__'


class LabDoctorRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabDoctorRole
        fields = '__all__'


class LabMenuAccessSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabMenuAccess
        fields = '__all__'


class LabStaffRolePermissionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabStaffRolePermissions
        fields = '__all__'


class LabReportsTemplatesSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabReportsTemplates
        fields = "__all__"


# class LabWordReportTemplatePageWiseContentSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = LabWordReportTemplatePageWiseContent
#         fields = "__all__"


class LabWordReportTemplateSerializer(serializers.ModelSerializer):
    # pages = LabWordReportTemplatePageWiseContentSerializer(many=True)
    header = serializers.CharField(read_only=True)

    class Meta:
        model = LabWordReportTemplate
        fields = "__all__"


class LabFixedReportNormalReferralRangesSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabFixedReportNormalReferralRanges
        fields = "__all__"


class LabFixedParametersReportTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabFixedParametersReportTemplate
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        normal_ranges = LabFixedReportNormalReferralRanges.objects.filter(parameter_id=instance)
        if normal_ranges:
            representation['normal_ranges'] = LabFixedReportNormalReferralRangesSerializer(normal_ranges,
                                                                                           many=True).data
        else:
            representation['normal_ranges'] = None

        return representation


class LabBranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabBranch
        fields = '__all__'


class LabShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabShift
        fields = '__all__'


class LabBloodGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabBloodGroup
        fields = '__all__'


class LabMaritalStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabMaritalStatus
        fields = '__all__'


class LabStaffLoginActionSerializer(serializers.Serializer):
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all(), required=True)
    lab_staff = serializers.PrimaryKeyRelatedField(queryset=LabStaff.objects.all(), required=True)


class LabGlobalPackagesSerializer(serializers.ModelSerializer):
    lab_tests = serializers.SerializerMethodField()


    class Meta:
        model = LabGlobalPackages
        fields = '__all__'

    def get_lab_tests(self, obj):
        request = self.context.get('request')
        lab_tests = obj.lab_tests.all()
        serializer = LabGlobalTestsSerializer(lab_tests, many=True, context={"request": request})
        return serializer.data

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        created_by_id = representation.get('created_by')
        if created_by_id is not None:
            created_by_name = instance.created_by.name
            representation['created_by_id'] = created_by_id
            representation['created_by'] = created_by_name
        return representation


class LabGlobalPackagesGetSerializer(serializers.ModelSerializer):
    total_tests_count = serializers.SerializerMethodField()

    class Meta:
        model = LabGlobalPackages
        fields = ['id', 'name', 'total_tests_count', 'description', 'offer_price', 'total_discount', 'is_active',
                  'created_by']

    def get_total_tests_count(self, obj):
        return obj.lab_tests.count()

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        created_by_id = representation.get('created_by')
        if created_by_id is not None:
            created_by_name = instance.created_by.name
            representation['created_by'] = created_by_name
        return representation


class DoctorAccessSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorAccess
        fields = "__all__"


class LabStaffDataSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = LabStaff
        fields = ['id', 'name', 'role', 'mobile_number']

    def get_role(self, obj):
        return obj.role.name


class DefaultTestParametersSerializer(serializers.ModelSerializer):
    class Meta:
        model = DefaultTestParameters
        fields = '__all__'


from datetime import datetime


def calculate_extra_and_deficit_hours(obj):
    if obj.total_worked_hours is None:
        return {'extra_hours': "", 'deficit_hours': ""}

    if obj.shift_start_time and obj.shift_end_time:
        start_time = datetime.combine(obj.date, obj.shift_start_time)
        end_time = datetime.combine(obj.date, obj.shift_end_time)
    else:
        job_details = LabStaffJobDetails.objects.filter(labstaff=obj.lab_staff).first()

        if job_details and job_details.shift_start_time and job_details.shift_end_time:
            start_time = datetime.combine(obj.date, job_details.shift_start_time)
            end_time = datetime.combine(obj.date, job_details.shift_end_time)
        else:
            raise serializers.ValidationError(
                {'error': 'Shift timings are not available in JobDetails or attendance for this staff'})

    shift_hours = end_time - start_time

    if obj.total_worked_hours > shift_hours:
        extra_minutes = int((obj.total_worked_hours - shift_hours).total_seconds() // 60)
        extra_hours, extra_minutes = divmod(extra_minutes, 60)
        extra_hours_str = f'{extra_hours} hours {extra_minutes} minutes' if extra_hours else f'{extra_minutes} minutes'
        deficit_hours_str = ""
    else:
        deficit_minutes = int((shift_hours - obj.total_worked_hours).total_seconds() // 60)
        deficit_hours, deficit_minutes = divmod(deficit_minutes, 60)
        deficit_hours_str = f'{deficit_hours} hours {deficit_minutes} minutes' if deficit_hours else f'{deficit_minutes} minutes'
        extra_hours_str = ""

    return {
        'extra_hours': extra_hours_str,
        'deficit_hours': deficit_hours_str
    }


class LabStaffAttendanceGetDetailsSerializer(serializers.ModelSerializer):
    extra_hours = serializers.SerializerMethodField()
    deficit_hours = serializers.SerializerMethodField()
    employment_type = serializers.SerializerMethodField()

    class Meta:
        model = LabStaffAttendanceDetails
        fields = "__all__"

    def get_employment_type(self, obj):
        return obj.lab_staff.employement_type.name if obj.lab_staff.employement_type else None

    def get_extra_hours(self, obj):
        return calculate_extra_and_deficit_hours(obj)['extra_hours']

    def get_deficit_hours(self, obj):
        return calculate_extra_and_deficit_hours(obj)['deficit_hours']

    def calculate_shift_hours(self, obj):
        if obj.shift_start_time and obj.shift_end_time:
            start_time = datetime.combine(obj.date, obj.shift_start_time)
            end_time = datetime.combine(obj.date, obj.shift_end_time)
            return end_time - start_time
        else:
            return serializers.ValidationError('Shift timings are not entered for this staff')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['lab_staff'] = (
            {'id': instance.lab_staff.id, 'name': instance.lab_staff.name,
             'mobile_number': instance.lab_staff.mobile_number,
             'profile_pic': instance.lab_staff.profile_pic}) if instance.lab_staff else None
        representation['attendance_status'] = instance.attendance_status.name if instance.attendance_status else None
        representation['total_worked_hours'] = calculate_total_worked_hours(
            instance.total_worked_hours) if instance.total_worked_hours else None
        return representation


class LabStaffPayRollSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabStaffPayRoll
        fields = "__all__"


class LabStaffPayRollGetSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabStaffPayRoll
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['payment_structure'] = instance.payment_structure.name if instance.payment_structure else None
        return representation


class LeavePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = '__all__'


class LabStaffLeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabStaffLeaveRequest
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['lab_staff'] = ({
            'id': instance.lab_staff.id, 'name': instance.lab_staff.name,
            'mobile_number': instance.lab_staff.mobile_number, 'profile_pic': instance.lab_staff.profile_pic
        }) if instance.lab_staff else None
        representation['leave_type'] = (
            {'id': instance.leave_type.id, 'name': instance.leave_type.name}) if instance.leave_type else None
        representation['status'] = (
            {'id': instance.status.id, 'name': instance.status.name}) if instance.status else None
        return representation


class LabStaffWithPayRollSerializer(serializers.ModelSerializer):
    payroll = serializers.SerializerMethodField()

    class Meta:
        model = LabStaff
        fields = ['id', 'name', 'mobile_number', 'profile_pic', 'payroll']

    def get_payroll(self, obj):
        payroll = obj.labstaffpayroll_set.first()
        if payroll:
            return LabStaffPayRollGetSerializer(payroll).data
        return None


class LabStaffDefaultBranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabStaffDefaultBranch
        fields = '__all__'