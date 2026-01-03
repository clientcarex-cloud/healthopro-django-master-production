from django.urls import path
from rest_framework.routers import SimpleRouter, DefaultRouter

from healtho_pro_user.views.business_views import BusinessProfilesViewSet, BusinessTypeViewSet, \
    GetNearestView, BContactsViewset, BContactForViewset, BExecutiveViewset, BusinesstimingsViewset, \
    BusinessAddressesViewSet
from healtho_pro_user.views.pro_doctor_views import ProDoctorConsultationViewSet, ProdoctorAppointmentSlotViewSet
from healtho_pro_user.views.subscription_views import BusinessBillCalculationTypeViewSet, BusinessSubscriptionPlansViewSet, OverallBusinessSubscriptionStatusViewSet, \
    OverallBusinessSubscriptionPlansPurchasedViewSet
from healtho_pro_user.views.users_views import CreateUserView, ResendOTPView, CustomUserViewSet, \
    DirectOTPLoginView, ULoginSlidersViewSet, current_tenant_info, SetPasswordForUser, \
    SendOTPToResetPassword, GetDoctorsListApiView, UserLoginView
from rest_framework_simplejwt.views import TokenRefreshView
from healtho_pro_user.views.universal_views import UserTypeViewSet, CountryViewSet, StateViewSet, CityViewSet, \
    SupportInfoTutorialsListAPIView, HealthcareRegistryTypeAPIView, UniversalProDoctorSpecializationsViewSet, \
    ShiftViewSet, ConsultationViewSet, ProDoctorViewSet, ProDoctorProfessionalDetailsViewSet

router = DefaultRouter()
router.register(r'users', CustomUserViewSet, basename='users')
router.register(r'usertypes', UserTypeViewSet, basename='usertypes')
router.register(r'businessprofiles', BusinessProfilesViewSet, basename='businessprofiles')
router.register(r'business_timings', BusinesstimingsViewset, basename='business_timings')
router.register(r'business_executive', BExecutiveViewset, basename='business_executive')
router.register(r'business_contactfor', BContactForViewset, basename='business_contactfor')
router.register(r'business_contacts', BContactsViewset, basename='business_contacts')
router.register(r'businesstypes', BusinessTypeViewSet, basename='businesstypes')
router.register(r'business_addresses', BusinessAddressesViewSet, basename='business_addresses')
router.register(r'country', CountryViewSet, basename='country')
router.register(r'state', StateViewSet, basename='state')
router.register(r'city', CityViewSet, basename='city')
router.register(r'login_sliders', ULoginSlidersViewSet)
router.register(r'upro_doctor_specializations', UniversalProDoctorSpecializationsViewSet)


router.register(r'shift', ShiftViewSet, basename='shift')
router.register(r'consultation', ConsultationViewSet, basename='consultation')
router.register(r'pro_doctors', ProDoctorViewSet, basename='Pro_doctors')
router.register(r'pro_doctor_professional_details', ProDoctorProfessionalDetailsViewSet, basename='pro_doctor_professional_details')
router.register(r'pro_doctor_consultation', ProDoctorConsultationViewSet, basename='pro_doctor_consultation')
router.register(r'appointment_slots', ProdoctorAppointmentSlotViewSet, basename='appointment_slot')

router.register(r'business_bill_calc_type', BusinessBillCalculationTypeViewSet, basename='business_bill_calc_type')
router.register(r'business_subscription_plans', BusinessSubscriptionPlansViewSet, basename='business_subscription_plans')
router.register(r'overall_business_subscription_status', OverallBusinessSubscriptionStatusViewSet, basename='overall_business_subscription_status')
router.register(r'overall_business_subscription_plans', OverallBusinessSubscriptionPlansPurchasedViewSet, basename='overall_business_subscription_plans')

urlpatterns = [
    path('create/', CreateUserView.as_view(), name='create-user'),
    path('login/', DirectOTPLoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path('otp-login/', UserLoginView.as_view(), name='otp-login'),
    path('password_login/', UserLoginView.as_view(), name='password_login'),
    path('send_otp_to_set_password/', SendOTPToResetPassword.as_view(), name='send_otp_to_set_password'),
    path('set_password/', SetPasswordForUser.as_view(), name='set_password'),
    path('tenant-info/', current_tenant_info, name='current_tenant_info'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend-otp'),
    path('get-nearest/', GetNearestView.as_view(), name='get-nearest'),
    path('support_info_tutorials/', SupportInfoTutorialsListAPIView.as_view(), name='support_info_tutorials'),
    path('healthcare_registry_types/', HealthcareRegistryTypeAPIView.as_view(), name='healthcare_registry_types'),
    path('get_doctors/', GetDoctorsListApiView.as_view(), name='get_doctors'),

] + router.urls


