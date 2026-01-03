from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

from .filters import LabExpensesFilter, LabIncomesFilter
from .models import LabExpenses, LabIncomes, LabExpenseType, LabPaidToType, LabIncomeFromAccount, \
    LabIncomeType
from .serializers import LabExpensesSerializer, LabIncomesSerializer, LabExpenseTypeSerializer, LabPaidToTypeSerializer, \
    LabIncomeTypeSerializer, LabIncomeFromAccountSerializer


class LabExpensesViewSet(viewsets.ModelViewSet):
    serializer_class = LabExpensesSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = LabExpensesFilter

    def get_queryset(self):
        queryset = LabExpenses.objects.all()
        query = self.request.query_params.get('q', None)
        sort = self.request.query_params.get('sort', None)
        labstaff = self.request.query_params.get('labstaff', None)

        if query is not None:
            search_query = (Q(pay_mode__name__icontains=query) | Q(expense_type__name__icontains=query) | Q(
                description__icontains=query) | Q(authorized_by__name__icontains=query))
            queryset = queryset.filter(search_query)
        if labstaff is not None:
            staff_query = (Q(authorized_by__id__icontains=labstaff))
            queryset = queryset.filter(staff_query)

        if sort == '-added_on':
            queryset = queryset.order_by('-added_on')
        if sort == 'added_on':
            queryset = queryset.order_by('added_on')

        return queryset


class LabIncomesViewSet(viewsets.ModelViewSet):
    serializer_class = LabIncomesSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = LabIncomesFilter

    def get_queryset(self):
        queryset = LabIncomes.objects.all()
        query = self.request.query_params.get('q', None)
        sort = self.request.query_params.get('sort', None)
        if query is not None:
            search_query = (Q(pay_mode__name__icontains=query) | Q(income_type__name__icontains=query) | Q(
                description__icontains=query) | Q(authorized_by__name__icontains=query))
            queryset = queryset.filter(search_query)
        if sort == '-added_on':
            queryset = queryset.order_by('-added_on')
        if sort == 'added_on':
            queryset = queryset.order_by('added_on')

        return queryset


class LabExpenseTypeViewSet(viewsets.ModelViewSet):
    queryset = LabExpenseType.objects.all()
    serializer_class = LabExpenseTypeSerializer


class LabPaidToTypeViewSet(viewsets.ModelViewSet):
    queryset = LabPaidToType.objects.all()
    serializer_class = LabPaidToTypeSerializer


# class LabPayModeTypeViewSet(viewsets.ModelViewSet):
#     queryset = LabPayModeType.objects.all()
#     serializer_class = LabPayModeTypeSerializer


class LabIncomeFromAccountViewSet(viewsets.ModelViewSet):
    queryset = LabIncomeFromAccount.objects.all()
    serializer_class = LabIncomeFromAccountSerializer


class LabIncomeTypeViewSet(viewsets.ModelViewSet):
    queryset = LabIncomeType.objects.all()
    serializer_class = LabIncomeTypeSerializer
