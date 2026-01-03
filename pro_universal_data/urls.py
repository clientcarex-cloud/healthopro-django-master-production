from django.urls import path, include
from rest_framework.routers import DefaultRouter

from pro_universal_data.views import ULabMenusListView, ULabPatientTitlesViewSet, \
    ULabPatientAttenderTitlesViewSet, ULabPatientActionViewSet, ULabReportTypeListView, \
    ULabTestStatusViewSet, ULabPaymentModeTypeViewSet, ULabPatientAgeViewset, \
    ULabStaffGenderViewSet, ULabPatientGenderViewSet, \
    PrintTemplateTypeViewset, TemplateTagsListAPIView, DashBoardOptionsViewset, DoctorSharedReportViewset, \
    DepartmentFlowTypeViewset, UserPermissionsViewset, TimeDurationTypesViewset, \
    ULabRelationsViewset, ULabFontsViewset, ULabReportsGenderViewSet, MarketingVisitTypesViewset, \
    UniversalFuelTypesViewset, UniversalVehicleTypesViewset, UniversalBloodGroupsViewset, UniversalMaritalStatusViewset, \
    LabEmploymentTypeViewSet, MarketingVisitStatusViewset, MarketingTargetTypesViewSet, MarketingTargetDurationsViewSet, \
    LabStaffAttendanceStatusViewSet, MarketingPaymentTypeViewSet, SalaryPaymentModesViewSet, LeaveStatusViewSet, \
    LeaveTypesViewSet, UniversalActionTypeViewset, PrivilegeCardBenefitsViewset, AvailabilityPeriodViewset, \
    ConsultationTypeViewSet, TimeCategoryViewSet, SourcingLabTypeViewSet, DoctorSalaryPaymentTypesViewSet, \
    DoctorTransactionTypesViewSet, TaxTypeViewSet, PharmaItemOperationTypeViewSet, SupplierTypeViewSet, \
    UniversalFoodIntakeViewSet, UniversalDayTimePeriodViewSet, UniversalAilmentsViewSet, PatientTypeViewSet

router = DefaultRouter()
router.register(r'lab_gender', ULabPatientGenderViewSet, basename='lab_gender')
router.register(r'lab_staff_gender', ULabStaffGenderViewSet, basename='lab_staff_gender')
router.register(r'lab_reports_gender', ULabReportsGenderViewSet, basename='lab_reports_gender')
router.register(r'lab_patient_titles', ULabPatientTitlesViewSet, basename='lab_patient_titles')
router.register(r'lab_patient_attender_titles', ULabPatientAttenderTitlesViewSet, basename='lab_patient_attender_title')
router.register(r'ulab_patient_action', ULabPatientActionViewSet, basename='ulab_patient_action')
router.register(r'lab_tests_status', ULabTestStatusViewSet)
router.register(r'ulab_payment_mode_types', ULabPaymentModeTypeViewSet, basename='ulab-payment-mode-types')
router.register(r'ulab_patient_ages', ULabPatientAgeViewset)
router.register(r'print_template_types', PrintTemplateTypeViewset, basename='print_template_types')
router.register('dashboard_options', DashBoardOptionsViewset, basename='dashboard_options')
router.register(r'doctor_reports', DoctorSharedReportViewset, basename='doctor_reports')
router.register(r'department_flow_type', DepartmentFlowTypeViewset, basename='department_flow_type')
router.register(r'user_permissions', UserPermissionsViewset, basename='user_permissions')
router.register(r'item_operation_type', PharmaItemOperationTypeViewSet, basename='item_operation_type')



router.register(r'consultation_type', ConsultationTypeViewSet, basename='consultation_type')

router.register(r'sourcing_type', SourcingLabTypeViewSet, basename='sourcing_type')



router.register(r'privilege_card_benefits', PrivilegeCardBenefitsViewset, basename='privilege_card_benefits')
router.register(r'availability_period', AvailabilityPeriodViewset, basename='availability_period')


