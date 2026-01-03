import logging
from datetime import timedelta, datetime

from django.core.cache import cache
from django.db import transaction
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django_tenants.utils import schema_context
from rest_framework.response import Response

from healtho_pro_user.models.business_models import BusinessProfiles, GlobalBusinessSettings, BusinessModules
from healtho_pro_user.models.subscription_models import OverallBusinessSubscriptionStatus, \
    OverallBusinessSubscriptionPlansPurchased, BusinessBillCalculationType, BusinessSubscriptionPlans
from healtho_pro_user.models.users_models import HealthOProUser, Client, UserTenant
from pro_laboratory.models.client_based_settings_models import LetterHeadSettings, BusinessDataStatus, \
    PrintReportSettings, BusinessDiscountSettings, BusinessPaidAmountSettings, PrintDueReports, BusinessMessageSettings, \
    PrintTestReportSettings
from pro_laboratory.models.doctorAuthorization_models import LabDrAuthorization, LabDrAuthorizationRemarks
from pro_laboratory.models.global_models import LabReportsTemplates, LabStaff, LabStaffLoginAccess, LabGlobalTests, \
    LabFixedParametersReportTemplate, LabWordReportTemplate
from pro_laboratory.models.labtechnicians_models import LabTechnicians, LabTechnicianRemarks, \
    LabPatientWordReportTemplate, LabPatientFixedReportTemplate
from pro_laboratory.models.marketing_models import MarketingExecutiveVisits, MarketingExecutiveLocationTracker
from pro_laboratory.models.patient_models import Patient, LabPatientInvoice, LabPatientReceipts, LabPatientTests, \
    LabPatientPackages, LabPatientRefund
from pro_laboratory.models.phlebotomists_models import LabPhlebotomist
from pro_laboratory.models.subscription_data_models import BusinessSubscriptionPlansPurchased
from pro_laboratory.models.universal_models import ActivityLogs
from pro_laboratory.views.client_based_settings_views import get_default_letterhead_settings
from pro_universal_data.models import MessagingVendors, UniversalActionType, MessagingTemplates, MessagingSendType, \
    ULabFonts
from pro_universal_data.views import send_and_log_sms, send_and_log_whatsapp_sms

# Setup a logger for this module
logger = logging.getLogger(__name__)


