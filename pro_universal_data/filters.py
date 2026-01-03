from datetime import datetime, timedelta
import django_filters
import pytz
from django.utils import timezone

from pro_universal_data.models import DoctorSharedReport


class DoctorSharedReportFilter(django_filters.FilterSet):
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
        model = DoctorSharedReport
        fields = ['date', 'date_range', 'doctor']
