import calendar

from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Q, Count, Sum, DurationField, Min, Max
from django.db.models.functions import TruncMonth
from django_filters.rest_framework import DjangoFilterBackend
from geopy import Nominatim
from geopy.exc import GeocoderTimedOut
from rest_framework import viewsets, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import generics
from rest_framework.views import APIView

from pro_laboratory.filters import MarketingExecutiveVisitsFilter
from pro_laboratory.models.doctors_models import LabDoctors
from pro_laboratory.models.global_models import LabStaff
from pro_laboratory.models.marketing_models import MarketingExecutiveVisits, MarketingExecutiveLocationTracker, \
    MarketingExecutiveTargets
from pro_laboratory.models.patient_models import Patient, LabPatientInvoice
from pro_laboratory.serializers.doctors_serializers import ReferralDoctorCountSerializer
from pro_laboratory.serializers.marketing_serializers import MarketingExecutiveVisitsSerializer, \
    MarketingExecutiveLocationTrackerSerializer, \
    MarketingExecutiveTargetsSerializer, calculate_total_worked_hours
from pro_universal_data.serializers import MarketingTargetTypesSerializer


class MarketingExecutiveVisitsViewset(viewsets.ModelViewSet):
    queryset = MarketingExecutiveVisits.objects.all()
    serializer_class = MarketingExecutiveVisitsSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = MarketingExecutiveVisitsFilter

    def get_queryset(self):
        queryset = self.queryset
        sort = self.request.query_params.get('sort', None)
        if sort == '-added_on':
            queryset = queryset.order_by('-added_on')
        if sort == 'added_on':
            queryset = queryset.order_by('added_on')

        return queryset

    def perform_create(self, serializer):
        instance = serializer.save()
        if instance.latitude_at_start and instance.longitude_at_start:
            instance.address_at_start = self.get_address(instance.latitude_at_start, instance.longitude_at_start)

        if instance.latitude_at_end and instance.longitude_at_end:
            instance.address_at_end = self.get_address(instance.latitude_at_end, instance.longitude_at_end)

        instance.save()

    def perform_update(self, serializer):
        instance = serializer.save()
        if instance.latitude_at_start and instance.longitude_at_start:
            instance.address_at_start = self.get_address(instance.latitude_at_start, instance.longitude_at_start)

        if instance.latitude_at_end and instance.longitude_at_end:
            instance.address_at_end = self.get_address(instance.latitude_at_end, instance.longitude_at_end)

        instance.save()

    def get_address(self, latitude, longitude):
        try:
            geolocator = Nominatim(user_agent="HealthOPro")
            location = geolocator.reverse(f"{latitude}, {longitude}")
            if location and location.raw:
                address = location.raw.get('address', {})
                area = address.get('neighbourhood') or address.get('road') or address.get('suburb')
                city = address.get('town') or address.get('city') or address.get('village')
                pincode = address.get('postcode')
                return f"{area}, {city}, {pincode}" if area or city or pincode else None
        except GeocoderTimedOut:
            print("Geocoding service timed out.")
        return None