@receiver(post_save, sender=BusinessProfiles)
def creating_data_in_new_b_id(sender, instance, created, **kwargs):
    if created:
        try:
            client = Client.objects.filter(name=instance.organization_name).first()

            with schema_context(client.schema_name):
                business_data_status = BusinessDataStatus.objects.create(
                    b_id=instance, client=client, is_data_imported=False)

                defaults = get_default_letterhead_settings()
                default_letterhead_settings = defaults.get('letterhead_settings')
                default_print_report_settings = defaults.get('print_report_settings')

                if default_letterhead_settings:
                    letterhead = LetterHeadSettings.objects.create(
                        client=client,
                        header_height=default_letterhead_settings['header_height'],
                        footer_height=default_letterhead_settings['footer_height'],
                        display_letterhead=default_letterhead_settings['display_letterhead'],
                        margin_left=default_letterhead_settings['margin_left'],
                        margin_right=default_letterhead_settings['margin_right'],
                        invoice_space=default_letterhead_settings['invoice_space'],
                        receipt_space=default_letterhead_settings['receipt_space'],
                        display_page_no=default_letterhead_settings['display_page_no'],
                        default_font=ULabFonts.objects.get(pk=default_letterhead_settings['default_font'])
                    )
                else:
                    letterhead = LetterHeadSettings.objects.create(
                        client=client, header_height=100, footer_height=100, margin_left=15, margin_right=15,
                        default_font=ULabFonts.objects.get(pk=3),
                        display_letterhead=True)

                if default_print_report_settings:
                    print_report_settings = PrintReportSettings.objects.create(
                        barcode_height=default_print_report_settings['barcode_height'],
                        barcode_width=default_print_report_settings['barcode_height'],
                        qr_code_size=default_print_report_settings['qr_code_size'],
                        test_barcode_height=default_print_report_settings['test_barcode_height'],
                        test_barcode_width=default_print_report_settings['test_barcode_width'])

                else:
                    print_report_settings = PrintReportSettings.objects.create(
                        barcode_height=30, barcode_width=150, qr_code_size=75, test_barcode_height=30,
                        test_barcode_width=150
                    )

                test_report_settings = PrintTestReportSettings.objects.create(client=client)

                minimum_discount = BusinessDiscountSettings.objects.create(number=100)

                minimum_paid_amount = BusinessPaidAmountSettings.objects.create(number=0)

                print_due_reports = PrintDueReports.objects.create(is_active=True)

                message_settings = BusinessMessageSettings.objects.create(client=client,
                                                                          whatsapp_vendor=MessagingVendors.objects.get(
                                                                              name='Meta WhatsApp'),
                                                                          send_reports_by=UniversalActionType.objects.get(
                                                                              name='Automatic')
                                                                          )

                global_business_settings = GlobalBusinessSettings.objects.create(business=instance)

                business_modules = BusinessModules.objects.create(business=instance)

                #new business subscriptions
                calc_type = BusinessBillCalculationType.objects.filter(subscription_type__name='Trail',
                                                                       is_default=True).first()

                plan = BusinessSubscriptionPlans.objects.filter(subscription_type__name='Trail',
                                                                is_default_plan=True).first()

                if plan is None:
                    plan = BusinessSubscriptionPlans.objects.filter(subscription_type__name='Trail').first()

                business_modules.modules.set(plan.modules.all())
                business_modules.save()

                sub_plan = BusinessSubscriptionPlansPurchased.objects.create(
                    b_id=instance,
                    plan_name=plan.name,
                    no_of_days=plan.plan_validity_in_days,
                    plan_start_date=datetime.now(),
                    plan_end_date=datetime.now() + timedelta(days=plan.plan_validity_in_days),
                    amount_per_patient=calc_type.amount_per_patient,
                    is_amount_percentage=calc_type.is_amount_percentage,
                    is_prepaid=calc_type.is_prepaid,
                    invoice_bill_amount=plan.plan_price if calc_type.is_prepaid else 0.00,
                    is_bill_paid=True if calc_type.is_prepaid else False,
                    payment_status='Free(Trail)',
                    invoice_id=""
                )

                overall_subscription_status = OverallBusinessSubscriptionStatus.objects.create(b_id=instance,
                                                                                               validity=sub_plan.plan_end_date,
                                                                                               account_locks_on=sub_plan.plan_end_date + timedelta(
                                                                                                   days=plan.grace_period))


        except Exception as error:
            print(error)
            logger.error(f"Error Creating subscription for {instance.organization_name}: {error}", exc_info=True)


@receiver(post_save, sender=BusinessSubscriptionPlansPurchased)
def subscription_for_b_id(sender, instance, created, **kwargs):
    if created:
        try:
            overall_purchased_plan = OverallBusinessSubscriptionPlansPurchased.objects.create(b_id=instance.b_id,
                                                                                              plan_id_at_client=instance.id,
                                                                                              plan_name=instance.plan_name,
                                                                                              plan_start_date=instance.plan_start_date,
                                                                                              plan_end_date=instance.plan_end_date,
                                                                                              no_of_days=instance.no_of_days,
                                                                                              amount_per_patient=instance.amount_per_patient,
                                                                                              is_amount_percentage=instance.is_amount_percentage,
                                                                                              is_prepaid=instance.is_prepaid,
                                                                                              invoice_bill_amount=instance.invoice_bill_amount,
                                                                                              is_plan_completed=instance.is_plan_completed,
                                                                                              is_bill_paid=instance.is_bill_paid,
                                                                                              invoice_id=instance.invoice_id,
                                                                                              payment_status=instance.payment_status
                                                                                              )


        except Exception as error:
            print(error)
            logger.error(f"Error while creating sub_plan for new b_id {instance}{error}")

    else:
        try:
            overall_plan = OverallBusinessSubscriptionPlansPurchased.objects.get(b_id=instance.b_id,
                                                                                 plan_id_at_client=instance.id)
            overall_plan.plan_name = instance.plan_name
            overall_plan.plan_start_date = instance.plan_start_date
            overall_plan.plan_end_date = instance.plan_end_date
            overall_plan.no_of_days = instance.no_of_days
            overall_plan.amount_per_patient = instance.amount_per_patient
            overall_plan.is_amount_percentage = instance.is_amount_percentage
            overall_plan.is_prepaid = instance.is_prepaid
            overall_plan.invoice_bill_amount = instance.invoice_bill_amount
            overall_plan.is_plan_completed = instance.is_plan_completed
            overall_plan.is_bill_paid = instance.is_bill_paid
            overall_plan.payment_status = instance.payment_status
            overall_plan.invoice_id = instance.invoice_id
            overall_plan.save()

        except Exception as error:
            print(error)
            logger.error(f"Error while updating sub_plan for new b_id {instance}{error}")


