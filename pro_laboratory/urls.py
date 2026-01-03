from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from pro_laboratory.views.b2b_views import CompanyViewSet, CompanyRevisedPricesViewSet, CompanyWorkPartnershipViewSet, \
    GetPatientsFromCompanyAPIView, GenerateCompanyInvoiceViewSet
from pro_laboratory.views.bulk_messaging_views import BulkSMSAPIView, BulkWhatsAppMessagingAPIView, \
    BulkMessagingTemplatesViewSet, BulkMessagingLogsViewSet, \
    BulkWhatsAppMessagingLogsViewSet, BulkBusinessMessagingStatisticsView, \
    BusinessMessagesCreditsView, SendAndLogCampaignMessagesView, BulkMessagingHistoryView
from pro_laboratory.views.client_based_settings_views import LetterHeadSettingsViewSet, CopiedLabDepartmentsDataView, \
    LabDepartmentsListToCopyView, BusinessDataStatusViewSet, BusinessDiscountSettingsViewset, \
    BusinessPaidAmountSettingsViewset, BusinessPNDTDetailsViewset, PrintReportSettingsViewSet, PrintDueReportsViewset, \
    PNDTRegistrationNumberViewset, BusinessMessageSettingsViewset, BusinessReferralDoctorSettingsViewset, \
    PrintTestReportSettingsViewSet, BusinessMessagingStatisticsView, BusinessWhatsappMessagingStatisticsView, \
    LabStaffPrintSettingsViewSet, ClientWiseMessagingTemplatesViewSet, \
    OtherBusinessSettingsSerializerViewset, BusinessEmailDetailsViewSet, CurrentTimingsAPIView, ReportFontSizesViewSet, \
    GenerateQuotationViewSet, PharmacyPricingConfigViewSet
from pro_laboratory.views.dashboard_views import DayWiseCollectionsAPIView, BusinessStatusAPIView, \
    DashBoardSettingsViewset, PatientOverviewListAPIView, ReferralDoctorDetailsAPIView, DepartmentAnalyticsAPIView, \
    PayModeAnalyticsListAPIView, LabPhlebotomistAnalyticsAPIView, LabTechnicianAnalyticsAPIView, TopTestDetailsAPIView, \
    PatientRegistrationOverviewAPIView, DoctorAuthorizationAnalyticsAPIView, PatientAnalyticsView
from pro_laboratory.views.doctors_views import LabDoctorsViewSet, LabDoctorsTypeViewSet, LabConsultingDoctorsListView, \
    LabReferralDoctorsListView, ConsultantDoctorsStatsListView, ReferralDoctorsStatsListView, \
    ReferralAmountForDoctorViewSet, SyncDataForReferralDoctorViewset, \
    ReferralDoctorsBulkEditViewSet, SearchForMatchingDoctors, PatientWiseLabReferralDoctorsListView, \
    DefaultsForDepartmentsViewSet, DoctorSpecializationsViewSet, ReferralDoctorsMergingViewSet, DoctorLoginAPIView
from pro_laboratory.views.global_views import LabGlobalTestsViewSet, LabDiscountTypeViewSet, \
    LabReportsTemplatesViewSet, LabWordReportTemplateViewSet, LabFixedParametersReportTemplateViewSet, \
    LabStaffAccessViewSet, LabMenuAccessViewSet, LabStaffRoleViewSet, \
    LabStaffRolePermissionsViewset, LabBranchViewSet, LabShiftViewSet, \
    LabStaffLoginActionViewSet, LabWorkingDaysViewSet, LabBloodGroupViewSet, \
    LabMaritalStatusViewSet, LabDoctorRoleViewSet, LabGlobalTestMethodologyViewSet, LabDepartmentsViewSet, \
    BodyPartsViewSet, LabGlobalPackagesListView, LabGlobalPackagesViewSet, DoctorAcessViewset, \
    SearchForHealthcareProfessional, UserCollectionsAPIView, DefaultTestParametersViewSet, \
    LabFixedReportNormalReferralRangesViewSet, LabStaffAttendanceDetailsViewSet, LabStaffAttendanceDetailsListView, \
    LabStaffPayRollViewSet, LabStaffJobDetailsViewSet, LabStaffLeaveRequestViewSet, LeavePolicyViewSet, \
    LabStaffPayRollAPIView, LeaveStatisticsAPIView, LabStaffDefaultBranchViewSet, LabStaffPageGuardView