class MarketingExecutiveVisitsByLabstaffView(generics.ListAPIView):
    queryset = MarketingExecutiveVisits.objects.all()
    # serializer_class = MarketingExecutiveVisitsSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = MarketingExecutiveVisitsFilter

    def get(self, request, *args, **kwargs):
        filtered_visits_queryset = self.filter_queryset(self.queryset)
        lab_staff_ids = filtered_visits_queryset.values_list('lab_staff_id', flat=True).distinct()

        lab_staffs = LabStaff.objects.filter(id__in=lab_staff_ids)

        visits_data = []

        for lab_staff in lab_staffs:
            visits = filtered_visits_queryset.filter(lab_staff=lab_staff).order_by('id')
            visit_counts = visits.values('status__name').annotate(count=Count('status'))
            accepted_count = visit_counts.filter(status__name='Accepted').aggregate(total=Count('count'))['total'] or 0
            follow_up_count = visit_counts.filter(status__name='Follow Up').aggregate(total=Count('count'))[
                                  'total'] or 0
            pending_count = visit_counts.filter(status__name='Pending').aggregate(total=Count('count'))['total'] or 0
            denied_count = visit_counts.filter(status__name='Denied').aggregate(total=Count('count'))['total'] or 0

            total_time_taken = visits.aggregate(total=Sum('total_time_taken', output_field=DurationField())
                                                )['total']

            total_distance_travelled = visits.aggregate(total=Sum('total_distance_travelled'))['total']

            first_start_time = visits.aggregate(first=Min('start_time'))['first']

            last_end_time = visits.aggregate(last=Max('end_time'))['last']

            marketing_tracker = getattr(lab_staff, 'marketingexecutivelocationtracker', None)

            if marketing_tracker is None:
                marketing_tracker = MarketingExecutiveLocationTracker.objects.create(lab_staff=lab_staff)

            last_seen = MarketingExecutiveLocationTrackerSerializer(marketing_tracker).data if marketing_tracker else ""

            visits_data.append({
                'id': lab_staff.id,
                'name': lab_staff.name,
                'mobile_number': lab_staff.mobile_number,
                'profile_pic': lab_staff.profile_pic,
                "visits": MarketingExecutiveVisitsSerializer(visits, many=True).data,
                'total_visits': visits.count(),
                'pending_visits': pending_count,
                'accepted_visits': accepted_count,
                'followup_visits': follow_up_count,
                'denied_visits': denied_count,
                'total_time_taken': calculate_total_worked_hours(total_time_taken),
                'total_distance_travelled': total_distance_travelled,
                'first_start_time': first_start_time,
                'last_end_time': last_end_time,
                'last_seen': last_seen
            })

        sort = self.request.query_params.get('sort', None)
        if sort == '-added_on':
            lab_staffs = lab_staffs.order_by('-added_on')
        if sort == 'added_on':
            lab_staffs = lab_staffs.order_by('added_on')

        page = self.paginate_queryset(visits_data)
        if page is not None:
            return self.get_paginated_response(page)

        return Response(visits_data)


class MarketingExecutiveLocationTrackerViewset(viewsets.ModelViewSet):
    queryset = MarketingExecutiveLocationTracker.objects.all()
    serializer_class = MarketingExecutiveLocationTrackerSerializer

    def get_queryset(self):
        queryset = self.queryset
        lab_staff = self.request.query_params.get('lab_staff', None)
        sort = self.request.query_params.get('sort', None)

        if lab_staff:
            queryset = queryset.filter(lab_staff__id=lab_staff)

            if queryset is None:
                obj, created = MarketingExecutiveLocationTracker.objects.get_or_create(
                    lab_staff=LabStaff.objects.get(pk=lab_staff))

        if sort == '-added_on':
            queryset = queryset.order_by('-added_on')
        if sort == 'added_on':
            queryset = queryset.order_by('added_on')

        return queryset

    def perform_update(self, serializer):
        instance = serializer.save()
        print(instance.address_at_last_seen)
        instance.address_at_last_seen = self.get_address(instance.latitude_at_last_seen,
                                                         instance.longitude_at_last_seen)
        print(instance.address_at_last_seen)
        instance.save()

    def get_address(self, latitude, longitude):
        try:
            geolocator = Nominatim(user_agent="HealthOPro")
            location = geolocator.reverse(f"{latitude}, {longitude}")
            if location and location.raw:
                address = location.raw.get('address', {})

                area = address.get('road') or address.get('neighbourhood') or address.get('suburb')
                city = address.get('town') or address.get('city') or address.get('village')
                pincode = address.get('postcode')
                return f"{area}, {city}, {pincode}" if area or city or pincode else None
        except GeocoderTimedOut:
            print("Geocoding service timed out.")
        return None


class MarketingExecutiveTargetsViewSet(viewsets.ModelViewSet):
    queryset = MarketingExecutiveTargets.objects.all()
    serializer_class = MarketingExecutiveTargetsSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data
        labstaff = validated_data.get('labstaff')
        from_date = validated_data.get('from_date')
        to_date = validated_data.get('to_date')
        assigned_area = validated_data.get('assigned_areas')

        area_conflict = MarketingExecutiveTargets.objects.filter(
            Q(from_date__lte=to_date, to_date__gte=from_date),
            assigned_areas=assigned_area
        ).exclude(labstaff=labstaff)

        if area_conflict.exists():
            return Response(
                {"Error": "This area is already assigned to another executive in the given date range!"},
                status=status.HTTP_400_BAD_REQUEST
            )
        conflicting_targets = MarketingExecutiveTargets.objects.filter(
            Q(from_date__lte=to_date, to_date__gte=from_date), labstaff=labstaff
        )

        if conflicting_targets.exists():
            return Response({"Error": "Given target dates overlaps with existing targets of Executive!"},
                            status=status.HTTP_400_BAD_REQUEST)

        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