router.register(r'time_duration_types', TimeDurationTypesViewset, basename='time_duration_types')
router.register(r'relations', ULabRelationsViewset, basename='relations')
router.register(r'lab_fonts', ULabFontsViewset, basename='lab_fonts')
router.register(r'vehicle_types', UniversalVehicleTypesViewset, basename='vehicle_types')
router.register(r'fuel_types', UniversalFuelTypesViewset, basename='fuel_types')
router.register(r'marketing_visit_types', MarketingVisitTypesViewset, basename='marketing_visit_types')
router.register(r'marketing_visit_status', MarketingVisitStatusViewset, basename='marketing_visit_status')
router.register(r'blood_groups', UniversalBloodGroupsViewset, basename='blood_groups')
router.register(r'marital_status', UniversalMaritalStatusViewset, basename='marital_status')
router.register(r'lab_employment_types', LabEmploymentTypeViewSet, basename='lab_employment_types')
router.register(r'marketing_target_types', MarketingTargetTypesViewSet, basename='marketing_target_types')
router.register(r'marketing_target_durations', MarketingTargetDurationsViewSet, basename='marketing_target_durations')
router.register(r'lab_staff_attendance_status', LabStaffAttendanceStatusViewSet, basename='lab_staff_attendance_status')
router.register(r'marketing_payment_types', MarketingPaymentTypeViewSet, basename='marketing_payment_types')
router.register(r'salary_payment_modes', SalaryPaymentModesViewSet, basename='salary_payment_modes')
router.register(r'leave_status', LeaveStatusViewSet, basename='leave_status')
router.register(r'leave_types', LeaveTypesViewSet, basename='leave_types')
router.register(r'action_types', UniversalActionTypeViewset, basename='action_types')
router.register(r'time_category', TimeCategoryViewSet, basename='time_category')
router.register(r'doctor_salary_payment_types', DoctorSalaryPaymentTypesViewSet, basename='doctor_salary_payment_types')
router.register(r'doctor_transaction_types', DoctorTransactionTypesViewSet, basename='doctor_transaction_types')
# router.register(r'pharma_item_flow_types', PharmaItemFlowTypeViewSet, basename='pharma_item_flow_types')
router.register(r'tax_types', TaxTypeViewSet, basename='tax_types')
router.register(r'supplier_type', SupplierTypeViewSet, basename='supplier_type')
router.register(r'ailments', UniversalAilmentsViewSet, basename='ailments')
router.register(r'day_time_periods', UniversalDayTimePeriodViewSet, basename='day_time_periods')
router.register(r'food_in_take_time', UniversalFoodIntakeViewSet, basename='food_in_take_time')
router.register(r'patient_type', PatientTypeViewSet, basename='patient_type')



urlpatterns = [
    path('', include(router.urls)),
    path('lab_menus_list/', ULabMenusListView.as_view(), name='lab_menus_list'),
    path('lab_report_types/', ULabReportTypeListView.as_view(), name='lab_report_types'),
    path('get_template_tags/', TemplateTagsListAPIView.as_view(), name='get_template_tags'),

]

# Third_party apis
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from pro_universal_data.views import (MessagingServiceTypesViewSet, MessagingVendorsViewSet, MessagingSendTypeViewSet,
                                      MessagingCategoryViewSet, MessagingTemplatesViewSet,
                                      MessagingForViewSet,
                                      TagsViewSet,
                                      InitiatePaymentViewset,
                                      payment_callback,
                                      )

router = DefaultRouter()
router.register(r'messaging_service_types', MessagingServiceTypesViewSet)
router.register(r'messaging_vendors', MessagingVendorsViewSet)
router.register(r'messaging_send_type', MessagingSendTypeViewSet)

router.register(r'messaging_category', MessagingCategoryViewSet)
router.register(r'messaging_templates', MessagingTemplatesViewSet)
router.register(r'messaging_for', MessagingForViewSet)
router.register(r'create_tags', TagsViewSet)
router.register(r'initiate_payment', InitiatePaymentViewset, basename='initiate_payment')
urlpatterns += [
    path('', include(router.urls)),
    path('payment_callback/', payment_callback, name='payment_callback')



]