from pro_laboratory.views.lab_appointment_of_patient_views import LabAppointmentForPatientViewset, \
    LabDoctorsAvailability, SendingAppointmentReminderSMSTOPatientsAPIView
from pro_laboratory.views.machine_integration_views import ProcessingMachineDataSavingView
from pro_laboratory.views.marketing_views import MarketingExecutiveLocationTrackerViewset, \
    MarketingExecutiveVisitsViewset, MarketingExecutiveVisitsByLabstaffView, MarketingExecutiveTargetsViewSet, \
    MarketingExecutiveTargetByLabstaffView, MarketingExecutiveStatsView, ReferralDoctorStatsAPIView
from pro_laboratory.views.messaging_views import MessagingLogsViewSet, SendAndSaveSMSDataViewset, \
    SendAndSaveWhatsAppSMSViewset

from pro_laboratory.views.nabl_views import LabNablReportListView
from pro_laboratory.views.patient_views import PatientViewSet, StandardViewPatientsListView, \
    LabPatientReceiptsListView, \
    LabPatientRefundViewSet, LabPatientInvoiceListAPIView, LabPatientRefundListAPIView, \
    LabPatientTestsViewSet, SendOTPforreportViewset, ResendOTPViewSet, \
    PatientMaxRefundLimitAPIView, NewTrailStandardViewPatientsListView, PaymentModePatientReportView
from pro_laboratory.views.phlebotomists_views import LabPhlebotomistListView, \
    LabPhlebotomistsViewSet, AllPatientsTestsView, PatientListView
from pro_laboratory.views.pndt_views import PatientPNDTViewSet, GeneratePatientPndtViewSet
from pro_laboratory.views.privilege_card_views import PrivilegeCardsViewset, PrivilegeCardMembershipViewset, \
    PrivilegeCardForViewSet, PrivilegeCardMembershipRenewalView, \
    PrivilegeCardUsageHistoryView, CalculatePrivilegeCardDiscountView
from pro_laboratory.views.sourcing_lab_views import AvailableSouringLabsListAPIView, SourcingLabRevisedTestPriceViewSet, \
    SourcingLabRegistrationViewSet, GetLabGlobalTestsOfSourcingLabView, \
    SourcingLabTestsTrackerViewset, GetAndCreatePatientForSourcingLab, GetPatientTestsStatusFromSourcingLab, \
    GetPrintOfLabPatientTests, CreateSourcedLabTestsView, SourcingLabPatientReportUploadsViewset, \
    CheckPaymentForReferralPatients, ReferralLabLoginActionView, GetSourcingLabFromLabStaff, \
    SyncRevisedPriceOfReferralLabsView, SourcingLabPaymentsViewSet, SourcingLabLetterHeadSettingsViewSet
from pro_laboratory.views.search_query_views import search_doctors, search_labTests, master_search, \
    master_search_for_tests
from pro_laboratory.views.subscription_data_views import BusinessSubscriptionPlansPurchasedCostCalculationAPIView, \
    BusinessSubscriptionPlansPurchasedView, GenerateBillForSubscriptionView, MarkPaymentDoneForSubscriptionView, \
    BusinessSubscriptionPlansPurchasedViewset
from pro_laboratory.views.universal_views import (
    GenerateBarcodePDFViewset, GeneratePatientInvoiceViewset,
    GenerateReceiptViewset, GenerateTestReportViewset,
    GeneratePatientReceiptViewSet, GeneratePatientTestReportViewset,
    TpaUltrasoundConfigViewset, TpaUltrasoundViewset,
    TpaUltrasoundIntegrationView, PrintReceptionistReportViewset,
    TpaUltrasoundImagesViewset, ReferralDoctorReportViewset,
    PrintTemplateViewset, PrintDataTemplateViewset,
    UserCollectionReportsList, TpaUltrasoundMetaInfoListView,
    DownloadTestReportViewset, ActivityLogsListView, GeneratePatientRefundViewset,
    DoctorSharedTestReportViewset, DownloadPatientReceiptViewset, GetPrivilegeCardView,
    GeneratePatientMedicalCertificateViewSet, BulkPaymentsWithGenerateReceiptView,
    ReplaceTemplateHeaderContent,
    DownloadBulkPatientsReportsViewSet, PatientsReportsSendingViaEmailAPIView,
    GenerateConsolidatedBillViewSet, TestCollectionReportView, StringToHTMLView
)
from pro_laboratory.views.doctorAuthorization_views import LabDoctorAuthorizationApprovalViewSet, \
    LabDoctorAuthorizationView
