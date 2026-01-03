from datetime import datetime, timedelta
import django_filters
import pytz
from django.db.models import Q
from django.utils import timezone

from healtho_pro_user.models.business_models import BusinessProfiles
from pro_laboratory.models.bulk_messaging_models import BulkMessagingLogs, BulkWhatsAppMessagingLogs, \
    BulkMessagingHistory
from pro_laboratory.models.doctorAuthorization_models import LabDrAuthorization
from pro_laboratory.models.doctors_models import LabDoctors
from pro_laboratory.models.global_models import LabStaff, LabStaffAttendanceDetails
from pro_laboratory.models.lab_appointment_of_patient_models import LabAppointmentForPatient
from pro_laboratory.models.labtechnicians_models import LabTechnicians
from pro_laboratory.models.marketing_models import MarketingExecutiveVisits, MarketingExecutiveTargets
from pro_laboratory.models.messaging_models import MessagingLogs, WhatsAppMessagingLogs
from pro_laboratory.models.patient_models import Patient, LabPatientTests, LabPatientInvoice, LabPatientReceipts
from pro_laboratory.models.phlebotomists_models import LabPhlebotomist
from django_filters import rest_framework as filters

from pro_laboratory.models.privilege_card_models import PrivilegeCards, PrivilegeCardMemberships
from pro_laboratory.models.sourcing_lab_models import SourcingLabTestsTracker
from pro_laboratory.models.universal_models import TpaUltrasound, ActivityLogs


class PatientFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(field_name='added_on', method='filter_by_date')
    date_range = django_filters.DateFromToRangeFilter(field_name='added_on', method='filter_by_date_range')

    def filter_by_date(self, queryset, name, value):
        start_date = datetime.combine(value, datetime.min.time())
        end_date = start_date + timedelta(days=1) - timedelta(seconds=1)  # Last second of the day
        return queryset.filter(added_on__range=(start_date, end_date))

    def filter_by_date_range(self, queryset, name, value):
        start_date = datetime.combine(value.start, datetime.min.time())
        end_date = datetime.combine(value.stop, datetime.max.time())
        return queryset.filter(added_on__range=(start_date, end_date))

    class Meta:
        model = Patient
        fields = ['date', 'date_range', 'id','patient_type']


class BusinessProfilesFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(field_name='added_on', method='filter_by_date')
    date_range = django_filters.DateFromToRangeFilter(field_name='added_on', method='filter_by_date_range')

    def filter_by_date(self, queryset, name, value):
        start_date = datetime.combine(value, datetime.min.time())
        end_date = start_date + timedelta(days=1) - timedelta(seconds=1)  # Last second of the day
        return queryset.filter(added_on__range=(start_date, end_date))

    def filter_by_date_range(self, queryset, name, value):
        start_date = datetime.combine(value.start, datetime.min.time())
        end_date = datetime.combine(value.stop, datetime.max.time())
        return queryset.filter(added_on__range=(start_date, end_date))

    class Meta:
        model = BusinessProfiles
        fields = ['date', 'date_range', 'id', 'provider_type', 'city', 'state', 'country', 'is_active', 'pin_code',
                  'is_account_disabled']


class SourcingLabTestsTrackerFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(field_name='added_on', method='filter_by_date')
    date_range = django_filters.DateFromToRangeFilter(field_name='added_on', method='filter_by_date_range')

    def filter_by_date(self, queryset, name, value):
        start_date = datetime.combine(value, datetime.min.time())
        end_date = start_date + timedelta(days=1) - timedelta(seconds=1)  # Last second of the day
        return queryset.filter(added_on__range=(start_date, end_date))

    def filter_by_date_range(self, queryset, name, value):
        start_date = datetime.combine(value.start, datetime.min.time())
        end_date = datetime.combine(value.stop, datetime.max.time())
        return queryset.filter(added_on__range=(start_date, end_date))

    class Meta:
        model = SourcingLabTestsTracker
        fields = ['date', 'date_range', 'id', 'sourcing_lab', 'patient_id', 'lab_patient_test', 'to_send', 'is_sent',
                  'is_received', 'is_cancelled', 'patient_id_at_client']


class MessagingStatisticsFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(field_name='sent_on', method='filter_by_date')
    date_range = django_filters.DateFromToRangeFilter(field_name='sent_on', method='filter_by_date_range')

    def filter_by_date(self, queryset, name, value):
        start_date = datetime.combine(value, datetime.min.time())
        end_date = start_date + timedelta(days=1) - timedelta(seconds=1)  # Last second of the day
        return queryset.filter(sent_on__range=(start_date, end_date))

    def filter_by_date_range(self, queryset, name, value):
        start_date = datetime.combine(value.start, datetime.min.time())
        end_date = datetime.combine(value.stop, datetime.max.time())
        return queryset.filter(sent_on__range=(start_date, end_date))

    class Meta:
        model = MessagingLogs
        fields = ['date', 'date_range', 'response_code']


class WhatsappMessagingStatisticsFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(field_name='sent_on', method='filter_by_date')
    date_range = django_filters.DateFromToRangeFilter(field_name='sent_on', method='filter_by_date_range')

    def filter_by_date(self, queryset, name, value):
        start_date = datetime.combine(value, datetime.min.time())
        end_date = start_date + timedelta(days=1) - timedelta(seconds=1)  # Last second of the day
        return queryset.filter(sent_on__range=(start_date, end_date))

    def filter_by_date_range(self, queryset, name, value):
        start_date = datetime.combine(value.start, datetime.min.time())
        end_date = datetime.combine(value.stop, datetime.max.time())
        return queryset.filter(sent_on__range=(start_date, end_date))

    class Meta:
        model = WhatsAppMessagingLogs
        fields = ['date', 'date_range', 'response_code']


class LabAppointmentForPatientFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(field_name='added_on', method='filter_by_date')
    date_range = django_filters.DateFromToRangeFilter(field_name='added_on', method='filter_by_date_range')
    apt_date = django_filters.DateFilter(field_name='appointment_time', method='filter_by_apt_date')
    apt_date_range = django_filters.DateFromToRangeFilter(field_name='appointment_time', method='filter_by_apt_date_range')
    patient_null = django_filters.BooleanFilter(field_name='patient', lookup_expr='isnull')

    def filter_by_date(self, queryset, name, value):
        start_date = datetime.combine(value, datetime.min.time())
        end_date = start_date + timedelta(days=1) - timedelta(seconds=1)  # Last second of the day
        return queryset.filter(added_on__range=(start_date, end_date))

    def filter_by_date_range(self, queryset, name, value):
        start_date = datetime.combine(value.start, datetime.min.time())
        end_date = datetime.combine(value.stop, datetime.max.time())
        return queryset.filter(added_on__range=(start_date, end_date))

    def filter_by_apt_date(self, queryset, name, value):
        start_date = datetime.combine(value, datetime.min.time())
        end_date = start_date + timedelta(days=1) - timedelta(seconds=1)  # Last second of the day
        return queryset.filter(appointment_date__range=(start_date, end_date))

    def filter_by_apt_date_range(self, queryset, name, value):
        start_date = datetime.combine(value.start, datetime.min.time())
        end_date = datetime.combine(value.stop, datetime.max.time())
        return queryset.filter(appointment_date__range=(start_date, end_date))

    class Meta:
        model = LabAppointmentForPatient
        fields = ['date', 'date_range', 'apt_date', 'apt_date_range', 'id', 'referral_doctor', 'consulting_doctor',
                  'is_cancelled']


class PrivilegeCardsFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(field_name='added_on', method='filter_by_date')
    date_range = django_filters.DateFromToRangeFilter(field_name='added_on', method='filter_by_date_range')
    validity_date_range = django_filters.DateFromToRangeFilter(method='filter_by_validity_date_range')

    def filter_by_date(self, queryset, name, value):
        start_date = datetime.combine(value, datetime.min.time())
        end_date = start_date + timedelta(days=1) - timedelta(seconds=1)  # Last second of the day
        return queryset.filter(added_on__range=(start_date, end_date))

    def filter_by_date_range(self, queryset, name, value):
        start_date = datetime.combine(value.start, datetime.min.time())
        end_date = datetime.combine(value.stop, datetime.max.time())
        return queryset.filter(added_on__range=(start_date, end_date))

    class Meta:
        model = PrivilegeCards
        fields = ['date', 'date_range', 'id', 'created_by', 'last_updated_by']


class PrivilegeCardMembershipsFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(field_name='added_on', method='filter_by_date')
    date_range = django_filters.DateFromToRangeFilter(field_name='added_on', method='filter_by_date_range')
    validity_date_range = django_filters.DateFromToRangeFilter(method='filter_by_validity_date_range')

    def filter_by_date(self, queryset, name, value):
        start_date = datetime.combine(value, datetime.min.time())
        end_date = start_date + timedelta(days=1) - timedelta(seconds=1)  # Last second of the day
        return queryset.filter(added_on__range=(start_date, end_date))

    def filter_by_date_range(self, queryset, name, value):
        start_date = datetime.combine(value.start, datetime.min.time())
        end_date = datetime.combine(value.stop, datetime.max.time())
        return queryset.filter(added_on__range=(start_date, end_date))

    def filter_by_validity_date_range(self, queryset, name, value):
        if value.start and not value.stop:
            start_date = datetime.combine(value.start, datetime.min.time())
            queryset = queryset.filter(validity_ends_on__gte=start_date)
        elif value.stop and not value.start:
            end_date = datetime.combine(value.stop, datetime.max.time())
            queryset = queryset.filter(validity_starts_on__lte=end_date)
        elif value.start and value.stop:
            start_date = datetime.combine(value.start, datetime.min.time())
            end_date = datetime.combine(value.stop, datetime.max.time())
            queryset = queryset.filter(validity_starts_on__lte=end_date, validity_ends_on__gte=start_date)
        return queryset

    class Meta:
        model = PrivilegeCardMemberships
        fields = ['date', 'date_range', 'validity_date_range', 'id', 'card', 'duration_type', 'created_by',
                  'last_updated_by']


class TpaUltraSoundFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(field_name='added_on', method='filter_by_date')
    date_range = django_filters.DateFromToRangeFilter(field_name='added_on', method='filter_by_date_range')

    def filter_by_date(self, queryset, name, value):
        start_date = datetime.combine(value, datetime.min.time())
        end_date = start_date + timedelta(days=1) - timedelta(seconds=1)  # Last second of the day
        return queryset.filter(added_on__range=(start_date, end_date))

    def filter_by_date_range(self, queryset, name, value):
        start_date = datetime.combine(value.start, datetime.min.time())
        end_date = datetime.combine(value.stop, datetime.max.time())
        return queryset.filter(added_on__range=(start_date, end_date))

    class Meta:
        model = TpaUltrasound
        fields = ['date', 'date_range']


# Define a custom filter class that can handle multiple IDs
class NumberInFilter(django_filters.BaseInFilter, django_filters.NumberFilter):
    pass


class LabTestFilter(django_filters.FilterSet):
    department = django_filters.CharFilter()
    status_id = NumberInFilter(field_name='status_id', lookup_expr='in')

    class Meta:
        model = LabPatientTests
        fields = ['department', 'status_id']

class LabTestFilterForPatientView(django_filters.FilterSet):
    departments = NumberInFilter(field_name='department', lookup_expr='in')
    status_id = NumberInFilter(field_name='status_id', lookup_expr='in')
    date = django_filters.DateFilter(field_name='added_on', method='filter_by_date')
    date_range = django_filters.DateFromToRangeFilter(field_name='added_on', method='filter_by_date_range')

    def filter_by_date(self, queryset, name, value):
        start_date = datetime.combine(value, datetime.min.time())
        end_date = start_date + timedelta(days=1) - timedelta(seconds=1)  # Last second of the day
        return queryset.filter(added_on__range=(start_date, end_date))

    def filter_by_date_range(self, queryset, name, value):
        start_date = datetime.combine(value.start, datetime.min.time())
        end_date = datetime.combine(value.stop, datetime.max.time())
        return queryset.filter(added_on__range=(start_date, end_date))

    class Meta:
        model = LabPatientTests
        fields = ['departments', 'status_id','date','date_range']


class LabPatientTestsFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(method='filter_by_date')
    date_range = django_filters.DateFromToRangeFilter(field_name='added_on', method='filter_by_date_range')

    def filter_by_date(self, queryset, name, value):
        tz = pytz.timezone('Asia/Kolkata')
        datetime_value = timezone.make_aware(datetime.combine(value, datetime.min.time()), tz)
        return queryset.filter(added_on__gte=datetime_value, added_on__lt=datetime_value + timedelta(days=1))

    def filter_by_date_range(self, queryset, name, value):
        tz = pytz.timezone('Asia/Kolkata')
        from_date = timezone.make_aware(datetime.combine(value.start, datetime.min.time()), tz)
        to_date = timezone.make_aware(datetime.combine(value.stop, datetime.min.time()), tz) + timedelta(days=1)
        return queryset.filter(added_on__gte=from_date, added_on__lt=to_date)

    @property
    def qs(self):
        queryset = super().qs
        if 'date_range' in self.form.data:
            return self.filter_by_date_range(queryset, 'added_on', self.form.data['date_range'])
        return queryset

    class Meta:
        model = LabPatientTests
        fields = ['date']


class PatientAnalyticsFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(field_name='added_on', method='filter_by_date')
    date_range = django_filters.DateFromToRangeFilter(field_name='added_on', method='filter_by_date_range')

    def filter_by_date(self, queryset, name, value):
        start_date = datetime.combine(value, datetime.min.time())
        end_date = start_date + timedelta(days=1) - timedelta(seconds=1)  # Last second of the day
        return queryset.filter(added_on__range=(start_date, end_date))

    def filter_by_date_range(self, queryset, name, value):
        start_date = datetime.combine(value.start, datetime.min.time())
        end_date = datetime.combine(value.stop, datetime.max.time())
        return queryset.filter(added_on__range=(start_date, end_date))

    class Meta:
        model = Patient
        fields = ['date', 'date_range']


class LabPhlebotomistAnalyticsFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(field_name='added_on', method='filter_by_date')
    date_range = django_filters.DateFromToRangeFilter(field_name='added_on', method='filter_by_date_range')

    def filter_by_date(self, queryset, name, value):
        start_date = datetime.combine(value, datetime.min.time())
        end_date = start_date + timedelta(days=1) - timedelta(seconds=1)
        return queryset.filter(added_on__range=(start_date, end_date))

    def filter_by_date_range(self, queryset, name, value):
        start_date = datetime.combine(value.start, datetime.min.time())
        end_date = datetime.combine(value.stop, datetime.max.time())
        return queryset.filter(added_on__range=(start_date, end_date))

    class Meta:
        model = LabPhlebotomist
        fields = ['date', 'date_range']


class LabTechniciansAnalyticsFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(field_name='added_on', method='filter_by_date')
    date_range = django_filters.DateFromToRangeFilter(field_name='added_on', method='filter_by_date_range')

    def filter_by_date(self, queryset, name, value):
        start_date = datetime.combine(value, datetime.min.time())
        end_date = start_date + timedelta(days=1) - timedelta(seconds=1)
        return queryset.filter(added_on__range=(start_date, end_date))

    def filter_by_date_range(self, queryset, name, value):
        start_date = datetime.combine(value.start, datetime.min.time())
        end_date = datetime.combine(value.stop, datetime.max.time())
        return queryset.filter(added_on__range=(start_date, end_date))

    class Meta:
        model = LabTechnicians
        fields = ['date', 'date_range']


class LabDoctorAuthorizationAnalyticsFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(field_name='added_on', method='filter_by_date')
    date_range = django_filters.DateFromToRangeFilter(field_name='added_on', method='filter_by_date_range')

    def filter_by_date(self, queryset, name, value):
        start_date = datetime.combine(value, datetime.min.time())
        end_date = start_date + timedelta(days=1) - timedelta(seconds=1)
        return queryset.filter(added_on__range=(start_date, end_date))

    def filter_by_date_range(self, queryset, name, value):
        start_date = datetime.combine(value.start, datetime.min.time())
        end_date = datetime.combine(value.stop, datetime.max.time())
        return queryset.filter(added_on__range=(start_date, end_date))

    class Meta:
        model = LabDrAuthorization
        fields = ['date', 'date_range']


class BusinessStatusFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(field_name='added_on', method='filter_by_date')
    date_range = django_filters.DateFromToRangeFilter(field_name='added_on', method='filter_by_date_range')

    def filter_by_date(self, queryset, name, value):
        start_date = datetime.combine(value, datetime.min.time())
        end_date = start_date + timedelta(days=1) - timedelta(seconds=1)  # Last second of the day
        return queryset.filter(added_on__range=(start_date, end_date))

    def filter_by_date_range(self, queryset, name, value):
        start_date = datetime.combine(value.start, datetime.min.time())
        end_date = datetime.combine(value.stop, datetime.max.time())
        return queryset.filter(added_on__range=(start_date, end_date))

    class Meta:
        model = LabPatientInvoice
        fields = ['date', 'date_range']


class LabTestAnalyticsFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(field_name='added_on', method='filter_by_date')
    date_range = django_filters.DateFromToRangeFilter(field_name='added_on', method='filter_by_date_range')

    def filter_by_date(self, queryset, name, value):
        start_date = datetime.combine(value, datetime.min.time())
        end_date = start_date + timedelta(days=1) - timedelta(seconds=1)  # Last second of the day
        return queryset.filter(added_on__range=(start_date, end_date))

    def filter_by_date_range(self, queryset, name, value):
        start_date = datetime.combine(value.start, datetime.min.time())
        end_date = datetime.combine(value.stop, datetime.max.time())
        return queryset.filter(added_on__range=(start_date, end_date))

    class Meta:
        model = LabPatientTests
        fields = ['date', 'date_range']


class DepartmentAnalyticsFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(field_name='added_on', method='filter_by_date')
    date_range = django_filters.DateFromToRangeFilter(field_name='added_on', method='filter_by_date_range')

    def filter_by_date(self, queryset, name, value):
        start_date = datetime.combine(value, datetime.min.time())
        end_date = start_date + timedelta(days=1) - timedelta(seconds=1)  # Last second of the day
        return queryset.filter(added_on__range=(start_date, end_date))

    def filter_by_date_range(self, queryset, name, value):
        start_date = datetime.combine(value.start, datetime.min.time())
        end_date = datetime.combine(value.stop, datetime.max.time())
        return queryset.filter(added_on__range=(start_date, end_date))

    class Meta:
        model = LabPatientTests
        fields = ['date', 'date_range']


class PayModeAnalyticsFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(field_name='added_on', method='filter_by_date')
    date_range = django_filters.DateFromToRangeFilter(field_name='added_on', method='filter_by_date_range')

    def filter_by_date(self, queryset, name, value):
        start_date = datetime.combine(value, datetime.min.time())
        end_date = start_date + timedelta(days=1) - timedelta(seconds=1)  # Last second of the day
        return queryset.filter(added_on__range=(start_date, end_date))

    def filter_by_date_range(self, queryset, name, value):
        start_date = datetime.combine(value.start, datetime.min.time())
        end_date = datetime.combine(value.stop, datetime.max.time())
        return queryset.filter(added_on__range=(start_date, end_date))

    class Meta:
        model = LabPatientReceipts
        fields = ['date', 'date_range']


class ReferralDoctorDetailsFilter(filters.FilterSet):
    date = django_filters.DateFilter(field_name='added_on', method='filter_by_date')
    date_range = django_filters.DateFromToRangeFilter(field_name='added_on', method='filter_by_date_range')

    def filter_by_date(self, queryset, name, value):
        start_date = datetime.combine(value, datetime.min.time())
        end_date = start_date + timedelta(days=1) - timedelta(seconds=1)  # Last second of the day
        return queryset.filter(added_on__range=(start_date, end_date))

    def filter_by_date_range(self, queryset, name, value):
        start_date = datetime.combine(value.start, datetime.min.time())
        end_date = datetime.combine(value.stop, datetime.max.time())
        return queryset.filter(added_on__range=(start_date, end_date))

    class Meta:
        model = Patient
        fields = ['date', 'date_range']


class PatientRegistrationOverviewFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(field_name='added_on', method='filter_by_date')
    date_range = django_filters.DateFromToRangeFilter(field_name='added_on', method='filter_by_date_range')

    def filter_by_date(self, queryset, name, value):
        start_date = datetime.combine(value, datetime.min.time())
        end_date = start_date + timedelta(days=1) - timedelta(seconds=1)  # Last second of the day
        return queryset.filter(added_on__range=(start_date, end_date))

    def filter_by_date_range(self, queryset, name, value):
        start_date = datetime.combine(value.start, datetime.min.time())
        end_date = datetime.combine(value.stop, datetime.max.time())
        return queryset.filter(added_on__range=(start_date, end_date))

    class Meta:
        model = Patient
        fields = ['date', 'date_range']


class LabDoctorAuthorizationFilter(django_filters.FilterSet):
    date = filters.DateFilter(method='filter_by_date')
    date_range = django_filters.DateFromToRangeFilter(field_name='added_on',
                                                      method='filter_by_date_range')

    def filter_by_date(self, queryset, name, value):
        tz = pytz.timezone('Asia/Kolkata')
        datetime_value = datetime.combine(value, datetime.min.time())
        datetime_value = tz.localize(datetime_value)
        return queryset.filter(patient__added_on__gte=datetime_value,
                               patient__added_on__lt=datetime_value + timedelta(days=1))

    def filter_by_date_range(self, queryset, name, value):
        tz = pytz.timezone('Asia/Kolkata')
        from_date = datetime.combine(value.start, datetime.min.time())
        from_date = tz.localize(from_date)
        to_date = datetime.combine(value.stop, datetime.min.time()) + timedelta(days=1)
        to_date = tz.localize(to_date)
        return queryset.filter(patient__added_on__gte=from_date, patient__added_on__lt=to_date)

    @property
    def qs(self):
        queryset = super().qs
        if 'date_range' in self.form.data:
            return self.filter_by_date_range(queryset, 'patient__added_on', self.form.data['date_range'])
        return queryset

    class Meta:
        model = LabPatientTests
        fields = ['date', 'date_range']