@receiver(post_save, sender=Patient)
def activity_log_for_patient(sender, instance, created, **kwargs):
    if created:
        patient = instance
        client = instance.client
        lab_staff = instance.created_by if instance.created_by else None
        user = (HealthOProUser.objects.get(phone_number=lab_staff.mobile_number)) if lab_staff else None

        try:
            # with schema_context(client.schema_name):
            activity_log = ActivityLogs.objects.create(
                user=user,
                lab_staff=lab_staff,
                client=client,
                patient=patient,
                operation="POST",
                url="lab/patient",
                model="Patient",
                activity=f"{instance.name} registered as Patient by {lab_staff.name if lab_staff else None} on {instance.added_on.strftime('%d-%m-%y %I:%M %p')}",
                model_instance_id=instance.id,
                response_code=201,
                duration="",
            )

        except Exception as error:
            print(error)
            logger.error(f"Error Creating Activitylog for {instance.name, instance.id}in {instance.client}: {error}",
                         exc_info=True)


@receiver(post_save, sender=LabPatientInvoice)
def activity_log_for_patient_invoice(sender, instance, created, **kwargs):
    if created:
        patient = instance.patient
        client = patient.client
        lab_staff = patient.created_by
        user = HealthOProUser.objects.get(phone_number=lab_staff.mobile_number) if lab_staff else None

        try:
            # with schema_context(client.schema_name):
            activity_log = ActivityLogs.objects.create(
                user=user,
                lab_staff=lab_staff,
                client=client,
                patient=patient,
                operation="POST",
                url="lab/patient",
                model="LabPatientInvoice",
                activity=f"Invoice {instance.invoice_id} generated for Patient {instance.patient.name} by {lab_staff.name if lab_staff else None} on {instance.added_on.strftime('%d-%m-%y %I:%M %p')}",
                model_instance_id=instance.id,
                response_code=201,
                duration="",
            )



        except Exception as error:
            print(error)
            logger.error(
                f"Error Creating Activitylog for {instance.patient.name} Invoice in {instance.patient.client} on {instance.added_on.strftime('%d-%m-%y %I:%M %p')}: {error}",
                exc_info=True)


@receiver(post_save, sender=LabPatientReceipts)
def activity_log_for_patient_receipts(sender, instance, created, **kwargs):
    if created:
        patient = instance.patient
        client = patient.client
        lab_staff = instance.created_by
        user = HealthOProUser.objects.get(phone_number=lab_staff.mobile_number) if lab_staff else None

        try:
            # with schema_context(client.schema_name):
            activity_log = ActivityLogs.objects.create(
                user=user,
                lab_staff=lab_staff,
                client=client,
                patient=patient,
                operation="POST",
                url="lab/generate_receipt",
                model="LabPatientReceipts",
                activity=f"Receipt {instance.Receipt_id} generated for Patient {instance.patient.name} by {lab_staff.name if lab_staff else None} on {instance.added_on.strftime('%d-%m-%y %I:%M %p')}",
                model_instance_id=instance.id,
                response_code=201,
                duration="",
            )



        except Exception as error:
            print(error)
            logger.error(
                f"Error Creating Activitylog for {instance.patient.name} Receipt in {instance.patient.client} on {instance.added_on.strftime('%d-%m-%y %I:%M %p')}: {error}",
                exc_info=True)


