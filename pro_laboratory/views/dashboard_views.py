import calendar
from collections import defaultdict
from datetime import datetime

from django.db import models
from django.db.models import Sum, DecimalField, Q, Count, F, Case, When
from django.db.models.functions import Coalesce
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, viewsets, status
from rest_framework.response import Response

from pro_laboratory.filters import BusinessStatusFilter, PatientAnalyticsFilter, ReferralDoctorDetailsFilter, \
    DepartmentAnalyticsFilter, PayModeAnalyticsFilter, LabPhlebotomistAnalyticsFilter, LabTechniciansAnalyticsFilter, \
    LabTestAnalyticsFilter, PatientRegistrationOverviewFilter, LabDoctorAuthorizationAnalyticsFilter
from pro_laboratory.models.client_based_settings_models import BusinessControls
from pro_laboratory.models.doctorAuthorization_models import LabDrAuthorization
from pro_laboratory.models.global_models import LabStaffDefaultBranch
from pro_laboratory.models.labtechnicians_models import LabTechnicians
from pro_laboratory.models.patient_models import LabPatientRefund, LabPatientReceipts, LabPatientInvoice, Patient, \
    LabPatientTests
from pro_laboratory.models.phlebotomists_models import LabPhlebotomist
from pro_laboratory.models.universal_models import DashBoardSettings
from pro_laboratory.serializers.doctorAuthorization_serializers import AuthorizationAnalyticsSerializer
from pro_laboratory.serializers.labtechnicians_serializers import LabTechniciansAnalyticsSerializer
from pro_laboratory.serializers.patient_serializers import BusinessStatusSerializer, PatientOverviewSerializer, \
    ReferralDoctorDetailSerializer, DepartmentAnalyticsSerializer, PayModeAnalyticsSerializer, \
    LabPatientTestDetailSerializer, PatientRegistrationOverviewSerializer, PatientCountSerializer
from pro_laboratory.serializers.phlebotomists_serializers import LabPhlebotomistAnalyticsSerializer
from pro_laboratory.serializers.universal_serializers import DashBoardSettingsSerializer
from pro_universal_data.models import ULabPaymentModeType, DashBoardOptions



class DashBoardSettingsViewset(viewsets.ModelViewSet):
    queryset = DashBoardSettings.objects.all()
    serializer_class = DashBoardSettingsSerializer

    def get_queryset(self):
        lab_staff = self.request.query_params.get('lab_staff')

        if lab_staff is not None:
            return DashBoardSettings.objects.filter(lab_staff=lab_staff).order_by('ordering')
        else:
            return DashBoardSettings.objects.none()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer_data = serializer.validated_data
        lab_staff = serializer_data.get('lab_staff')
        options = DashBoardOptions.objects.all()

        for option in options:
            object = DashBoardSettings.objects.create(dash_board=option, lab_staff=lab_staff)

            object.ordering = option.id
            object.graph_size = option.graph_size
            object.save()

        data = DashBoardSettings.objects.filter(lab_staff=lab_staff)

        serializer = DashBoardSettingsSerializer(data, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)