def calculate_target_achieved_by_marketing_executive(target=None):
    doctors = LabDoctors.objects.filter(doctor_type_id=1, marketing_executive=target.labstaff,
                                        added_on__date__gte=target.from_date,
                                        added_on__date__lte=target.to_date)

    patients = Patient.objects.filter(added_on__date__gte=target.from_date,
                                      added_on__date__lte=target.to_date,
                                      referral_doctor__in=doctors)

    total_price = LabPatientInvoice.objects.filter(patient__in=patients).aggregate(total=Sum('total_price'))[
                      'total'] or 0

    return {"total_price": total_price,
            "ref_doctors_count": doctors.count(),
            "doctors": ReferralDoctorCountSerializer(doctors, many=True).data if doctors else None}


class MarketingExecutiveTargetByLabstaffView(generics.ListAPIView):
    queryset = MarketingExecutiveTargets.objects.all()
    serializer_class = MarketingExecutiveTargetsSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.query_params.get('q', None)
        selected_date = self.request.query_params.get('date', None)
        labstaff = self.request.query_params.get('labstaff', None)
        start_date = self.request.query_params.get('date_range_after', None)
        end_date = self.request.query_params.get('date_range_before', None)

        if labstaff is not None:
            queryset = queryset.filter(labstaff__id=labstaff)

        if query is not None:
            queryset = queryset.filter(labstaff__name__icontains=query)

        if selected_date:
            try:
                selected_date = timezone.datetime.strptime(selected_date, '%Y-%m-%d').date()
                queryset = queryset.filter(from_date__lte=selected_date, to_date__gte=selected_date)
            except ValueError:
                return queryset.none()

        if start_date and end_date:
            try:
                start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
                queryset = queryset.filter(from_date__lte=end_date, to_date__gte=start_date)
            except ValueError:
                return queryset.none()

        return queryset

    def list(self, request, *args, **kwargs):
        targets = self.get_queryset()
        target_data = []

        for target in targets:
            visits = MarketingExecutiveVisits.objects.filter(
                lab_staff=target.labstaff,
                date__range=[target.from_date, target.to_date]
            )
            visit_counts = visits.values('status__name').annotate(count=Count('status'))

            accepted_count = visit_counts.filter(status__name='Accepted').aggregate(total=Count('count'))['total'] or 0
            follow_up_count = visit_counts.filter(status__name='Follow Up').aggregate(total=Count('count'))[
                                  'total'] or 0
            pending_count = visit_counts.filter(status__name='Pending').aggregate(total=Count('count'))['total'] or 0
            denied_count = visit_counts.filter(status__name='Denied').aggregate(total=Count('count'))['total'] or 0

            target_achieved = calculate_target_achieved_by_marketing_executive(target=target)

            marketing_tracker = getattr(target.labstaff, 'marketingexecutivelocationtracker', None)

            if marketing_tracker is None:
                marketing_tracker = MarketingExecutiveLocationTracker.objects.create(lab_staff=target.labstaff)

            last_seen = MarketingExecutiveLocationTrackerSerializer(marketing_tracker).data if marketing_tracker else ""

            target_data.append({
                'id': target.id,
                'labstaff_id': target.labstaff.id if target.labstaff else None,
                'labstaff': target.labstaff.name if target.labstaff else None,
                'profile_pic': target.labstaff.profile_pic if target.labstaff else None,
                'mobile_number': target.labstaff.mobile_number if target.labstaff else None,
                'target_type': MarketingTargetTypesSerializer(target.target_type).data if target.target_type else None,
                'assigned_areas': target.assigned_areas if target.assigned_areas else None,
                'target_revenue': target.target_revenue if target.target_revenue else 0.00,
                'no_of_referrals': target.no_of_referrals if target.no_of_referrals else 0.00,
                'target_duration': target.target_duration.name if target.target_duration else None,
                'revenue_achieved': target_achieved['total_price'],
                'referrals_achieved': target_achieved['ref_doctors_count'],
                'new_referral_doctors': target_achieved['doctors'],
                'from_date': target.from_date,
                'to_date': target.to_date,
                'total_visits': visits.count(),
                'accepted_visits': accepted_count,
                'followup_visits': follow_up_count,
                'pending_visits': pending_count,
                'denied_visits': denied_count,
                'visits': MarketingExecutiveVisitsSerializer(visits, many=True).data,
                'last_seen': last_seen
            })

        page = self.paginate_queryset(target_data)
        if page is not None:
            return self.get_paginated_response(page)

        return Response(target_data)