from pro_laboratory.views.global_views import LabStaffViewSet
from pro_laboratory.views.labtechnicians_views import (LabTechniciansViewSet, LabTechnicianRemarksViewSet,
                                                       LabPatientWordReportTemplateViewSet,
                                                       LabPatientFixedReportTemplateViewSet,
                                                       LabPatientFixedReportTemplateUpdateViewSet,
                                                       LabPatientTestFixedReportDeletionView, LabTechniciansListView,
                                                       LabPatientWordReportTemplateListViewSet,
                                                       LabPatientTestReportGenerationViewset,
                                                       SendTestReportInWhatsappView, PreviousVisitReportsAPIView
                                                       )
from pro_laboratory.views.managePayments_views import ManagePaymentListView
from pro_laboratory.views.user_permissions_views import UserPermissionsAccessViewset
from pro_universal_data.views import PrintTemplateTypeViewset


router = DefaultRouter()
router.register(r'labstaff', LabStaffViewSet, basename='labstaff')
router.register(r'lab_staff_default_branch', LabStaffDefaultBranchViewSet, basename='lab_staff_default_branch')

router.register(r'labdoctors', LabDoctorsViewSet, basename='labdoctors')
router.register(r'ref_amount_for_doctor', ReferralAmountForDoctorViewSet, basename='ref_amount_for_doctor')
router.register(r'patient', PatientViewSet)
router.register(r'lab_appointment_for_patient', LabAppointmentForPatientViewset, basename='lab_appointment_for_patient')
router.register(r'lab_departments', LabDepartmentsViewSet, basename='lab_departments')
router.register(r'defaults_for_departments', DefaultsForDepartmentsViewSet, basename='defaults_for_departments')
router.register(r'doctor_specializations', DoctorSpecializationsViewSet, basename='doctor_specializations')

router.register(r'lab_global_tests', LabGlobalTestsViewSet, basename='lab_global_tests')
router.register(r'lab_patient_tests', LabPatientTestsViewSet, basename='lab_patient_tests')
router.register(r'lab_doctor_authorization_approval', LabDoctorAuthorizationApprovalViewSet,
                basename='lab_doctor_authorization_approval')
router.register(r'lab_global_packages', LabGlobalPackagesViewSet, basename='lab_global_packages')
router.register(r'lab_reports_templates', LabReportsTemplatesViewSet, basename='lab_reports_templates')
router.register(r'lab_branches', LabBranchViewSet, basename='lab_branches')
router.register(r'lab_shifts', LabShiftViewSet, basename='lab_shifts')
router.register(r'lab_working_days', LabWorkingDaysViewSet, basename='lab_working_days')
router.register(r'lab_blood_group', LabBloodGroupViewSet, basename='lab_blood_group')
router.register(r'lab_marital_status', LabMaritalStatusViewSet, basename='lab_marital_status')
router.register(r'bodyparts', BodyPartsViewSet, basename='bodyparts')
router.register(r'lab_technicians', LabTechniciansViewSet, basename='lab_technicians')
router.register(r'lab_technician_remarks', LabTechnicianRemarksViewSet, basename='lab_technician_remarks')
router.register(r'lab_patient_word_report_templates', LabPatientWordReportTemplateViewSet,
                basename='lab_patient_word_report_templates')
router.register(r'lab_word_report_templates', LabWordReportTemplateViewSet, basename='lab_word_report_templates')
router.register(r'lab_fixed_parameters_report_templates', LabFixedParametersReportTemplateViewSet,
                basename='lab_fixed_parameters_report_templates')

router.register(r'lab_fixed_parameters_normal_ranges', LabFixedReportNormalReferralRangesViewSet,
                basename='lab_fixed_parameters_normal_ranges')


router.register(r'lab_patient_refunds', LabPatientRefundViewSet)
router.register(r'lab_discount_types', LabDiscountTypeViewSet, basename='lab_discount_types')
router.register(r'lab_global_test_methodology', LabGlobalTestMethodologyViewSet, basename='lab_global_test_methodology')
router.register(r'lab_phlebotomists', LabPhlebotomistsViewSet, basename='lab_phlebotomists')