@receiver(post_save, sender=LabPatientTests)
def activity_log_for_patient_tests(sender, instance, created, **kwargs):
    if created:
        patient = instance.patient
        client = patient.client
        lab_staff = patient.created_by
        user = HealthOProUser.objects.get(phone_number=lab_staff.mobile_number) if lab_staff else None

        try:
            if not instance.is_package_test:
                # with schema_context(client.schema_name):
                activity_log = ActivityLogs.objects.create(
                    user=user,
                    lab_staff=lab_staff,
                    client=client,
                    patient=patient,
                    operation="POST",
                    url="lab/patient",
                    model="LabPatientTests",
                    activity=f"{instance.name} booked for Patient {instance.patient.name} by {lab_staff.name if lab_staff else None} on {instance.added_on.strftime('%d-%m-%y %I:%M %p')}",
                    model_instance_id=instance.id,
                    response_code=201,
                    duration="",
                )


        except Exception as error:
            print(error)
            logger.error(
                f"Error Creating Activitylog for {instance.name} for {instance.patient.name}  in {instance.patient.client} on {instance.added_on.strftime('%d-%m-%y %I:%M %p')}: {error}",
                exc_info=True)


@receiver(post_save, sender=LabPatientPackages)
def activity_log_for_patient_packages(sender, instance, created, **kwargs):
    if created:
        patient = instance.patient
        client = patient.client
        lab_staff = instance.created_by
        user = HealthOProUser.objects.get(phone_number=lab_staff.mobile_number)

        try:
            # with schema_context(client.schema_name):
            activity_log = ActivityLogs.objects.create(
                user=user,
                lab_staff=lab_staff,
                client=client,
                patient=patient,
                operation="POST",
                url="lab/patient",
                model="LabPatientPackages",
                activity=f"{instance.name} booked for Patient {instance.patient.name} by {lab_staff.name} on {instance.added_on.strftime('%d-%m-%y %I:%M %p')}",
                model_instance_id=instance.id,
                response_code=201,
                duration=""
            )


        except Exception as error:
            print(error)
            logger.error(
                f"Error Creating Activitylog for {instance} for {instance.patient.name}  in {instance.patient.client} on {instance.added_on.strftime('%d-%m-%y %I:%M %p')}: {error}",
                exc_info=True)


@receiver(post_save, sender=LabPatientRefund)
def activity_log_for_patient_refund(sender, instance, created, **kwargs):
    if created:
        patient = instance.patient
        client = patient.client
        lab_staff = instance.created_by
        user = HealthOProUser.objects.get(phone_number=lab_staff.mobile_number)

        try:
            activity = [f"For patient {patient.name}:"]
            amount_refunded = instance.refund
            if amount_refunded:
                activity.append(f"Refunded Rs. {amount_refunded}.")

            if instance.remarks:
                activity.append(f"Remarks:{instance.remarks}.")

            if instance.tests:
                cancelled_tests = ", ".join([test.name for test in instance.tests.all()])
                activity.append(f"Cancelled tests: {cancelled_tests}")

            if instance.packages.exists():
                cancelled_packages = ", ".join([package.name for package in instance.packages.all()])
                activity.append(f"Cancelled packages: {cancelled_packages}")

            # with schema_context(client.schema_name):
            activity_log = ActivityLogs.objects.create(
                user=user,
                lab_staff=lab_staff,
                client=client,
                patient=patient,
                operation="POST",
                url="lab/lab_patient_refund",
                model="LabPatientRefund",
                activity=f"{"".join(activity)} on {instance.added_on.strftime('%d-%m-%y %I:%M %p')}",
                model_instance_id=instance.id,
                response_code=201,
                duration="",
            )


        except Exception as error:
            print(error)
            logger.error(
                f"Error Creating Activitylog for {instance} for {instance.patient.name}  in {patient.client} on {instance.added_on.strftime('%d-%m-%y %I:%M %p')}: {error}",
                exc_info=True)


@receiver(post_save, sender=LabPhlebotomist)
def activity_log_for_phlebotomist(sender, instance, created, **kwargs):
    if created:
        patient = instance.LabPatientTestID.patient
        client = patient.client
        lab_staff = instance.collected_by
        user = HealthOProUser.objects.get(phone_number=lab_staff.mobile_number)

        try:
            # with schema_context(client.schema_name):
            activity_log = ActivityLogs.objects.create(
                user=user,
                lab_staff=lab_staff,
                client=client,
                patient=patient,
                operation="POST",
                url="lab/lab_phlebotomists",
                model="LabPhlebotomist",
                activity=f"Sample collected for Patient {patient.name} for {instance.LabPatientTestID.name} by {lab_staff.name} on {instance.added_on.strftime('%d-%m-%y %I:%M %p')}",
                model_instance_id=instance.id,
                response_code=201,
                duration="",
            )


        except Exception as error:
            print(error)
            logger.error(
                f"Error Creating Activitylog for phlebotomist for {patient.name}  for {instance.LabPatientTestID.name} in {instance.client} on {instance.added_on.strftime('%d-%m-%y %I:%M %p')}: {error}",
                exc_info=True
            )