class MarketingExecutiveStatsView(APIView):
    def get(self, request):
        date = self.request.query_params.get('date')
        from_date = self.request.query_params.get('from_date')
        to_date = self.request.query_params.get('to_date')
        labstaff = self.request.query_params.get('lab_staff')

        if labstaff:
            labstaff = [int(id) for id in labstaff.split(',')]

        date_content = ""
        if date:
            date_content += f"<span>Date: {date}</span>"
        elif from_date and to_date:
            date_content += f"<span>{from_date} to {to_date}</span>"

        html_content = """
        <html>
            <body>
                <table style="width:100%;" class="table inter-font">
                    <thead>
                    <tr >
                        <th colspan="5" class="text-center py-1" >Marketing Executive Statistics</th>
                    </tr>
                    <tr>
                        <th colspan="5" class="text-center py-1">"""  + date_content + f"""</th>
                    </tr>
                        <tr>
                            <th style="text-align:left;background-color:#e6e8e6;">S.No</th>
                            <th style="text-align:left;background-color:#e6e8e6;">Marketing Executive</th>
                            <th style="text-align:left;background-color:#e6e8e6;">Area</th>
                            <th style="text-align:left;background-color:#e6e8e6;">Doctor Name</th>
                            <th style="text-align:center;background-color:#e6e8e6;">Patients Count</th>
                        </tr>
                    </thead>
                    <tbody>
        """

        # Step 2: Get referral doctors (doctor_type_id=1) with non-null marketing executives
        referral_doctors = LabDoctors.objects.filter(doctor_type_id=1, marketing_executive__isnull=False)
        if labstaff:
            referral_doctors = referral_doctors.filter(marketing_executive__id__in=labstaff)

        sno = 1
        for marketing_executive in referral_doctors.values('marketing_executive__id',
                                                           'marketing_executive__name').distinct():
            executive_id = marketing_executive['marketing_executive__id']
            executive_name = marketing_executive['marketing_executive__name']
            target = MarketingExecutiveTargets.objects.filter(labstaff__id=executive_id).first()
            assigned_area = target.assigned_areas if target else "Not Assigned"

            referral_doctors_by_executive = referral_doctors.filter(marketing_executive__id=executive_id)

            for doctor in referral_doctors_by_executive:
                patients_query = Patient.objects.filter(referral_doctor=doctor)
                if date:
                    patients_query = patients_query.filter(added_on__date=date)
                elif from_date and to_date:
                    patients_query = patients_query.filter(added_on__date__range=[from_date, to_date])
                patients_count = patients_query.count()

                html_content += f"""
                <tr>
                    <td style="text-align:left;vertical-align:middle;">{sno}</td>
                    <td style="text-align:left;vertical-align:middle;">{executive_name}</td>
                    <td style="text-align:left;vertical-align:middle;">{assigned_area}</td>
                    <td style="text-align:left;vertical-align:middle;">{doctor.name}</td>
                    <td style="text-align:center;vertical-align:middle;">{patients_count}</td>
                </tr>
                """
                sno += 1
        html_content += """
                    </tbody>
                </table>
            </body>
        </html>
        """
        return Response({'html_content': html_content})
        # return HttpResponse(html_content)