class DayWiseCollectionsAPIView(generics.GenericAPIView):
    def get(self, request, *args, **kwargs):
        # Retrieve the date, start_date, and end_date from query params
        date = request.query_params.get('date')
        start_date = request.query_params.get('date_range_after')
        end_date = request.query_params.get('date_range_before')

        # If start_date or end_date is provided, we validate the date range
        if start_date and end_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)

            if start_date > end_date:
                return Response({'error': 'Start date cannot be greater than end date'}, status=400)
        elif date:
            try:
                date = datetime.strptime(date, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
        else:
            return Response({'error': 'Date or date range (start_date and end_date) parameter is required'}, status=400)

        # Retrieve all payment modes dynamically from the ULabPaymentModeType model
        payment_modes = ULabPaymentModeType.objects.values_list('name', flat=True)

        # Initialize new_collections, previous_due_collections, and refund_collections
        new_collections = {}
        previous_due_collections = {}
        refund_collections = {}
        subtotals = {}

        user = self.request.user
        controls = BusinessControls.objects.first()
        if controls and controls.multiple_branches:
            default_branch_obj = LabStaffDefaultBranch.objects.get(lab_staff__mobile_number=user.phone_number)
            default_branch = default_branch_obj.default_branch.all()
            receipts = LabPatientReceipts.objects.filter(patient__branch__in=default_branch)
            refunds = LabPatientRefund.objects.filter(patient__branch__in=default_branch)

        else:
            receipts = LabPatientReceipts.objects.all()
            refunds = LabPatientRefund.objects.all()

        for mode in payment_modes:
            if start_date and end_date:
                # Date range filter
                # Calculate new collections within the date range
                new_collections[mode] = receipts.filter(
                    payments__pay_mode__name=mode,
                    added_on__date__range=[start_date, end_date],
                    invoiceid__added_on__date__range=[start_date, end_date]
                ).aggregate(total=Sum('payments__paid_amount'))['total'] or 0

                # Calculate previous due collections within the date range
                previous_due_collections[mode] = receipts.filter(
                    payments__pay_mode__name=mode,
                    added_on__date__range=[start_date, end_date],
                    invoiceid__added_on__lt=start_date  # Invoices issued before the start date
                ).aggregate(total=Sum('payments__paid_amount'))['total'] or 0

                # Calculate refund collections within the date range
                refund_collections[mode] = refunds.filter(
                    refund_mode__name=mode,
                    added_on__date__range=[start_date, end_date]
                ).aggregate(total=Sum('refund'))['total'] or 0

            else:
                # Single date filter
                # Calculate new collections for the given date
                new_collections[mode] = receipts.filter(
                    payments__pay_mode__name=mode,
                    added_on__date=date,
                    invoiceid__added_on__date=date
                ).aggregate(total=Sum('payments__paid_amount'))['total'] or 0

                # Calculate previous due collections for the given date
                previous_due_collections[mode] = receipts.filter(
                    payments__pay_mode__name=mode,
                    added_on__date=date,
                    invoiceid__added_on__lt=date
                ).aggregate(total=Sum('payments__paid_amount'))['total'] or 0

                # Calculate refund collections for the given date
                refund_collections[mode] = refunds.filter(
                    refund_mode__name=mode,
                    added_on__date=date
                ).aggregate(total=Sum('refund'))['total'] or 0

            # Calculate subtotals
            subtotals[mode] = new_collections[mode] + previous_due_collections[mode] - refund_collections[mode]

        # Calculate total values across all payment modes
        new_collections['total'] = sum(new_collections[mode] for mode in payment_modes)
        previous_due_collections['total'] = sum(previous_due_collections[mode] for mode in payment_modes)
        refund_collections['total'] = sum(refund_collections[mode] for mode in payment_modes)
        subtotals['total'] = sum(subtotals[mode] for mode in payment_modes)

        # Construct response data
        response_data = {
            'new_collections': new_collections,
            'previous_due_collections': previous_due_collections,
            'refund_collections': refund_collections,
            'subtotals': subtotals
        }

        return Response(response_data)



class BusinessStatusAPIView(generics.ListAPIView):
    queryset = LabPatientInvoice.objects.all()
    serializer_class = BusinessStatusSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = BusinessStatusFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if not queryset.exists():
            return Response({
                'total_amount': 0,
                'total_discount': 0,
                'net_amount': 0,
                'balance_amount': 0,
                'refund_amount': 0,
                'total_paid': 0})

        user = self.request.user
        controls = BusinessControls.objects.first()
        if controls and controls.multiple_branches:
            default_branch_obj = LabStaffDefaultBranch.objects.get(lab_staff__mobile_number=user.phone_number)
            default_branch = default_branch_obj.default_branch.all()
            queryset = queryset.filter(patient__branch__in=default_branch)

        total_amount = queryset.aggregate(total_amount=Coalesce(Sum('total_cost'), 0, output_field=DecimalField()))[
            'total_amount']
        total_discount = \
            queryset.aggregate(total_discount=Coalesce(Sum('total_discount'), 0, output_field=DecimalField()))[
                'total_discount']
        net_amount = queryset.aggregate(net_amount=Coalesce(Sum('total_price'), 0, output_field=DecimalField()))[
            'net_amount']
        balance_amount = queryset.aggregate(balance_amount=Coalesce(Sum('total_due'), 0, output_field=DecimalField()))[
            'balance_amount']
        refund_amount = queryset.aggregate(refund_amount=Coalesce(Sum('total_refund'), 0, output_field=DecimalField()))[
            'refund_amount']
        total_paid = queryset.aggregate(total_paid=Coalesce(Sum('total_paid'), 0, output_field=DecimalField()))[
            'total_paid']

        data = {
            'total_amount': total_amount,
            'total_discount': total_discount,
            'net_amount': net_amount,
            'balance_amount': balance_amount,
            'refund_amount': refund_amount,
            'total_paid': total_paid
        }

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)