@receiver(post_save, sender=LabTechnicians)
def activity_log_for_technician(sender, instance, created, **kwargs):
    if created:
        patient = instance.LabPatientTestID.patient
        client = patient.client
        lab_staff = instance.report_created_by
        try:
            user = HealthOProUser.objects.get(phone_number=lab_staff.mobile_number)
        except Exception as error:
            print(error)
            user = None

        try:
            # with schema_context(client.schema_name):
            activity_log = ActivityLogs.objects.create(
                user=user,
                lab_staff=lab_staff,
                client=client,
                patient=patient,
                operation="POST",
                url="lab/lab_technicians",
                model="LabTechnicians",
                activity=f"Technician/Transcriptor object generated for Patient {patient.name} for {instance.LabPatientTestID.name} on {instance.added_on.strftime('%d-%m-%y %I:%M %p')}",
                model_instance_id=instance.id,
                response_code=201,
                duration="",
            )


        except Exception as error:
            print(error)
            logger.error(
                f"Error Creating Activitylog for technician for {patient.name}  for {instance.LabPatientTestID.name} in {patient.client} on {instance.added_on.strftime('%d-%m-%y %I:%M %p')}: {error}",
                exc_info=True)


@receiver(post_save, sender=LabTechnicians)
def create_technician_remarks(sender, instance, created, **kwargs):
    try:
        if created:
            global_test = instance.LabPatientTestID.LabGlobalTestId
            default_template = LabReportsTemplates.objects.get(LabGlobalTestID=global_test, is_default=True)
            if default_template.default_technician_remarks:
                remarks = LabTechnicianRemarks.objects.create(LabPatientTestID=instance.LabPatientTestID,
                                                              remark=default_template.default_technician_remarks)
            else:
                pass
    except Exception as error:
        logger.error(
            f"Error while creating technician remarks after technician created, if default remarks exist in report:{error}")
        print(error)


@receiver(post_save, sender=LabTechnicianRemarks)
def activity_log_for_technician_remarks(sender, instance, created, **kwargs):
    if created:
        patient = instance.LabPatientTestID.patient
        client = patient.client
        lab_staff = instance.added_by
        try:
            user = HealthOProUser.objects.get(phone_number=lab_staff.mobile_number)
        except Exception as error:
            print(error)
            user = None

        try:
            # with schema_context(client.schema_name):
            activity_log = ActivityLogs.objects.create(
                user=user,
                lab_staff=lab_staff,
                client=client,
                patient=patient,
                operation="POST",
                url="lab/lab_technician_remarks",
                model="LabTechnicians",
                activity=f"Remarks added to Technician/Transcriptor object for Patient {patient.name} for {instance.LabPatientTestID.name} by {lab_staff.name} on {instance.added_on.strftime('%d-%m-%y %I:%M %p')}",
                model_instance_id=instance.id,
                response_code=201,
                duration="",
            )


        except Exception as error:
            print(error)
            logger.error(
                f"Error Creating Activitylog for technician_remarks for {patient.name}  for {instance.LabPatientTestID.name} in {client} on {instance.added_on.strftime('%d-%m-%y %I:%M %p')}: {error}",
                exc_info=True)


@receiver(post_save, sender=LabPatientWordReportTemplate)
def activity_log_for_word_template(sender, instance, created, **kwargs):
    if created:
        patient = instance.LabPatientTestID.patient
        client = patient.client
        lab_staff = instance.created_by
        try:
            user = HealthOProUser.objects.get(phone_number=lab_staff.mobile_number)
        except Exception as error:
            print(error)
            user = None

        try:
            # with schema_context(client.schema_name):
            activity_log = ActivityLogs.objects.create(
                user=user,
                lab_staff=lab_staff,
                client=client,
                patient=patient,
                operation="POST",
                url="lab/lab_patient_report_generate",
                model="LabPatientWordReportTemplate",
                activity=f"Word Template Report created for Patient {patient.name} for {instance.LabPatientTestID.name} by {lab_staff.name} on {instance.added_on.strftime('%d-%m-%y %I:%M %p')}",
                model_instance_id=instance.id,
                response_code=201,
                duration="",
            )

        except Exception as error:
            logger.error(
                f"Error Creating Activitylog for technician_word_report for {patient.name}  for {instance.LabPatientTestID.name} in {client} on {instance.added_on.strftime('%d-%m-%y %I:%M %p')}: {error}",
                exc_info=True)


