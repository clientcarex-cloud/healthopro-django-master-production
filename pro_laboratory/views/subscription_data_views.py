from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from django_tenants.utils import schema_context
from rest_framework import viewsets, status, generics
from rest_framework.response import Response

from healtho_pro_user.models.business_models import BusinessProfiles
from healtho_pro_user.models.subscription_models import BusinessBillCalculationType, BusinessSubscriptionPlans, \
    OverallBusinessSubscriptionPlansPurchased, OverallBusinessSubscriptionStatus
from healtho_pro_user.models.users_models import Client
from pro_laboratory.models.patient_models import Patient, LabPatientReceipts, LabPatientInvoice
from pro_laboratory.models.subscription_data_models import BusinessSubscriptionPlansPurchased
from pro_laboratory.serializers.subscription_data_serializers import (BusinessSubscriptionPlansPurchasedSerializer,
                                                                      BusinessSubscriptionPlansPurchaseFromAdminSerializer)


class CheckCompletedBusinessPlans(generics.ListAPIView):
    def get(self, request=None, *args, **kwargs):
        subscriptions = OverallBusinessSubscriptionStatus.objects.all()

        today = timezone.now()

        completed_plans_list = []

        for subscription_status in subscriptions:
            try:
                if today >= subscription_status.account_locks_on:
                    client = Client.objects.filter(name=subscription_status.b_id.organization_name).first()

                    if client is not None:
                        with schema_context(client.schema_name):
                            subscription_status.is_subscription_active = False
                            subscription_status.save()
                            print(f"Subscription is made inactive for {subscription_status.b_id.organization_name}")

                            # existing_active_plans = BusinessSubscriptionPlansPurchased.objects.filter(
                            #     is_plan_completed=False,
                            #     plan__subscription_type__name='Paid',
                            #     plan_end_date__lte=today)
                            #
                            # for plan in existing_active_plans:
                            #     generate_bill_for_subscription(b_id=plan.b_id.id, plan_id=plan.id)
                            #     completed_plans_list.append(plan.b_id.organization_name)
                            #     print("Plan bill generated for ", plan.b_id.organization_name)

            except Exception as error:
                print(f"Error occured while checking {subscription_status.b_id.organization_name}:{error}")
        # completed_plans_list_businesses = ",".join(completed_plans_list)

        return Response({"Status": f"Completed checking subscription status for the businesses"},
                        status=status.HTTP_200_OK)


def check_completed_business_plans():
    print('Checking Business plans validity in Scheduling')
    plans = CheckCompletedBusinessPlans()
    response = plans.get()

    return Response(response.data, status=response.status_code)


def generate_bill_for_subscription(b_id=None, plan_id=None):
    generate_bill = GenerateBillForSubscriptionView()
    response = generate_bill.create(b_id=b_id, plan_id=plan_id)

    return Response(response.data, status=response.status_code)


class GenerateBillForSubscriptionView(generics.CreateAPIView):
    def create(self, request=None, b_id=None, plan_id=None, *args, **kwargs):
        try:
            if request:
                b_id = self.request.query_params.get('b_id', None)
                plan_id = self.request.query_params.get('plan_id', None)
            else:
                b_id = b_id
                plan_id = plan_id

            business = BusinessProfiles.objects.get(pk=b_id)

            client = Client.objects.get(name=business.organization_name)
            with schema_context(client.schema_name):
                today = timezone.now()
                plan = BusinessSubscriptionPlansPurchased.objects.get(pk=plan_id)

                if plan.plan_end_date <= today:
                    patients = Patient.objects.filter(
                        added_on__gte=plan.plan_start_date,
                        added_on__lte=plan.plan_end_date
                    )

                    patients_count = patients.count()
                    patients_total_payments = LabPatientInvoice.objects.filter(
                        patient__in=patients
                    ).aggregate(patients_total_payments=Sum('total_paid'))['patients_total_payments'] or 0

                    if plan.is_amount_percentage:
                        invoice_bill = (plan.amount_per_patient * patients_total_payments) / 100
                    else:
                        invoice_bill = plan.amount_per_patient * patients_count

                    invoices = OverallBusinessSubscriptionPlansPurchased.objects.filter(
                        plan__subscription_type__name='Paid', invoice_id__isnull=False
                    )
                    invoice_number = invoices.count() + 1

                    invoice_id = f"INV{invoice_number:05d}"
                    print(invoice_id)

                    plan.is_plan_completed = True
                    plan.payment_status = "Bill Generated"
                    plan.invoice_id = invoice_id
                    plan.invoice_bill_amount = invoice_bill
                    plan.save()

                return Response({"Status": "Bill Generated Successfully"}, status=status.HTTP_200_OK)

        except Exception as error:
            print(error)
            return Response({"Error": error}, status=status.HTTP_400_BAD_REQUEST)