class ReferralDoctorStatsAPIView(APIView):
    def get(self, request):
        date = self.request.query_params.get('date')
        start_date = self.request.query_params.get('date_range_after')
        end_date = self.request.query_params.get('date_range_before')
        doctors = self.request.query_params.get('doctors')
        if doctors:
            doctors = [int(id) for id in doctors.split(',')]
        if start_date and end_date:
            try:
                start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                raise ValidationError({'error': 'Invalid date range format. Expected format: YYYY-MM-DD'})

        referral_doctors = LabDoctors.objects.filter(doctor_type_id=1, is_active=True)
        if doctors:
            referral_doctors = referral_doctors.filter(id__in=doctors)
        ref_doctor = referral_doctors.first()
        html_content = ""

        # Determine the months in the date range
        selected_months = []
        if start_date and end_date:
            current_date = start_date
            while current_date <= end_date:
                selected_months.append((current_date.year, current_date.month))
                current_date = (current_date.replace(day=28) + timezone.timedelta(days=4)).replace(day=1)  # Next month

        # Generate month headers dynamically
        month_headers = [f"{calendar.month_abbr[month]}'{str(year)[-2:]}" for year, month in selected_months]


        date_content = ""
        if date:
            date_content += f"<span>Date: {date}</span>"
        elif start_date and end_date:
            date_content += f"<span>{start_date} to {end_date}</span>"

        html_content += f"""
             <table style="width:100%;" class="table table-bordered table-sm inter-font">
                <thead>
                    <tr>
                        <th colspan="{len(month_headers) + 3}" class="text-center py-1">Executive Name: {ref_doctor.marketing_executive.name if ref_doctor.marketing_executive else 'N/A'}</th>
                    </tr>
                    <tr>
                        <th colspan="{len(month_headers) + 3}" class="text-center py-1">Referral Doctor Statistics</th>
                    </tr>
                    <tr>
                        <th colspan="{len(month_headers) + 3}" class="text-center py-1">{date_content}</th>
                    </tr>
                   <tr>
                        <th rowspan="3" style="text-align:left;vertical-align:top;padding:2px 4px;background-color:#e6e8e6;">S.No</th>
                        <th rowspan="3" style="text-align:left;vertical-align:top;padding:2px 4px;background-color:#e6e8e6;">Doctor Name</th>
                        <th rowspan="3" style="text-align:center;vertical-align:top;padding:2px 4px;background-color:#e6e8e6;">Mobile Number</th>
                        <th colspan="{len(month_headers)*2}" style="text-align:center;padding:2px 4px;background-color:#e6e8e6;">Patients</th>
                    </tr>
                    <tr>
                        {''.join([f"<th colspan='2' style='text-align:center;padding:2px 4px;background-color:#e6e8e6;'>{header}</th>" for header in month_headers])}
                    </tr>
                    <tr>
                        {''.join([f"<th style='text-align:center;padding:2px 4px;background-color:#e6e8e6;'>Count</th>"
                                  f"<th style='text-align:center;padding:2px 4px;background-color:#e6e8e6;'>Collection</th>" for _ in month_headers])}
                    </tr>
                </thead>
                <tbody>
        """

        sno = 1
        for doctor in referral_doctors:
            patients_query = Patient.objects.filter(referral_doctor=doctor)

            if date:
                patients_query = patients_query.filter(added_on__date=date)
                patients_count = patients_query.count()
                collection = LabPatientInvoice.objects.filter(patient__in=patients_query).aggregate(Sum('total_price'))[
                                 'total_price__sum'] or 0

                html_content += f"""
                <tr>
                    <td>{sno}</td>
                    <td>{doctor.name}</td>
                    <td>{doctor.mobile_number}</td>
                    <td>{patients_count}</td>
                    <td>{collection}</td>
                </tr>
                """
            elif start_date and end_date:
                patients_query = patients_query.filter(added_on__date__range=[start_date, end_date])
                monthly_counts = {f"{calendar.month_abbr[month]}'{str(year)[-2:]}": 0 for year, month in selected_months}
                monthly_collections = {f"{calendar.month_abbr[month]}'{str(year)[-2:]}": 0 for year, month in selected_months}

                # Annotate by month and count patients
                patients_by_month = patients_query.annotate(month=TruncMonth('added_on')).values('month').annotate(
                    count=Count('id')).order_by('month')

                for month_data in patients_by_month:
                    year = month_data['month'].year
                    month = month_data['month'].month
                    month_key = f"{calendar.month_abbr[month]}'{str(year)[-2:]}"
                    monthly_counts[month_key] = month_data['count']

                    collection_for_month = LabPatientInvoice.objects.filter(
                        patient__in=patients_query,
                        patient__added_on__month=month,
                        patient__added_on__year=year
                    ).aggregate(Sum('total_cost'))['total_cost__sum'] or 0
                    monthly_collections[month_key] = collection_for_month

                counts_html = "".join([f"<td>{monthly_counts[header]}</td><td>{monthly_collections[header]}</td>" for header in month_headers])

                html_content += f"""
                <tr>
                    <td>{sno}</td>
                    <td>{doctor.name}</td>
                    <td>{doctor.mobile_number}</td>
                    {counts_html}
                </tr>
                """
                sno += 1

        html_content += """
                </tbody>
            </table>
        """
        return Response({"html_content": html_content})
        # return HttpResponse(html_content)