class PatientOverviewListAPIView(generics.ListAPIView):
    serializer_class = PatientOverviewSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = PatientAnalyticsFilter

    def get_queryset(self):
        queryset = Patient.objects.all()

        user = self.request.user
        controls = BusinessControls.objects.first()
        if controls and controls.multiple_branches:
            default_branch_obj = LabStaffDefaultBranch.objects.get(lab_staff__mobile_number=user.phone_number)
            default_branch = default_branch_obj.default_branch.all()
            queryset = queryset.filter(branch__in=default_branch)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        total_patients = queryset.count()
        male_count = queryset.filter(gender__name='Male').count()
        female_count = queryset.filter(gender__name='Female').count()

        age_groups = {
            '0_18': queryset.filter(age__lte=18).count(),
            '19_30': queryset.filter(Q(age__gte=19) & Q(age__lte=30)).count(),
            '31_50': queryset.filter(Q(age__gte=31) & Q(age__lte=50)).count(),
            'above_50': queryset.filter(age__gt=50).count(),
        }

        age_group_serializer = self.serializer_class()
        age_group = age_group_serializer.get_age_group(age_groups)

        if not queryset:
            return Response({
                'total_patients': 0,
                'male_count': 0,
                'female_count': 0,
                'age_group': {
                    '0_18': 0,
                    '19_30': 0,
                    '31_50': 0,
                    'above_50': 0
                }
            }, status=status.HTTP_200_OK)
        return Response({
            'total_patients': total_patients,
            'male_count': male_count,
            'female_count': female_count,
            'age_group': age_group
        }, status=status.HTTP_200_OK)




class ReferralDoctorDetailsAPIView(generics.ListAPIView):
    serializer_class = ReferralDoctorDetailSerializer
    filterset_class = ReferralDoctorDetailsFilter

    def get_queryset(self):
        queryset = Patient.objects.all()

        user = self.request.user
        controls = BusinessControls.objects.first()
        if controls and controls.multiple_branches:
            default_branch_obj = LabStaffDefaultBranch.objects.get(lab_staff__mobile_number=user.phone_number)
            default_branch = default_branch_obj.default_branch.all()
            queryset = queryset.filter(branch__in=default_branch)

        filtered_queryset = self.filterset_class(self.request.GET, queryset=queryset).qs
        output_queryset = filtered_queryset.values('referral_doctor__name').annotate(
            total_patients=Count('id', distinct=True),
            total_cost=Sum('labpatientinvoice__total_cost'),
            total_paid=Sum('labpatientinvoice__total_paid'),
            doctor_name=F('referral_doctor__name')
        )
        output_queryset = output_queryset.order_by('-total_patients')
        return output_queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        queryset = queryset[:10]
        serializer = self.get_serializer(queryset, many=True)

        response_data = {
            'count': len(serializer.data),
            'results': serializer.data
        }
        return Response(response_data)