def mark_payment_for_subscription_view(b_id=None, plan_id=None, invoice_id=None, paid_amount=None):
    mark_payment = MarkPaymentDoneForSubscriptionView()
    response = mark_payment.create(b_id=b_id, plan_id=plan_id, invoice_id=invoice_id, paid_amount=paid_amount)

    return Response(response.data, status=response.status_code)


class MarkPaymentDoneForSubscriptionView(generics.CreateAPIView):
    def create(self, request=None, b_id=None, plan_id=None, invoice_id=None, paid_amount=None, *args, **kwargs):
        try:
            if request:
                b_id = self.request.query_params.get('b_id', None)
                plan_id = self.request.query_params.get('plan_id', None)
                invoice_id = self.request.query_params.get('invoice_id', None)
                paid_amount = self.request.query_params.get('paid_amount', None)
            else:
                b_id = b_id
                plan_id = plan_id
                invoice_id = invoice_id
                paid_amount = paid_amount
            business = BusinessProfiles.objects.get(pk=b_id)
            paid_amount = Decimal(paid_amount)
            client = Client.objects.get(name=business.organization_name)
            with schema_context(client.schema_name):
                try:
                    plan = BusinessSubscriptionPlansPurchased.objects.get(pk=plan_id, b_id=b_id, invoice_id=invoice_id)

                    if plan:
                        if paid_amount == plan.invoice_bill_amount:
                            if not plan.is_bill_paid:
                                plan.is_bill_paid = True
                                plan.payment_status = "Bill Paid"
                                plan.save()

                                overall_plan = OverallBusinessSubscriptionPlansPurchased.objects.get(b_id=b_id,
                                                                                                     invoice_id=invoice_id)
                                overall_plan.is_bill_paid = True
                                overall_plan.payment_status = "Bill Paid"
                                overall_plan.save()

                                return Response({"Status": "Bill Marked as Paid Successfully"},
                                                status=status.HTTP_200_OK)

                            else:
                                return Response({"Error": "It seems the bill is already Paid. Please check!"},
                                                status=status.HTTP_400_BAD_REQUEST)

                        else:
                            return Response({"Error": "Paid amount not matching Invoice Bill Amount!"},
                                            status=status.HTTP_400_BAD_REQUEST)

                    else:
                        return Response({"Error": "Plan with Given details does not exist!"},
                                        status=status.HTTP_400_BAD_REQUEST)


                except BusinessSubscriptionPlansPurchased.DoesNotExist:
                    return Response({"Error": "Plan with Given details does not exist!"},
                                    status=status.HTTP_400_BAD_REQUEST)

                except Exception as error:
                    print(error)
                    return Response({"Error": error}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as error:
            print(error)
            return Response({"Error": error}, status=status.HTTP_400_BAD_REQUEST)


class BusinessSubscriptionPlansPurchasedView(generics.ListCreateAPIView):
    queryset = BusinessSubscriptionPlansPurchased.objects.all().order_by('-id')  #don't remove this
    serializer_class = BusinessSubscriptionPlansPurchasedSerializer

    def create(self, request, *args, **kwargs):
        try:
            b_id = self.request.query_params.get('b_id', None)
            b_id = BusinessProfiles.objects.get(pk=b_id)

            calc_type = BusinessBillCalculationType.objects.filter(is_default=True).first()

            plan = BusinessSubscriptionPlans.objects.filter(subscription_type__name='Paid',
                                                            is_default_plan=True).first()

            today = timezone.now()

            # Check if there are any plans that overlap with today's date
            existing_plans = BusinessSubscriptionPlansPurchased.objects.filter(
                b_id=b_id,
                plan__subscription_type__name='Paid',
                is_plan_completed=False
            )

            if existing_plans:
                return Response({"Error": "An Active Paid Plan exists already for this period!"},
                                status=status.HTTP_400_BAD_REQUEST)

            payment_not_done_plans = BusinessSubscriptionPlansPurchased.objects.filter(b_id=b_id,
                                                                                       plan__subscription_type__name='Paid',
                                                                                       is_bill_paid=False)
            if payment_not_done_plans.count() >= 1:
                return Response({"Error": "Cannot add subscription when unpaid Dues exists!"},
                                status=status.HTTP_400_BAD_REQUEST)

            sub_plan = BusinessSubscriptionPlansPurchased.objects.create(b_id=b_id, calc_type=calc_type,
                                                                         plan=plan)
            serializer = BusinessSubscriptionPlansPurchasedSerializer(sub_plan)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as error:
            return Response({"Error": error}, status=status.HTTP_400_BAD_REQUEST)


class BusinessSubscriptionPlansPurchasedCostCalculationAPIView(generics.ListAPIView):
    def list(self, request, *args, **kwargs):
        plan = BusinessSubscriptionPlansPurchased.objects.all().last()

        patients = Patient.objects.filter(
            added_on__gte=plan.plan_start_date,
            added_on__lte=plan.plan_end_date
        )

        patients_count = patients.count()
        patients_total_payments = LabPatientInvoice.objects.filter(
            patient__in=patients
        ).aggregate(patients_total_payments=Sum('total_paid'))['patients_total_payments'] or 0

        if plan.is_amount_percentage:
            invoice_bill = (plan.amount_per_patient * patients_total_payments) / 100
        else:
            invoice_bill = plan.amount_per_patient * patients_count

        invoice_bill_data = {
            "plan_start_date": plan.plan_start_date,
            "plan_end_date": plan.plan_end_date,
            "amount_per_patient": plan.amount_per_patient,
            "is_amount_percentage": plan.is_amount_percentage,
            "patients_count": patients_count,
            "patients_total_payments": patients_total_payments,
            "invoice_bill": invoice_bill
        }

        return Response(invoice_bill_data)


class BusinessSubscriptionPlansPurchasedViewset(viewsets.ModelViewSet):
    queryset = BusinessSubscriptionPlansPurchased.objects.all()
    serializer_class = BusinessSubscriptionPlansPurchasedSerializer

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            partial = kwargs.pop('partial', False)
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            validated_data = serializer.validated_data

            b_id = validated_data.get('b_id')
            calc_type = validated_data.get('calc_type')
            plan = validated_data.get('plan')
            plan_end_date = validated_data.get('plan_end_date')
            no_of_days = validated_data.get('no_of_days')
            payment_status = validated_data.get('payment_status')
            invoice_id = validated_data.get('invoice_id')
            invoice_bill_amount = validated_data.get('invoice_bill_amount')
            is_plan_completed = validated_data.get('is_plan_completed')
            is_bill_paid = validated_data.get('is_bill_paid')

            overall_plan = OverallBusinessSubscriptionPlansPurchased.objects.filter(b_id=b_id).last()

            if calc_type:
                instance.calc_type = calc_type
                instance.amount_per_patient = calc_type.amount_per_patient
                instance.is_amount_percentage = calc_type.is_amount_percentage

                overall_plan.calc_type = calc_type
                overall_plan.amount_per_patient = calc_type.amount_per_patient
                overall_plan.is_amount_percentage = calc_type.is_amount_percentage

            if plan:
                instance.plan = plan
                instance.plan_name = plan.name
                instance.plan_end_date = instance.plan_start_date + timedelta(
                    days=plan.plan_validity_in_days)
                instance.no_of_days = plan.plan_validity_in_days

                overall_plan.plan = plan
                overall_plan.plan_name = plan.name
                overall_plan.plan_end_date = instance.plan_start_date + timedelta(
                    days=plan.plan_validity_in_days)
                overall_plan.no_of_days = plan.plan_validity_in_days

            if plan_end_date:
                instance.plan_end_date = plan_end_date

                overall_plan.plan_end_date = plan_end_date

            if no_of_days:
                instance.no_of_days = no_of_days

                overall_plan.no_of_days = no_of_days

            if invoice_bill_amount:
                instance.invoice_bill_amount = invoice_bill_amount

                overall_plan.invoice_bill_amount = invoice_bill_amount

            if is_plan_completed:
                instance.is_plan_completed = is_plan_completed

                overall_plan.is_plan_completed = is_plan_completed

            if is_bill_paid:
                instance.is_bill_paid = is_bill_paid

                overall_plan.is_bill_paid = is_bill_paid

            if payment_status:
                instance.payment_status = payment_status

                overall_plan.payment_status = payment_status

            if invoice_id:
                instance.invoice_id = invoice_id

                overall_plan.invoice_id = invoice_id

            instance.save()
            overall_plan.save()

            serializer = BusinessSubscriptionPlansPurchasedSerializer(instance)

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as error:
            return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)