# router.register(r'lab_patient_receipt_payments', LabPatientReceiptPaymentsViewSet)
router.register(r'labdoctors_types', LabDoctorsTypeViewSet)
router.register(r'generate_barcode_pdf', GenerateBarcodePDFViewset, basename='generate_barcode_pdf')
router.register(r'print_patient_invoice', GeneratePatientInvoiceViewset, basename='print_patient_invoice')
router.register(r'print_patient_refund', GeneratePatientRefundViewset, basename='print_patient_refund')
router.register(r'print_patient_receipt', GeneratePatientReceiptViewSet, basename='print_patient_receipt')
router.register(r'print_patient_consolidated_bill', GenerateConsolidatedBillViewSet, basename='print_patient_consolidated_bill')
router.register(r'print_patient_test_report', GeneratePatientTestReportViewset, basename='print_patient_test_report')

router.register(r'generate_receipt', GenerateReceiptViewset, basename='generate_receipt')
router.register(r'lab_staff_access', LabStaffAccessViewSet, basename='lab_staff_access')

router.register(r'lab_patient_report_generate', LabPatientTestReportGenerationViewset,
                basename='lab_patient_report_generate')

router.register(r'lab_fixed_patient_report_list', LabPatientFixedReportTemplateViewSet,
                basename='lab_fixed_patient_report_list')
router.register(r'lab_fixed_patient_report_update', LabPatientFixedReportTemplateUpdateViewSet,
                basename='lab_fixed_patient_report_update')


router.register(r'lab_word_patient_report_list', LabPatientWordReportTemplateListViewSet,
                basename='lab_word_patient_report_list')

router.register(r'print_test_report', GenerateTestReportViewset, 'print_test_report')
router.register(r'lab_staff_role', LabStaffRoleViewSet, 'lab_staff_role')
router.register(r'lab_doctor_role', LabDoctorRoleViewSet, 'lab_doctor_role')
router.register(r'lab_menu_access_for_staff', LabMenuAccessViewSet, 'lab_menu_access')
router.register(r'lab_staff_role_permissions', LabStaffRolePermissionsViewset, 'lab_staff_role_permissions')
router.register(r'lab_staff_login_access_action', LabStaffLoginActionViewSet, 'lab_staff_login_access_action')
router.register(r'tpa_ultrasound_config', TpaUltrasoundConfigViewset, 'tpa_ultrasound_config')
router.register(r'tpa_ultrasound_images', TpaUltrasoundImagesViewset, 'tpa_ultrasound_images')
router.register(r'tpa_ultrasound', TpaUltrasoundViewset, 'tpa_ultrasound')
router.register(r'print_receptionist_report', PrintReceptionistReportViewset, 'print_receptionist_report')
router.register(r'patient_pndt', PatientPNDTViewSet, basename='patient_pndt')
router.register(r'print_patient_pndt', GeneratePatientPndtViewSet, basename='print_patient_pndt')
router.register(r'referral_doctor_report', ReferralDoctorReportViewset, basename='referral_doctor_report')


router.register(r'sync_referral_doctor_data', SyncDataForReferralDoctorViewset, basename='sync_referral_doctor_data')
router.register(r'merging_referral_doctors', ReferralDoctorsMergingViewSet, basename='merging_referral_doctors')
router.register(r'print_template_types', PrintTemplateTypeViewset, basename='print_template_types')
router.register(r'print_templates', PrintTemplateViewset, basename='print_template')
router.register(r'print_data_templates', PrintDataTemplateViewset, basename='print_data_templates')
router.register(r'download_patient_receipt', DownloadPatientReceiptViewset, basename='download_patient_receipt')

router.register('download_test_report', DownloadTestReportViewset, basename='testing')
router.register('referral_doctor_bulk_edit', ReferralDoctorsBulkEditViewSet, basename='referral_doctor_bulk_edit')
router.register('otp_for_report', SendOTPforreportViewset, basename='otp_for_report')
router.register(r'resend_otp_for_report', ResendOTPViewSet, basename='resend_otp_for_report')

router.register(r'doctor_access', DoctorAcessViewset, basename='doctor_access')
router.register(r'print_doctor_shared_report', DoctorSharedTestReportViewset, basename='print_doctor_shared_report')