class LabDoctorFilter(django_filters.FilterSet):
    date = filters.DateFilter(method='filter_by_date')
    date_range = django_filters.DateFromToRangeFilter(field_name='added_on', method='filter_by_date_range')

    def filter_by_date(self, queryset, name, value):
        tz = pytz.timezone('Asia/Kolkata')
        datetime_value = datetime.combine(value, datetime.min.time())
        datetime_value = tz.localize(datetime_value)
        return queryset.filter(added_on__gte=datetime_value, added_on__lt=datetime_value + timedelta(days=1))

    def filter_by_date_range(self, queryset, name, value):
        tz = pytz.timezone('Asia/Kolkata')
        from_date = datetime.combine(value.start, datetime.min.time())
        from_date = tz.localize(from_date)
        to_date = datetime.combine(value.stop, datetime.min.time()) + timedelta(days=1)
        to_date = tz.localize(to_date)
        return queryset.filter(added_on__gte=from_date, added_on__lt=to_date)

    @property
    def qs(self):
        queryset = super().qs
        if 'date_range' in self.form.data:
            return self.filter_by_date_range(queryset, 'added_on', self.form.data['date_range'])
        return queryset

    class Meta:
        model = LabDoctors
        fields = ['id', 'date', 'date_range']


class LabStaffFilter(django_filters.FilterSet):
    date = filters.DateFilter(method='filter_by_date')
    date_range = django_filters.DateFromToRangeFilter(field_name='added_on', method='filter_by_date_range')

    def filter_by_date(self, queryset, name, value):
        tz = pytz.timezone('Asia/Kolkata')
        datetime_value = datetime.combine(value, datetime.min.time())
        datetime_value = tz.localize(datetime_value)
        return queryset.filter(added_on__gte=datetime_value, added_on__lt=datetime_value + timedelta(days=1))

    def filter_by_date_range(self, queryset, name, value):
        tz = pytz.timezone('Asia/Kolkata')
        from_date = datetime.combine(value.start, datetime.min.time())
        from_date = tz.localize(from_date)
        to_date = datetime.combine(value.stop, datetime.min.time()) + timedelta(days=1)
        to_date = tz.localize(to_date)
        return queryset.filter(added_on__gte=from_date, added_on__lt=to_date)

    @property
    def qs(self):
        queryset = super().qs
        if 'date_range' in self.form.data:
            return self.filter_by_date_range(queryset, 'added_on', self.form.data['date_range'])
        return queryset

    class Meta:
        model = LabStaff
        fields = ['date', 'date_range']


class LabTechniciansFilter(django_filters.FilterSet):
    date = filters.DateFilter(method='filter_by_date')
    date_range = django_filters.DateFromToRangeFilter(field_name='added_on', method='filter_by_date_range')

    def filter_by_date(self, queryset, name, value):
        tz = pytz.timezone('Asia/Kolkata')
        datetime_value = timezone.make_aware(datetime.combine(value, datetime.min.time()), tz)
        return queryset.filter(LabPatientTestID__patient__added_on__gte=datetime_value,
                               LabPatientTestID__patient__added_on__lt=datetime_value + timedelta(days=1))

    def filter_by_date_range(self, queryset, name, value):
        tz = pytz.timezone('Asia/Kolkata')
        from_date = timezone.make_aware(datetime.combine(value.start, datetime.min.time()), tz)
        to_date = timezone.make_aware(datetime.combine(value.stop, datetime.min.time()), tz) + timedelta(days=1)
        return queryset.filter(LabPatientTestID__patient__added_on__gte=from_date,
                               LabPatientTestID__patient__added_on__lt=to_date)

    @property
    def qs(self):
        queryset = super().qs
        if 'date_range' in self.form.data:
            return self.filter_by_date_range(queryset, 'LabPatientTestID__patient__added_on',
                                             self.form.data['date_range'])
        return queryset

    class Meta:
        model = LabTechnicians
        fields = ['date', 'date_range']