@receiver(post_save, sender=LabPatientFixedReportTemplate)
def activity_log_for_fixed_template(sender, instance, created, **kwargs):
    if created:
        patient = instance.LabPatientTestID.patient
        client = patient.client
        lab_staff = instance.created_by
        try:
            user = HealthOProUser.objects.get(phone_number=lab_staff.mobile_number)
        except Exception as error:
            print(error)
            user = None

        try:
            # with schema_context(client.schema_name):
            activity_log = ActivityLogs.objects.create(
                user=user,
                lab_staff=lab_staff,
                client=client,
                patient=patient,
                operation="POST",
                url="lab/lab_patient_report_generate",
                model="LabPatientFixedReportTemplate",
                activity=f"Fixed Report Parameter created for Patient {patient.name} for {instance.LabPatientTestID.name} by {lab_staff.name if lab_staff else ""} on {instance.added_on.strftime('%d-%m-%y %I:%M %p')}",
                model_instance_id=instance.id,
                response_code=201,
                duration="",
            )


        except Exception as error:
            print(error)
            logger.error(
                f"Error Creating Activitylog for technician_fixed_report Parameter for {patient.name}  for {instance.LabPatientTestID.name} in {client} on {instance.added_on.strftime('%d-%m-%y %I:%M %p')}: {error}",
                exc_info=True)


@receiver(post_save, sender=LabDrAuthorization)
def activity_log_for_dr(sender, instance, created, **kwargs):
    if created:
        patient = instance.LabPatientTestID.patient
        client = patient.client
        lab_staff = instance.added_by
        try:
            user = HealthOProUser.objects.get(phone_number=lab_staff.mobile_number)
        except Exception as error:
            print(error)
            user = None

        try:
            # with schema_context(client.schema_name):
            activity_log = ActivityLogs.objects.create(
                user=user,
                lab_staff=lab_staff,
                client=client,
                patient=patient,
                operation="POST",
                url="lab/lab_doctor_authorization_approval",
                model="LabDrAuthorization",
                activity=f"{instance.LabPatientTestID.name} for Patient {patient.name} Authorized  by Lab Doctor  {lab_staff.name} on {instance.added_on.strftime('%d-%m-%y %I:%M %p')}",
                model_instance_id=instance.id,
                response_code=201,
                duration="",
            )

        except Exception as error:
            print(error)
            logger.error(
                f"Error Creating Activitylog for Lab Doctor Authorization for {patient.name}  for {instance.LabPatientTestID.name} in {instance.client} on {instance.added_on.strftime('%d-%m-%y %I:%M %p')}: {error}",
                exc_info=True)


@receiver(post_save, sender=LabDrAuthorizationRemarks)
def activity_log_for_doctor_remarks(sender, instance, created, **kwargs):
    if created:
        patient = instance.LabPatientTestID.patient
        client = patient.client
        lab_staff = instance.added_by
        try:
            user = HealthOProUser.objects.get(phone_number=lab_staff.mobile_number)
        except Exception as error:
            print(error)
            user = None

        try:
            # with schema_context(client.schema_name):
            activity_log = ActivityLogs.objects.create(
                user=user,
                lab_staff=lab_staff,
                client=client,
                patient=patient,
                operation="POST",
                url="lab/lab_doctor_authorization_approval",
                model="LabDrAuthorizationRemarks",
                activity=f"Lab Doctor authorized for {instance.LabPatientTestID.name} for Patient {patient.name} by {lab_staff.name} on {instance.added_on.strftime('%d-%m-%y %I:%M %p')}",
                model_instance_id=instance.id,
                response_code=201,
                duration="",
            )

        except Exception as error:
            print(error)
            logger.error(
                f"Error Creating Activity log for Lab Doctor Authorization for {patient.name}  for {instance.LabPatientTestID.name} in {instance.client} on {instance.added_on.strftime('%d-%m-%y %I:%M %p')}: {error}",
                exc_info=True)