router.register(r'letterhead_settings', LetterHeadSettingsViewSet, basename='letterhead_settings')

router.register(r'business_data_status', BusinessDataStatusViewSet, basename='business_data_status')
router.register(r'copy_biz_data', CopiedLabDepartmentsDataView, basename='copy_biz_data')
router.register(r'user_permissions_access', UserPermissionsAccessViewset, basename='user_permissions_access')
router.register(r'business_discount_settings', BusinessDiscountSettingsViewset, basename='business_discount_settings')
router.register(r'business_paid_amount_settings', BusinessPaidAmountSettingsViewset,
                basename='business_paid_amount_settings')
router.register(r'business_pndt_details', BusinessPNDTDetailsViewset, basename='business_pndt_details')
router.register(r'print_test_report_settings', PrintTestReportSettingsViewSet, basename='print_test_report_settings')
router.register(r'print_report_settings', PrintReportSettingsViewSet, basename='print_report_settings')
router.register(r'business_print_due_reports', PrintDueReportsViewset, basename='business_print_due_reports')
router.register(r'pndt_reg_number', PNDTRegistrationNumberViewset, basename='pndt_reg_number')
router.register(r'business_message_settings', BusinessMessageSettingsViewset, basename='business_message_settings')
router.register(r'business_referral_doctor_settings', BusinessReferralDoctorSettingsViewset,
                basename='business_referral_doctor_settings')
router.register(r'lab_staff_print_settings', LabStaffPrintSettingsViewSet, basename='lab_staff_print_settings')
router.register(r'other_business_settings', OtherBusinessSettingsSerializerViewset, basename='other_business_settings')


router.register(r'privilege_cards', PrivilegeCardsViewset, basename='privilege_cards')
router.register(r'privilege_cards_for', PrivilegeCardForViewSet, basename='privilege_cards_for')
router.register(r'privilege_card_memberships', PrivilegeCardMembershipViewset, basename='privilege_card_memberships')


router.register(r'default_parameters', DefaultTestParametersViewSet, basename='default_parameters')
router.register(r'sourcing_lab_registration', SourcingLabRegistrationViewSet, basename='sourcing_lab_registration')
router.register(r'revised_test_price', SourcingLabRevisedTestPriceViewSet, basename='revised_test_price')
router.register(r'bulk_messaging_templates', BulkMessagingTemplatesViewSet, basename='bulk_messaging_templates')
router.register(r'bulk_sms_messaging_logs', BulkMessagingLogsViewSet, basename='bulk_sms_messaging_logs')
router.register(r'bulk_whatsapp_messaging_logs', BulkWhatsAppMessagingLogsViewSet, basename='bulk_whatsapp_messaging_logs')
router.register(r'print_medical_certificate', GeneratePatientMedicalCertificateViewSet, basename='print_medical_certificate')
router.register(r'update_business_subscription_plans', BusinessSubscriptionPlansPurchasedViewset, basename='update_business_subscription_plans')
router.register(r'sourcing_lab_test_tracker', SourcingLabTestsTrackerViewset, basename='sourcing_lab_test_tracker')
router.register(r'client_wise_templates', ClientWiseMessagingTemplatesViewSet, basename='client_wise_templates')
router.register(r'marketing_visits', MarketingExecutiveVisitsViewset, basename='marketing_visits')
router.register(r'marketing_executive_location', MarketingExecutiveLocationTrackerViewset, basename='marketing_executive_location')
router.register(r'lab_staff_attendance', LabStaffAttendanceDetailsViewSet, basename='lab_staff_attendance')
router.register(r'marketing_executive_targets', MarketingExecutiveTargetsViewSet, basename='marketing_executive_targets')
router.register(r'lab_staff_pay_roll', LabStaffPayRollViewSet, basename='lab_staff_pay_roll')
router.register(r'staff_job_details', LabStaffJobDetailsViewSet, basename='staff_job_details')
router.register(r'staff_leave_request', LabStaffLeaveRequestViewSet, basename='staff_leave_request')
router.register(r'leave_policy', LeavePolicyViewSet, basename='leave_policy')

router.register(r'messaging_logs', MessagingLogsViewSet, basename='messaging_logs')
router.register(r'send_and_save_sms', SendAndSaveSMSDataViewset, basename='send_and_save_sms')
router.register(r'send_and_save_whatsapp_sms', SendAndSaveWhatsAppSMSViewset, basename='send_and_save_whatsapp_sms')

