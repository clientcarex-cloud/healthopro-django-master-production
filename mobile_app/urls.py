from django.urls import path
from rest_framework.routers import DefaultRouter
from mobile_app.views import DoctorAPIView, HospitalListAPIView, QuickServicesViewSet, \
    MobileAppLabMenusViewSet, \
    DoctorLanguageSpokenAPIView, DoctorSpecializationsAPIView, \
    LaboratoryListAPIView, LabtestAPIView, ShiftAPIView, ConsultationAPIView, \
    MedicineCategoriesAPIView, PharmaItemsAPIView, \
    PharmaciesAPIView, MobileAppPatientViewSet, PatientRegistrationWithDoctorViewSet, \
    PatientMedicineOrderViewSet, DoctorAppointmentsListView, DeliveryModeView, \
    master_search, FrequentlyOrderedMedicinesView, NearbyDoctorsView, NearbyHospitalsView, \
    NearbyLaboratoriesView, NearbyPharmaciesView, LabGlobalPackagesAPIView, CategoryPharmaItemsViewSet, \
    DepartmentsListAPIView, CategoryViewSet, DoctorsByHospitalListAPIView, \
    PopularDoctorsInCityView

router = DefaultRouter()
router.register(r'quick_services', QuickServicesViewSet)
router.register(r'mobileappmenus', MobileAppLabMenusViewSet)
router.register('mobile_app_patient', MobileAppPatientViewSet)
router.register(r'patient_doctor_appointment', PatientRegistrationWithDoctorViewSet,basename='patient_doctor_appointment')
router.register(r'patient_medicine_order', PatientMedicineOrderViewSet,basename='patient_medicine_order')
router.register(r'category_pharma_items', CategoryPharmaItemsViewSet, basename='category_pharma_items')
router.register(r'medicine_categories', CategoryViewSet, basename='medicine_categories')


urlpatterns = [
    path('doctors/', PopularDoctorsInCityView.as_view(), name='doctors'),
    path('doctor_appointments_list/', DoctorAppointmentsListView.as_view(), name='doctor_appointments_list'),
    path('hospitals/', HospitalListAPIView.as_view(), name='hospital-list'),
    path('laboratories/', LaboratoryListAPIView.as_view(), name='laboratory-list'),
    path('pharmacies/', PharmaciesAPIView.as_view(), name='pharmacies'),
    path('lab_test/', LabtestAPIView.as_view(), name='lab_tests'),
    path('specializations/', DoctorSpecializationsAPIView.as_view(), name='specializations'),
    path('languages_spoken/', DoctorLanguageSpokenAPIView.as_view(), name='languages_spoken'),
    path('shift/', ShiftAPIView.as_view(), name='shift'),
    path('health_checkups/', LabGlobalPackagesAPIView.as_view(), name='health_checkups'),
    path('consultation/', ConsultationAPIView.as_view(), name='consultation'),
    path('medicines/', PharmaItemsAPIView.as_view(), name='medicines'),
    path('frequently_ordered_items/', FrequentlyOrderedMedicinesView.as_view(), name='frequently_ordered_items'),
    path('delivery_modes/', DeliveryModeView.as_view(), name='delivery_modes'),
    path('healtho_master_search/', master_search, name='healtho_master_search'),
    path('nearby_doctors/', NearbyDoctorsView.as_view(), name='nearby_doctors'),
    path('nearby_hospitals/', NearbyHospitalsView.as_view(), name='nearby_hospitals'),
    path('nearby_laboratories/', NearbyLaboratoriesView.as_view(), name='nearby_laboratories'),
    path('nearby_pharmacies/', NearbyPharmaciesView.as_view(), name='nearby_pharmacies'),
    path('departments_list/', DepartmentsListAPIView.as_view(), name='departments_list'),
    path('hospital_doctors/', DoctorsByHospitalListAPIView.as_view(), name='hospital_doctors')




] + router.urls