class DepartmentAnalyticsAPIView(generics.ListAPIView):
    serializer_class = DepartmentAnalyticsSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = DepartmentAnalyticsFilter

    def get_queryset(self):
        queryset = LabPatientTests.objects.all()
        queryset = queryset.exclude(name__isnull=True)

        user = self.request.user
        controls = BusinessControls.objects.first()
        if controls and controls.multiple_branches:
            default_branch_obj = LabStaffDefaultBranch.objects.get(lab_staff__mobile_number=user.phone_number)
            default_branch = default_branch_obj.default_branch.all()
            queryset = queryset.filter(patient__branch__in=default_branch)

        filtered_queryset = self.filterset_class(self.request.GET, queryset=queryset).qs
        output_queryset = filtered_queryset.values('department__name').annotate(
            test_count=Count('id'),
            department_name=F('department__name')
        )
        output_queryset = output_queryset.order_by('-test_count')
        return output_queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        queryset = queryset
        serializer = self.get_serializer(queryset, many=True)

        response_data = {
            'count': len(serializer.data),
            'results': serializer.data
        }
        return Response(response_data)


class PayModeAnalyticsListAPIView(generics.ListAPIView):
    serializer_class = PayModeAnalyticsSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = PayModeAnalyticsFilter

    def get_queryset(self):
        queryset = LabPatientReceipts.objects.all()

        user = self.request.user
        controls = BusinessControls.objects.first()
        if controls and controls.multiple_branches:
            default_branch_obj = LabStaffDefaultBranch.objects.get(lab_staff__mobile_number=user.phone_number)
            default_branch = default_branch_obj.default_branch.all()
            queryset = queryset.filter(patient__branch__in=default_branch)

        filtered_queryset = self.filterset_class(self.request.GET, queryset=queryset).qs
        output_queryset = filtered_queryset.values('payments__pay_mode__name').annotate(
            total_patients=Count('patient__id', distinct=True),
            total_amount=Sum('payments__paid_amount'),
            pay_mode=F('payments__pay_mode__name')
        )
        total_patients_all = output_queryset.aggregate(total_patients_all=Sum('total_patients'))['total_patients_all']
        total_amount_all = output_queryset.aggregate(total_amount_all=Sum('total_amount'))['total_amount_all']

        for record in output_queryset:
            record['total_patients_all'] = total_patients_all
            record['total_amount_all'] = total_amount_all

        return output_queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        response_data = {
            'count': len(serializer.data),
            'results': serializer.data,
            'total_patients_all': queryset.aggregate(total_patients_all=Sum('total_patients'))['total_patients_all'],
            'total_amount_all': queryset.aggregate(total_amount_all=Sum('total_amount'))['total_amount_all']
        }
        return Response(response_data)




class LabPhlebotomistAnalyticsAPIView(generics.ListAPIView):
    serializer_class = LabPhlebotomistAnalyticsSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = LabPhlebotomistAnalyticsFilter

    def get_queryset(self):
        queryset = LabPhlebotomist.objects.all()

        user = self.request.user
        controls = BusinessControls.objects.first()
        if controls and controls.multiple_branches:
            default_branch_obj = LabStaffDefaultBranch.objects.get(lab_staff__mobile_number=user.phone_number)
            default_branch = default_branch_obj.default_branch.all()
            queryset = queryset.filter(LabPatientTestID__branch__in=default_branch)

        if queryset:
            queryset = queryset.values('collected_by__name').annotate(
                total_collected=Count(Case(When(is_collected=True, then=1))),
                total_pending=Count(Case(When(is_collected=False, then=1))),
                collected_by=F('collected_by__name')
            )
        return queryset



class LabTechnicianAnalyticsAPIView(generics.ListAPIView):
    serializer_class = LabTechniciansAnalyticsSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = LabTechniciansAnalyticsFilter

    def get_queryset(self):
        queryset = LabTechnicians.objects.filter(report_created_by__isnull=False)

        user = self.request.user
        controls = BusinessControls.objects.first()
        if controls and controls.multiple_branches:
            default_branch_obj = LabStaffDefaultBranch.objects.get(lab_staff__mobile_number=user.phone_number)
            default_branch = default_branch_obj.default_branch.all()
            queryset = queryset.filter(LabPatientTestID__branch__in=default_branch)


        queryset = queryset.values('report_created_by__name').annotate(
            total_received=Count('id'),
            total_draft_reports=Count(Case(When(is_word_report=False, is_completed=False, then=1))),
            total_authorization_pending=Count(Case(When(is_word_report=True, is_completed=False, then=1))),
            total_completed=Count(Case(When(is_completed=True, then=1))),
            report_created_by_name=F('report_created_by__name')
        )

        return queryset