router.register(r'company', CompanyViewSet, basename='company')
router.register(r'company_test_prices', CompanyRevisedPricesViewSet, basename='company_test_prices')
router.register(r'company_work_partnership', CompanyWorkPartnershipViewSet, basename='company_work_partnership')
router.register(r'print_company_invoice', GenerateCompanyInvoiceViewSet, basename='print_company_invoice')
router.register(r'sourcing_reports_upload', SourcingLabPatientReportUploadsViewset, basename='sourcing_reports_upload')
router.register(r'patients_reports_download', DownloadBulkPatientsReportsViewSet, basename='patients_reports_download')
router.register(r'client_email_details', BusinessEmailDetailsViewSet, basename='client_email_details')


router.register(r'sourcing_lab_payments', SourcingLabPaymentsViewSet, basename='sourcing_lab_payments')
router.register(r'sourcing_lab_letterheads', SourcingLabLetterHeadSettingsViewSet, basename='sourcing_lab_letterheads')
router.register(r'report_font_sizes', ReportFontSizesViewSet,basename='report_font_sizes')

router.register(r'pharmacy_pricing_configs', PharmacyPricingConfigViewSet, basename='pharmacy_pricing_configs')
#dashboard apis
router.register(r'dashboard_settings', DashBoardSettingsViewset, basename='dashboard_settings')
router.register(r'print_quotation', GenerateQuotationViewSet, basename='print_quotation')



