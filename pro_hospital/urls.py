from django.urls import path, include
from rest_framework.routers import DefaultRouter
from pro_hospital.views.patient_wise_views import PatientServicesViewSet, PatientDoctorConsultationDetailsViewSet, \
    IPRoomBookingViewSet, PatientVitalsViewSet
from pro_hospital.views.prescription_views import PatientPrescriptionViewSet, GeneratePatientPrescriptionViewSet, \
    GetPatientPrescriptionsListAPIView
from pro_hospital.views.universal_views import CaseTypeViewSet, GlobalServicesViewSet, RoomTypeViewSet, FloorViewSet, \
    GlobalRoomViewSet, DoctorConsultationDetailsViewSet, GlobalPackagesViewSet, master_search_for_entities

router = DefaultRouter()
router.register(r'doctor_consultation_details', DoctorConsultationDetailsViewSet, basename='doctor_consultation_details')
router.register(r'case_type', CaseTypeViewSet, basename='case_type')
router.register(r'global_services', GlobalServicesViewSet, basename='global_services')
router.register(r'patient_services', PatientServicesViewSet, basename='patient_services')
router.register(r'patient_consultations', PatientDoctorConsultationDetailsViewSet, basename='patient_consultations')
router.register(r'patient_vitals', PatientVitalsViewSet, basename='patient_vitals')


router.register(r'room_type', RoomTypeViewSet, basename='room_type')
router.register(r'floor', FloorViewSet, basename='floor')
router.register(r'global_room', GlobalRoomViewSet, basename='global_room')
router.register(r'global_package', GlobalPackagesViewSet, basename='global_package')
router.register(r'patient_room_booking', IPRoomBookingViewSet, basename='patient_room_booking')
router.register(r'patient_prescription', PatientPrescriptionViewSet, basename='patient_prescription')
router.register(r'print_patient_prescription', GeneratePatientPrescriptionViewSet, basename='print_patient_prescription')




urlpatterns = [
    path('', include(router.urls)),
    path('ip_master_search/', master_search_for_entities, name='ip_master_search'),
    path('get_prescription_patients/', GetPatientPrescriptionsListAPIView.as_view(), name='get_prescription_patients')

]