class LabPhlebotomistFilter(django_filters.FilterSet):
    date = filters.DateFilter(method='filter_by_date')
    date_range = django_filters.DateFromToRangeFilter(field_name='added_on',
                                                      method='filter_by_date_range')

    def filter_by_date(self, queryset, name, value):
        tz = pytz.timezone('Asia/Kolkata')
        datetime_value = datetime.combine(value, datetime.min.time())
        datetime_value = tz.localize(datetime_value)
        return queryset.filter(patient__added_on__gte=datetime_value,
                               patient__added_on__lt=datetime_value + timedelta(days=1))

    def filter_by_date_range(self, queryset, name, value):
        tz = pytz.timezone('Asia/Kolkata')
        from_date = datetime.combine(value.start, datetime.min.time())
        from_date = tz.localize(from_date)
        to_date = datetime.combine(value.stop, datetime.min.time()) + timedelta(days=1)
        to_date = tz.localize(to_date)
        return queryset.filter(patient__added_on__gte=from_date, patient__added_on__lt=to_date)

    @property
    def qs(self):
        queryset = super().qs
        if 'date_range' in self.form.data:
            return self.filter_by_date_range(queryset, 'patient__added_on', self.form.data['date_range'])
        return queryset

    class Meta:
        model = LabPatientTests
        fields = ['date', 'date_range', 'is_outsourcing', 'sourcing_lab']


class ActivityLogsFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(field_name='timestamp', method='filter_by_date')
    date_range = django_filters.DateFromToRangeFilter(field_name='timestamp', method='filter_by_date_range')

    def filter_by_date(self, queryset, name, value):
        start_date = datetime.combine(value, datetime.min.time())
        end_date = start_date + timedelta(days=1) - timedelta(seconds=1)  # Last second of the day
        return queryset.filter(timestamp__range=(start_date, end_date))

    def filter_by_date_range(self, queryset, name, value):
        start_date = datetime.combine(value.start, datetime.min.time())
        end_date = datetime.combine(value.stop, datetime.max.time())
        return queryset.filter(timestamp__range=(start_date, end_date))

    class Meta:
        model = ActivityLogs
        fields = ['date', 'date_range', 'id', 'user', 'client', 'lab_staff', 'operation', 'url', 'model',
                  'response_code', 'duration', 'patient', 'timestamp']


class BulkMessagingStatisticsFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(field_name='sent_on', method='filter_by_date')
    date_range = django_filters.DateFromToRangeFilter(field_name='sent_on', method='filter_by_date_range')

    def filter_by_date(self, queryset, name, value):
        start_date = datetime.combine(value, datetime.min.time())
        end_date = start_date + timedelta(days=1) - timedelta(seconds=1)  # Last second of the day
        return queryset.filter(sent_on__range=(start_date, end_date))

    def filter_by_date_range(self, queryset, name, value):
        start_date = datetime.combine(value.start, datetime.min.time())
        end_date = datetime.combine(value.stop, datetime.max.time())
        return queryset.filter(sent_on__range=(start_date, end_date))

    class Meta:
        model = BulkMessagingLogs
        fields = ['date', 'date_range', 'response_code']


class BulkWhatsappMessagingStatisticsFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(field_name='sent_on', method='filter_by_date')
    date_range = django_filters.DateFromToRangeFilter(field_name='sent_on', method='filter_by_date_range')

    def filter_by_date(self, queryset, name, value):
        start_date = datetime.combine(value, datetime.min.time())
        end_date = start_date + timedelta(days=1) - timedelta(seconds=1)  # Last second of the day
        return queryset.filter(sent_on__range=(start_date, end_date))

    def filter_by_date_range(self, queryset, name, value):
        start_date = datetime.combine(value.start, datetime.min.time())
        end_date = datetime.combine(value.stop, datetime.max.time())
        return queryset.filter(sent_on__range=(start_date, end_date))

    class Meta:
        model = BulkWhatsAppMessagingLogs
        fields = ['date', 'date_range', 'response_code']


class MarketingExecutiveVisitsFilter(django_filters.FilterSet):
    date_range = django_filters.DateFromToRangeFilter(field_name='date')

    class Meta:
        model = MarketingExecutiveVisits
        fields = ['date', 'date_range', 'id', 'visit_type', 'status', 'created_by', 'lab_staff']


class LabStaffAttendanceDetailsFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(field_name='date', method='filter_by_date')
    date_range = django_filters.DateFromToRangeFilter(field_name='date', method='filter_by_date_range')

    def filter_by_date(self, queryset, name, value):
        start_date = datetime.combine(value, datetime.min.time())
        end_date = start_date + timedelta(days=1) - timedelta(seconds=1)  # Last second of the day
        return queryset.filter(added_on__range=(start_date, end_date))

    def filter_by_date_range(self, queryset, name, value):
        start_date = datetime.combine(value.start, datetime.min.time())
        end_date = datetime.combine(value.stop, datetime.max.time())
        return queryset.filter(added_on__range=(start_date, end_date))

    class Meta:
        model = LabStaffAttendanceDetails
        fields = ['date', 'date_range', 'id', 'lab_staff']


class MarketingExecutiveTargetsFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(field_name='added_on', method='filter_by_date')
    date_range = django_filters.DateFromToRangeFilter(field_name='added_on', method='filter_by_date_range')

    def filter_by_date(self, queryset, name, value):
        start_date = datetime.combine(value, datetime.min.time())
        end_date = start_date + timedelta(days=1) - timedelta(seconds=1)  # Last second of the day
        return queryset.filter(added_on__range=(start_date, end_date))

    def filter_by_date_range(self, queryset, name, value):
        start_date = datetime.combine(value.start, datetime.min.time())
        end_date = datetime.combine(value.stop, datetime.max.time())
        return queryset.filter(added_on__range=(start_date, end_date))

    class Meta:
        model = MarketingExecutiveTargets
        fields = ['date', 'date_range', 'labstaff']


class LabPhlebotomistListFilter(django_filters.FilterSet):
    date = filters.DateFilter(method='filter_by_date')
    date_range = django_filters.DateFromToRangeFilter(field_name='added_on',
                                                      method='filter_by_date_range')
    q = django_filters.CharFilter(method='filter_by_patient_or_test')
    status_id = django_filters.CharFilter(method='filter_by_test_status')

    def filter_by_patient_or_test(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value) |  # patient name
            Q(labpatienttests__name__icontains=value) |  # test name
            Q(labpatienttests__phlebotomist__assession_number__icontains=value)  # test accession number
        ).distinct()

    def filter_by_test_status(self, queryset, name, value):
        status_ids_list = value.split(',')
        sample_collected_status_ids = ['18', '19', '20']
        if len(status_ids_list) == len(sample_collected_status_ids):
            current_date = timezone.now().date()
            queryset = queryset.filter(
                labpatienttests__status_id__in=status_ids_list,
                labpatienttests__phlebotomist__collected_at__date=current_date
            )
        else:
            queryset = queryset.filter(labpatienttests__status_id__in=status_ids_list)
        return queryset

    def filter_by_date(self, queryset, name, value):
        tz = pytz.timezone('Asia/Kolkata')
        datetime_value = datetime.combine(value, datetime.min.time())
        datetime_value = tz.localize(datetime_value)
        return queryset.filter(added_on__gte=datetime_value,
                               added_on__lt=datetime_value + timedelta(days=1))

    def filter_by_date_range(self, queryset, name, value):
        tz = pytz.timezone('Asia/Kolkata')
        from_date = datetime.combine(value.start, datetime.min.time())
        from_date = tz.localize(from_date)
        to_date = datetime.combine(value.stop, datetime.min.time()) + timedelta(days=1)
        to_date = tz.localize(to_date)
        return queryset.filter(added_on__gte=from_date, added_on__lt=to_date)

    @property
    def qs(self):
        queryset = super().qs
        if 'date_range' in self.form.data:
            return self.filter_by_date_range(queryset, 'added_on', self.form.data['date_range'])
        return queryset

    class Meta:
        model = Patient
        fields = ['date', 'date_range', 'q', 'status_id']



class BulkMessagingHistoryFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(field_name='added_on', method='filter_by_date')
    date_range = django_filters.DateFromToRangeFilter(field_name='added_on', method='filter_by_date_range')

    def filter_by_date(self, queryset, name, value):
        start_date = datetime.combine(value, datetime.min.time())
        end_date = start_date + timedelta(days=1) - timedelta(seconds=1)  # Last second of the day
        return queryset.filter(added_on__range=(start_date, end_date))

    def filter_by_date_range(self, queryset, name, value):
        start_date = datetime.combine(value.start, datetime.min.time())
        end_date = datetime.combine(value.stop, datetime.max.time())
        return queryset.filter(added_on__range=(start_date, end_date))

    class Meta:
        model = BulkMessagingHistory
        fields = ['date', 'date_range', 'created_by','template','template__messaging_service_types']