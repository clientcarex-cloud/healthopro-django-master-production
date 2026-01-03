from django.urls import path, include
from rest_framework.routers import DefaultRouter
from pro_pharmacy.views import CategoryViewSet, StorageConditionsViewSet, DosageViewSet, PharmaItemsViewSet, \
    PharmaStockViewSet, OrdersViewSet, ManufacturerViewSet, PharmaStockGetAPIView, GeneratePatientPharmacyBillingViewSet

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='categories')
router.register(r'storage_conditions', StorageConditionsViewSet, basename='storage_conditions')
router.register(r'dosages', DosageViewSet, basename='dosages')
router.register(r'pharma_items', PharmaItemsViewSet, basename='pharma_items')
router.register(r'pharma_stock', PharmaStockViewSet, basename='pharma_stock')
router.register(r'manufacturer', ManufacturerViewSet, basename='manufacturer')
router.register(r'print_patient_pharmacy_bill', GeneratePatientPharmacyBillingViewSet, basename='print_patient_pharmacy_bill')


urlpatterns = [
    path('', include(router.urls)),
    path('stock_list/', PharmaStockGetAPIView.as_view(), name='stock_list')
]