@receiver(post_save, sender=LabStaff)
@receiver(post_delete, sender=LabStaff)
def invalidate_cache_on_lab_staff_update(sender, instance, **kwargs):
    def invalidate_cache():
        print('started deleting cache')
        try:
            cache_key = f"user_login_data_{instance.mobile_number}_"
            for key in cache.keys(f"{cache_key}*"):
                cache.delete(key)
                print(f"Deleted cache:{key}")
        except Exception as e:
            print(f"Error occurred while invalidating cache: {str(e)}")

    transaction.on_commit(invalidate_cache)


@receiver(post_save, sender=LabStaffLoginAccess)
@receiver(post_delete, sender=LabStaffLoginAccess)
def invalidate_cache_on_lab_staff_update(sender, instance, **kwargs):
    def invalidate_cache():
        print('started deleting cache')
        try:
            cache_key = f"user_login_data_{instance.lab_staff_id.mobile_number}_"
            for key in cache.keys(f"{cache_key}*"):
                cache.delete(key)
                print(f"Deleted cache:{key}")
        except Exception as e:
            print(f"Error occurred while invalidating cache: {str(e)}")

    transaction.on_commit(invalidate_cache)


@receiver(post_delete, sender=HealthOProUser)
def invalidate_cache_on_user_update(sender, instance,created, **kwargs):
    def invalidate_cache():
        print('started deleting cache')
        try:
            cache_key = f"user_login_data_{instance.phone_number}_"
            for key in cache.keys(f"{cache_key}*"):
                cache.delete(key)
                print(f"Deleted cache: {key}")

        except Exception as e:
            print(f"Error occurred while invalidating cache: {str(e)}")

    transaction.on_commit(invalidate_cache)


@receiver(post_save, sender=BusinessProfiles)
def invalidate_cache_if_disabled(sender, instance, **kwargs):
    if instance.is_account_disabled:
        try:
            user_tenants = UserTenant.objects.filter(client__name=instance.organization_name)
            for user_tenant in user_tenants:
                user = HealthOProUser.objects.get(id=user_tenant.user.id)

                cache_key = f"user_login_data_{user.phone_number}_"
                for key in cache.keys(f"{cache_key}*"):
                    cache.delete(key)
                    print(f"Deleted cache:{key}")
        except Exception as e:
            print(f"Error occurred while invalidating cache: {str(e)}")


@receiver(post_save, sender=MarketingExecutiveVisits)
def update_last_seen_of_marketing_executive(sender, instance, **kwargs):
    try:
        executive_location, created = MarketingExecutiveLocationTracker.objects.get_or_create(
            lab_staff=instance.lab_staff)

        if instance.end_time:
            if instance.end_time > executive_location.last_seen_on:
                executive_location.last_seen_on = instance.end_time
                executive_location.latitude_at_last_seen = instance.latitude_at_end
                executive_location.longitude_at_last_seen = instance.longitude_at_end
                executive_location.address_at_last_seen = instance.address_at_end
                executive_location.save()

        elif instance.start_time:
            if instance.start_time > executive_location.last_seen_on:
                executive_location.last_seen_on = instance.start_time
                executive_location.latitude_at_last_seen = instance.latitude_at_start
                executive_location.longitude_at_last_seen = instance.longitude_at_start
                executive_location.address_at_last_seen = instance.address_at_start
                executive_location.save()
        else:
            pass
    except Exception as error:
        print(error)


@receiver(pre_save, sender=LabGlobalTests)
def department_modified(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        existing_instance = LabGlobalTests.objects.get(pk=instance.pk)
    except LabGlobalTests.DoesNotExist:
        return

    if existing_instance.department != instance.department:
        with transaction.atomic():
            templates = LabReportsTemplates.objects.filter(LabGlobalTestID=instance)
            for template in templates:
                template.department = instance.department
                template.save()

                fixed_params = LabFixedParametersReportTemplate.objects.filter(LabReportsTemplate=template)
                for fixed_param in fixed_params:
                    fixed_param.department = instance.department
                    fixed_param.save()

                word_params = LabWordReportTemplate.objects.filter(LabReportsTemplate=template)
                for word_param in word_params:
                    word_param.department = instance.department
                    word_param.save()



