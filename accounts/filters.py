from datetime import datetime, timedelta
import django_filters
import pytz
from django_filters import rest_framework as filters
from django.utils import timezone
from django.utils.timezone import make_aware

from accounts.models import LabExpenses, LabIncomes


class LabExpensesFilter(django_filters.FilterSet):
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
        model = LabExpenses
        fields = ['date', 'date_range']



class LabIncomesFilter(django_filters.FilterSet):
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
        model = LabIncomes
        fields = ['date', 'date_range']