class TopTestDetailsAPIView(generics.ListAPIView):
    serializer_class = LabPatientTestDetailSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = LabTestAnalyticsFilter

    def get_queryset(self):
        queryset = LabPatientTests.objects.all()
        queryset = queryset.exclude(name__isnull=True)

        user = self.request.user
        controls = BusinessControls.objects.first()
        if controls and controls.multiple_branches:
            default_branch_obj = LabStaffDefaultBranch.objects.get(lab_staff__mobile_number=user.phone_number)
            default_branch = default_branch_obj.default_branch.all()
            queryset = queryset.filter(branch__in=default_branch)

        filtered_queryset = self.filterset_class(self.request.GET, queryset=queryset).qs
        output_queryset = filtered_queryset.values('name').annotate(
            test_count=Count('name'),
            test_name=F('name')
        )
        output_queryset = output_queryset.order_by('-test_count')
        return output_queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        queryset = queryset[:10]
        serializer = self.get_serializer(queryset, many=True)

        response_data = {
            'count': len(serializer.data),
            'results': serializer.data
        }
        return Response(response_data)




class PatientRegistrationOverviewAPIView(generics.ListAPIView):
    serializer_class = PatientRegistrationOverviewSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = PatientRegistrationOverviewFilter

    def get_queryset(self):
        user = self.request.user
        controls = BusinessControls.objects.first()
        if controls and controls.multiple_branches:
            default_branch_obj = LabStaffDefaultBranch.objects.get(lab_staff__mobile_number=user.phone_number)
            default_branch = default_branch_obj.default_branch.all()
            queryset = Patient.objects.filter(branch__in=default_branch)
        else:
            queryset = Patient.objects.all()


        queryset = queryset.values('created_by__name').annotate(
            total_patients=Count('id', distinct=True),
            total_amount=Sum('labpatientinvoice__total_cost'),
            total_paid=Sum('labpatientinvoice__total_paid'),
            total_due=Sum('labpatientinvoice__total_due'),
            total_cash=Sum('labpatientreceipts__payments__paid_amount',
                           filter=Q(labpatientreceipts__payments__pay_mode__name='Cash')),
            created_by=F('created_by__name')
        )
        return queryset




class DoctorAuthorizationAnalyticsAPIView(generics.ListAPIView):
    serializer_class = AuthorizationAnalyticsSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = LabDoctorAuthorizationAnalyticsFilter

    def get_queryset(self):
        user = self.request.user
        controls = BusinessControls.objects.first()
        if controls and controls.multiple_branches:
            default_branch_obj = LabStaffDefaultBranch.objects.get(lab_staff__mobile_number=user.phone_number)
            default_branch = default_branch_obj.default_branch.all()
            queryset = LabDrAuthorization.objects.filter(LabPatientTestID__branch__in=default_branch)
        else:
            queryset = LabDrAuthorization.objects.all()

        queryset = queryset.values('added_by__name').annotate(
            total_authorization_pending=Sum(
                Case(When(is_authorized=False, then=1), default=0, output_field=models.IntegerField())),
            total_authorized_completed=Sum(
                Case(When(is_authorized=True, then=1), default=0, output_field=models.IntegerField())),
            added_by=F('added_by__name')
        )
        return queryset




