from rest_framework import serializers

from pro_laboratory.models.global_models import LabStaff
from pro_laboratory.models.marketing_models import LabStaffVehicleDetails, MarketingExecutiveVisits, \
    MarketingExecutiveLocationTracker, MarketingExecutiveTargets
from pro_universal_data.serializers import UniversalVehicleTypesSerializer, UniversalFuelTypesSerializer


class LabStaffVehicleDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabStaffVehicleDetails
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        representation['fuel_type'] = UniversalVehicleTypesSerializer(
            instance.fuel_type).data if instance.fuel_type else None
        representation['vehicle_type'] = UniversalFuelTypesSerializer(
            instance.vehicle_type).data if instance.vehicle_type else None

        return representation


def calculate_total_worked_hours(total_time_taken):
    if not total_time_taken:
        return None

    days = total_time_taken.days
    total_seconds = total_time_taken.total_seconds()
    hours, remainder = divmod(total_seconds - days * 86400, 3600)
    minutes, seconds = divmod(remainder, 60)

    time_parts = []

    if days > 0:
        time_parts.append(f'{days} day{"s" if days > 1 else ""}')

    if hours > 0:
        time_parts.append(f'{int(hours)} hr{"s" if hours > 1 else ""}')

    if minutes > 0:
        time_parts.append(f'{int(minutes)} min{"s" if minutes > 1 else ""}')

    if seconds > 0 and len(time_parts) == 0:
        time_parts.append(f'{int(seconds)}s')

    return ' '.join(time_parts)


class MarketingExecutiveVisitsSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketingExecutiveVisits
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        related_fields = ['lab_staff', 'created_by', 'last_updated_by', 'visit_type', 'status']
        for field in related_fields:
            related_instance = getattr(instance, field, None)
            representation[field] = {"id": related_instance.id,
                                     "name": related_instance.name} if related_instance else None

        representation['total_time_taken'] = calculate_total_worked_hours(instance.total_time_taken)

        return representation


class MarketingExecutiveVisitsByLabstaffSerializer(serializers.ModelSerializer):
    visits = MarketingExecutiveVisitsSerializer(many=True, read_only=True)
    total_visits = serializers.IntegerField(read_only=True)
    pending_visits = serializers.IntegerField(read_only=True)
    followup_visits = serializers.IntegerField(read_only=True)
    accepted_visits = serializers.IntegerField(read_only=True)
    denied_visits = serializers.IntegerField(read_only=True)
    total_time_taken = serializers.DurationField(read_only=True)
    first_start_time = serializers.DateTimeField(read_only=True)
    last_end_time = serializers.DateTimeField(read_only=True)

    class Meta:
        model = LabStaff
        fields = ['id', 'name', 'mobile_number', 'profile_pic', 'visits', 'total_visits', 'pending_visits',
                  'followup_visits', 'accepted_visits', 'denied_visits', 'total_time_taken', 'first_start_time',
                  'last_end_time']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['total_time_taken'] = calculate_total_worked_hours(instance.total_time_taken)
        return representation


class MarketingExecutiveLocationTrackerSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketingExecutiveLocationTracker
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        lab_staff = instance.lab_staff

        if lab_staff:
            representation['lab_staff'] = {"id": lab_staff.id, "name": lab_staff.name}

        return representation


class MarketingExecutiveTargetsSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketingExecutiveTargets
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        related_fields = ['labstaff', 'target_type', 'target_duration']
        representation.update({
            field: getattr(getattr(instance, field, None), 'name', None) for field in related_fields
        })
        return representation


class MarketingExecutiveTargetsByLabstaffSerializer(serializers.ModelSerializer):
    targets = MarketingExecutiveTargetsSerializer(many=True, read_only=True, source='marketingexecutivetargets_set')
    total_visits = serializers.IntegerField(read_only=True)
    pending_visits = serializers.IntegerField(read_only=True)
    followup_visits = serializers.IntegerField(read_only=True)
    accepted_visits = serializers.IntegerField(read_only=True)
    denied_visits = serializers.IntegerField(read_only=True)
    total_time_taken = serializers.DurationField(read_only=True)
    first_start_time = serializers.DateTimeField(read_only=True)
    last_end_time = serializers.DateTimeField(read_only=True)

    class Meta:
        model = LabStaff
        fields = ['id', 'name', 'mobile_number', 'profile_pic', 'targets', 'total_visits', 'pending_visits',
                  'followup_visits', 'accepted_visits', 'denied_visits', 'total_time_taken', 'first_start_time',
                  'last_end_time']


class MarketingExecutiveStatsSerializer(serializers.ModelSerializer):
    referral_doctors_count = serializers.IntegerField()
    patients_count = serializers.IntegerField()

    class Meta:
        model = LabStaff
        fields = ['id', 'name', 'referral_doctors_count', 'patients_count']