urlpatterns = [
    path('', include(router.urls)),

    #dashboard apis
    path('daywise_collections/', DayWiseCollectionsAPIView.as_view(), name='daywise_collections'),
    path('business_status_analytics/', BusinessStatusAPIView.as_view(), name='lab-patient-invoice-analytics'),
    path('analytics_patient_overview/', PatientOverviewListAPIView.as_view(), name='patient_overview'),
    path('analytics_referral_doctor_details/', ReferralDoctorDetailsAPIView.as_view(), name='referral-doctor-details'),
    path('department_analytics/', DepartmentAnalyticsAPIView.as_view(), name='department_analytics'),
    path('paymode_analytics/', PayModeAnalyticsListAPIView.as_view(), name='patient-analytics-paymode'),
    path('phlebotomist_analytics/', LabPhlebotomistAnalyticsAPIView.as_view(), name='phlebotomist_analytics'),
    path('technicians_analytics/', LabTechnicianAnalyticsAPIView.as_view(), name='technicians_analytics'),
    path('analytics_top_tests/', TopTestDetailsAPIView.as_view(), name='top_tests'),
    path('patient_registration_overview/', PatientRegistrationOverviewAPIView.as_view(),
         name='patient_registration_overview'),
    path('doctor_authorization_analytics/', DoctorAuthorizationAnalyticsAPIView.as_view(),
         name='authorization_analytics'),
    path('patient_analytics/', PatientAnalyticsView.as_view(), name='patient-analytics'),


    # path('pdf/', my_pdf_view, name='my_pdf_view'),
    path('search_doctors/', search_doctors, name='search_doctors'),
    path('search_labtests/', search_labTests, name='search_labtests'),
    path('patients_standard_view/', StandardViewPatientsListView.as_view(), name='patient-lab-tests-list'),
    path('new_patients_standard_view/', NewTrailStandardViewPatientsListView.as_view(), name='new_patient-lab-tests-list'),

    path('master_search/', master_search, name='master_search'),
    path('tests_master_search/', master_search_for_tests, name='tests_master_search'),

    path('lab_staff_page_guard/', LabStaffPageGuardView.as_view(), name='lab_staff_page_guard'),

    path('manage_payments/', ManagePaymentListView.as_view(), name='manage_payments'),
    path('lab_phlebotomists_list/', LabPhlebotomistListView.as_view(), name='lab_phlebotomists'),
    path('lab_technicians_list/', LabTechniciansListView.as_view(), name='lab_technicians_list'),
    path('lab_nabl/', LabNablReportListView.as_view(), name='lab_nabl'),
    path('lab_doctor_authorization/', LabDoctorAuthorizationView.as_view(), name='lab_doctor_authorization'),
    path('lab_patient_receipts/', LabPatientReceiptsListView.as_view(), name='lab_patient_receipts-list'),
    path('lab_patient_get_refund/', LabPatientRefundListAPIView.as_view(), name='lab_patient_get_refund-list'),
    path('lab_patient_get_invoice/', LabPatientInvoiceListAPIView.as_view(), name='lab_patient_get_invoice_list'),
    path('lab_patient_test_fixed_report_delete', LabPatientTestFixedReportDeletionView.as_view(),
         name='lab_patient_test_fixed_report_delete'),

    path('lab_get_packages/', LabGlobalPackagesListView.as_view(), name='lab_packages_get_list'),
    path('lab_get_consulting_doctors/', LabConsultingDoctorsListView.as_view(), name='lab-get-consulting_doctors-list'),
    path('lab_get_referral_doctors/', LabReferralDoctorsListView.as_view(), name='lab-get-referral_doctors-list'),
    path('patient_wise_doctors/', PatientWiseLabReferralDoctorsListView.as_view(),
         name='lab_get_doctors-list'),
    path('lab_consultant_doctor_stats/', ConsultantDoctorsStatsListView.as_view(), name='lab_consultant_doctor_stats'),
    path('lab_referral_doctor_stats/', ReferralDoctorsStatsListView.as_view(), name='lab_referral_doctor_stats'),
    path('tpa_ultrasound_integration/', TpaUltrasoundIntegrationView.as_view(), name='tpa_ultrasound_integration'),
    path('tpa_meta_info/', TpaUltrasoundMetaInfoListView.as_view(), name='tpa_meta_info'),
    path('tpa_machine_integration/', ProcessingMachineDataSavingView.as_view(), name='tpa_machine_integration'),


    path('test_collection_report/', TestCollectionReportView.as_view(), name='test_collection_report'),
    path('user_collection_reports_list/', UserCollectionReportsList.as_view(), name='user_collection_reports_list'),
    path('activity_logs/', ActivityLogsListView.as_view(), name='activity_logs'),
    path('lab_departments_list_to_copy/', LabDepartmentsListToCopyView.as_view(), name='lab_departments_list_to_copy'),
    path('patient_max_refund_limit/', PatientMaxRefundLimitAPIView.as_view(), name='patient_max_refund_view'),
    path('lab_departments_list_to_copy/', LabDepartmentsListToCopyView.as_view(), name='lab_departments_list_to_copy'),
    path('business_subscription_plans_purchased/', BusinessSubscriptionPlansPurchasedView.as_view(),
         name='business_subscription_plans_purchased'),
    path('business_plan_calculation/', BusinessSubscriptionPlansPurchasedCostCalculationAPIView.as_view(),
         name='business_plan_calculation'),
    path('generate_bill_for_subscription/', GenerateBillForSubscriptionView.as_view(),
         name='generate_bill_for_subscription'),
    path('mark_payment_done_for_subscription/', MarkPaymentDoneForSubscriptionView.as_view(),
         name='mark_payment_done_for_subscription'),
    path('search_for_matching_doctors/', SearchForMatchingDoctors.as_view(), name='search_for_matching_doctors'),
    path('search_for_healthcare_professionals/', SearchForHealthcareProfessional.as_view(),
         name='search_for_healthcare_professionals'),
    path('user_collections/', UserCollectionsAPIView.as_view(), name='user_collections'),
    path('send_test_report_whatsapp/', SendTestReportInWhatsappView.as_view(), name='send_test_report_whatsapp'),

    path('business_messaging_stats/', BusinessMessagingStatisticsView.as_view(), name='business_messaging_stats'),
    path('business_whatsapp_stats/', BusinessWhatsappMessagingStatisticsView.as_view(), name='business_whatsapp_stats'),

    #privilege card
    path('privilege_card_renewal/', PrivilegeCardMembershipRenewalView.as_view(), name='privilege_card_renewal'),
    path('privilege_usage_history/', PrivilegeCardUsageHistoryView.as_view(), name='privilege_usage_history'),

    path('bulk_campaign_for_recipients/', SendAndLogCampaignMessagesView.as_view(), name='bulk_campaign_for_recipients'),
    path('campaign_history/', BulkMessagingHistoryView.as_view(), name='campaign_history'),




    path('get_privilege_card/', GetPrivilegeCardView.as_view(), name='get_privilege_card'),
    path('calculate_privilege_card_discount/', CalculatePrivilegeCardDiscountView.as_view(),
         name='calculate_privilege_card_discount/'),

    path('replace_header_content/', ReplaceTemplateHeaderContent.as_view(), name='replace_header_content/'),



    path('bulk_sms/', BulkSMSAPIView.as_view(), name='bulk_sms'),
    path('bulk_whatsapp_messaging/', BulkWhatsAppMessagingAPIView.as_view(), name='bulk_whatsapp_messaging'),
    path('bulk_messaging_stats/', BulkBusinessMessagingStatisticsView.as_view(), name='business_whatsapp_stats'),
    path('bulk_messaging_history/', BusinessMessagesCreditsView.as_view(), name='bulk_messaging_stats'),
    path('lab_doctors_availability/', LabDoctorsAvailability.as_view(), name='lab_doctors_availability'),
    path('sourcing_labs_list/', AvailableSouringLabsListAPIView.as_view(), name='sourcing_labs_list'),
    path('get_sourcing_lab_tests_master/', GetLabGlobalTestsOfSourcingLabView.as_view(), name='get_sourcing_lab_tests_master'),
    path('get_and_create_patient_for_lab/', GetAndCreatePatientForSourcingLab.as_view(), name='get_and_create_patient_for_lab'),
    path('get_patient_tests_status_from_lab/', GetPatientTestsStatusFromSourcingLab.as_view(({'get': 'list'})), name='get_patient_tests_status_from_lab'),
    path('get_print_of_lab_patient_tests/', GetPrintOfLabPatientTests.as_view(), name='get_print_of_lab_patient_tests'),
    path('create_sourcing_lab_tests/', CreateSourcedLabTestsView.as_view(), name='create_sourcing_lab_tests'),
    path('bulk_payments_for_sourcing/', BulkPaymentsWithGenerateReceiptView.as_view(), name='bulk_payments_for_sourcing'),
    path('referral_lab_login_access/', ReferralLabLoginActionView.as_view(), name='referral_lab_login_access'),
    path('get_sourcing_lab_from_lab_staff/', GetSourcingLabFromLabStaff.as_view(), name='get_sourcing_lab_from_lab_staff'),
    path('sync_revised_price_for_ref_labs/', SyncRevisedPriceOfReferralLabsView.as_view(), name='sync_revised_price_for_ref_labs'),



    path('marketing_visits_by_lab_staff/', MarketingExecutiveVisitsByLabstaffView.as_view(), name='marketing_visits_by_lab_staff'),
    path('attendance_details/', LabStaffAttendanceDetailsListView.as_view(), name='attendance_details'),
    path('marketing_targets_by_lab_staff/', MarketingExecutiveTargetByLabstaffView.as_view(), name='marketing_targets_by_lab_staff'),
    path('lab_staff_payroll_details/', LabStaffPayRollAPIView.as_view(), name='lab_staff_payroll_details'),
    path('leaves_stats/', LeaveStatisticsAPIView.as_view(), name='leaves_stats'),

    path('test_details/', AllPatientsTestsView.as_view(), name='test_details'),
    path('executive_stats/', MarketingExecutiveStatsView.as_view(), name='executive_stats'),
    path('executive_ref_doctors_stats/', ReferralDoctorStatsAPIView.as_view(), name='executive_ref_doctors_stats'),

    path('get_patients_from_company/', GetPatientsFromCompanyAPIView.as_view(), name='get_patients_from_company'),
    path('check_payment_for_referrals/', CheckPaymentForReferralPatients.as_view(), name='check_payment_for_referrals'),
    path('sending_patients_reports_via_email/', PatientsReportsSendingViaEmailAPIView.as_view(), name='sending_patients_reports_via_email'),
    path('phlebotomists_list/', PatientListView.as_view(), name='phlebotomists_list'),
    path('send_appointment_reminder_sms/', SendingAppointmentReminderSMSTOPatientsAPIView.as_view(), name='send_appointment_reminder_sms'),
    path('print_past_reports/', PreviousVisitReportsAPIView.as_view(), name='print_past_reports'),
    path('get_current_timings/', CurrentTimingsAPIView.as_view(), name='get_current_timings'),
    path('string_to_html/', StringToHTMLView.as_view(), name='string_to_html'),
    path('doctor_login/', DoctorLoginAPIView.as_view(), name='doctor_login'),
    path('paymode_collections/', PaymentModePatientReportView.as_view(), name='paymode_collections')

]


urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