class PatientAnalyticsView(generics.ListAPIView):
    serializer_class = PatientCountSerializer

    def get_queryset(self):
        year = self.request.query_params.get('year')
        month = self.request.query_params.get('month')
        date = self.request.query_params.get('date')
        date_range_after = self.request.query_params.get('date_range_after')
        date_range_before = self.request.query_params.get('date_range_before')

        user = self.request.user
        controls = BusinessControls.objects.first()
        if controls and controls.multiple_branches:
            default_branch_obj = LabStaffDefaultBranch.objects.get(lab_staff__mobile_number=user.phone_number)
            default_branch = default_branch_obj.default_branch.all()
            queryset = Patient.objects.filter(branch__in=default_branch)
        else:
            queryset = Patient.objects.all()

        if date_range_after and date_range_before:
            start_year, start_month, start_day = map(int, date_range_after.split('-'))
            end_year, end_month, end_day = map(int, date_range_before.split('-'))
            start_date = timezone.datetime(start_year, start_month, start_day, 0, 0, 0)
            end_date = timezone.datetime(end_year, end_month, end_day, 23, 59, 59)

            queryset = queryset.filter(added_on__gte=start_date, added_on__lte=end_date)
            return queryset


        if year:
            queryset = queryset.filter(added_on__year=year)

        if month:
            year, month_num = map(int, month.split('-'))
            start_date = timezone.datetime(year, month_num, 1)
            end_date = start_date.replace(day=calendar.monthrange(year, month_num)[1]) + timezone.timedelta(days=1)
            queryset = queryset.filter(added_on__gte=start_date, added_on__lt=end_date)

        if date:
            year, month_num, day = map(int, date.split('-'))
            start_date = timezone.datetime(year, month_num, day, 0, 0, 0)
            end_date = start_date + timezone.timedelta(days=1)
            queryset = queryset.filter(added_on__gte=start_date, added_on__lt=end_date)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        year = self.request.query_params.get('year')
        month = self.request.query_params.get('month')
        date = self.request.query_params.get('date')
        date_range_after = self.request.query_params.get('date_range_after')
        date_range_before = self.request.query_params.get('date_range_before')

        if date_range_after and date_range_before:
            date_range_after = timezone.datetime.strptime(date_range_after, '%Y-%m-%d')
            date_range_before = timezone.datetime.strptime(date_range_before, '%Y-%m-%d') + timezone.timedelta(days=1)

            if date_range_after.year < 2024:
                date_range_after = timezone.datetime(2024, 1, 1)

            patient_counts = defaultdict(int)
            current_date = date_range_after
            while current_date < date_range_before:
                formatted_date = current_date.strftime('%a, %Y %b %d')
                patient_counts[formatted_date] += queryset.filter(added_on__date=current_date).count()
                current_date += timezone.timedelta(days=1)

            return Response(dict(patient_counts))

        if date:
            hour_count_dict = {}
            for hour in range(24):
                hour_count_dict[hour] = 0
            for patient in queryset:
                registration_hour = patient.added_on.astimezone().hour
                hour_count_dict[registration_hour] += 1
            return Response(hour_count_dict)

        elif month:
            date_count_dict = {}
            year, month_num = map(int, month.split('-'))
            days_in_month = calendar.monthrange(year, month_num)[1]
            start_date = timezone.datetime(year, month_num, 1)
            current_date = start_date
            while current_date.month == month_num:
                date_count_dict[current_date.strftime('%Y-%m-%d')] = 0
                current_date += timezone.timedelta(days=1)
            for patient in queryset:
                registration_date = patient.added_on.astimezone().date()
                if registration_date.strftime('%Y-%m-%d') in date_count_dict:
                    date_count_dict[registration_date.strftime('%Y-%m-%d')] += 1
            return Response(date_count_dict)

        elif year:
            month_count_dict = {}

            for patient in queryset:
                registration_month = patient.added_on.astimezone().month

                month_name = calendar.month_name[registration_month]

                month_count_dict[month_name] = month_count_dict.get(month_name, 0) + 1

            for month_num in range(1, 13):
                month_name = calendar.month_name[month_num]

                month_count_dict.setdefault(month_name, 0)

            sorted_month_count_dict = dict(
                sorted(month_count_dict.items(), key=lambda x: list(calendar.month_name).index(x[0])))
            return Response(sorted_month_count_dict)

        else:
            return Response({"message": "Please provide year, month, or date for search."})

