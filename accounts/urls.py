from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LabExpensesViewSet, LabIncomesViewSet, LabExpenseTypeViewSet, LabPaidToTypeViewSet, \
    LabIncomeTypeViewSet, LabIncomeFromAccountViewSet

router = DefaultRouter()
router.register(r'lab_expenses', LabExpensesViewSet, basename='lab_expenses'),
router.register(r'lab_incomes', LabIncomesViewSet, basename='lab_incomes'),
router.register(r'lab_expense_types', LabExpenseTypeViewSet, basename='lab_expense_types'),
router.register(r'lab_paid_to_types', LabPaidToTypeViewSet, basename='lab_paid_to_types'),
router.register(r'lab_incomes_from_account', LabIncomeFromAccountViewSet, basename='lab_incomes_from_account'),
router.register(r'lab_income_types', LabIncomeTypeViewSet, basename='lab_income_types')

urlpatterns = [
    path('', include(router.urls)),
]