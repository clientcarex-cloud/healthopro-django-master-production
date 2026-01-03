from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from super_admin.views import SuperAdminLoginView, HealthOProSuperAdminViewset, DirectOTPLoginViewForAdmin, \
    ResendOTPViewForAdmin, BusinessProfilesViewSet, BusinessLoginAccessControl, GlobalMessagingSettingsViewset, \
    GlobalBusinessSettingsViewset, BusinessMessagesCreditsAdditionView, BusinessModulesMappingView, \
    ULabMenusListViewset, BusinessBillCalculationTypeViewSet, \
    BusinessSubscriptionTypeViewSet, BusinessSubscriptionPlansViewSet, BusinessSubscriptionPlansPurchasedViewset, \
    OverallBusinessSubscriptionStatusViewSet, WhatsappConfigurationsViewSet, BusinessControlsViewSet, \
    DeleteBusinessAccountsView

router = DefaultRouter()

router.register(r'admin', HealthOProSuperAdminViewset, basename='admin')
router.register(r'businessprofiles', BusinessProfilesViewSet, basename='businessprofiles')
router.register(r'global_messaging_settings', GlobalMessagingSettingsViewset, basename='global_messaging_settings')
router.register(r'global_business_settings', GlobalBusinessSettingsViewset, basename='global_business_settings')
router.register(r'business_modules', BusinessModulesMappingView, basename='business_modules')
router.register(r'lab_menus_list', ULabMenusListViewset, basename='lab_menus_list')
router.register(r'business_bill_calc_type', BusinessBillCalculationTypeViewSet, basename='business_bill_calc_type')
router.register(r'business_subscription_type', BusinessSubscriptionTypeViewSet, basename='business_subscription_type')
router.register(r'business_subscription_plans', BusinessSubscriptionPlansViewSet, basename='business_subscription_plans')
router.register(r'business_plans_purchased', BusinessSubscriptionPlansPurchasedViewset, basename='business_plans_purchased')
router.register(r'business_subscription_status', OverallBusinessSubscriptionStatusViewSet, basename='business_subscription_status')
router.register(r'business_whatsapp_configuration', WhatsappConfigurationsViewSet, basename='business_whatsapp_configuration')
router.register(r'business_controls', BusinessControlsViewSet, basename='business_controls')


urlpatterns = [
    path('', include(router.urls)),
    path('admin_login/', SuperAdminLoginView.as_view(), name='admin_login'),
    path('otp_for_admin/', DirectOTPLoginViewForAdmin.as_view(), name='otp_for_admin'),
    path('resend_otp_for_admin/', ResendOTPViewForAdmin.as_view(), name='resend_otp_for_admin'),
    path('business_login_access_control/', BusinessLoginAccessControl.as_view(), name='business_login_access_control'),
    path('add_message_credits/', BusinessMessagesCreditsAdditionView.as_view(), name='add_message_credits'),
    path('delete_business_account/', DeleteBusinessAccountsView.as_view(), name='delete_business_account')

]
