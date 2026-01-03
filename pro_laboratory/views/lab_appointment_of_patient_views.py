from datetime import timedelta, datetime

from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from pro_laboratory.filters import LabAppointmentForPatientFilter
from pro_laboratory.models.client_based_settings_models import BusinessControls
from pro_laboratory.models.doctors_models import LabDoctors
from pro_laboratory.models.global_models import LabStaffDefaultBranch
from pro_laboratory.models.lab_appointment_of_patient_models import LabAppointmentForPatient
from pro_laboratory.models.patient_models import Patient
from pro_laboratory.serializers.lab_appointment_of_patient_serializers import LabAppointmentForPatientSerializer
import logging
from pro_universal_data.models import MessagingTemplates, MessagingSendType
from pro_universal_data.views import send_and_log_sms
logger = logging.getLogger(__name__)

class LabAppointmentForPatientViewset(viewsets.ModelViewSet):
    queryset=LabAppointmentForPatient.objects.all()
    serializer_class = LabAppointmentForPatientSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = LabAppointmentForPatientFilter

    def get_queryset(self):
        user = self.request.user
        controls = BusinessControls.objects.first()
        if controls and controls.multiple_branches:
            default_branch_obj = LabStaffDefaultBranch.objects.get(lab_staff__mobile_number=user.phone_number)
            default_branch = default_branch_obj.default_branch.all()
            queryset = LabAppointmentForPatient.objects.filter(branch__in=default_branch)
        else:
            queryset = LabAppointmentForPatient.objects.all()


        query = self.request.query_params.get('q', None)
        sort = self.request.query_params.get('sort', None)
        departments_details = self.request.query_params.get('departments', [])
        receiptionist_details = self.request.query_params.get('labstaff_id', [])
        patient_null = self.request.query_params.get('patient_null', None)

        if query is not None:
            search_query = (Q(name__icontains=query) |Q(mobile_number__icontains=query))
            queryset = queryset.filter(search_query)

        if departments_details:
            departments = [department.strip() for department in departments_details.split(',') if department.strip()]
            department_query = Q(labpatienttests__department__id__in=departments)
            queryset = queryset.filter(department_query)

        if patient_null:
            now = datetime.now()  # Get the current date and time
            queryset = queryset.filter(
                patient__isnull=True,  # Filter where the patient field is null
            ).filter(
                Q(appointment_date__lt=now.date()) |  # Past dates
                (Q(appointment_date=now.date()) & Q(appointment_time__lte=now.time()))  # Past times today
            )

        if receiptionist_details:
            labstaffs = [labstaff.strip() for labstaff in receiptionist_details.split(',') if labstaff.strip()]
            staff_query = Q(created_by__id__in=labstaffs)
            queryset = queryset.filter(staff_query)

        if sort == '-added_on':
            queryset = queryset.order_by('-added_on')
        if sort == 'added_on':
            queryset = queryset.order_by('added_on')
        return queryset


class LabDoctorsAvailability(generics.ListAPIView):
    def list(self, request, *args, **kwargs):
        doctor_id = request.query_params.get('doctor_id', '')
        date_str = request.query_params.get('date', '')

        if doctor_id and date_str:
            try:
                doctor = LabDoctors.objects.get(pk=doctor_id)
                doctor_schedule_start = doctor.shift_start_time
                doctor_schedule_end = doctor.shift_end_time
                avg_consulting_time = doctor.avg_consulting_time

                # Parse date string to datetime
                date = datetime.strptime(date_str, '%Y-%m-%d').date()

                # Create datetime objects for the start and end times
                start_time = datetime.combine(date, doctor_schedule_start)
                end_time = datetime.combine(date, doctor_schedule_end)

                # Fetch existing appointments for the doctor on the given date
                appointments = LabAppointmentForPatient.objects.filter(
                    consulting_doctor=doctor,
                    appointment_date=date,
                    is_cancelled=False
                )

                # Get a set of booked times in minutes since start of the day
                booked_times = set()
                for appointment in appointments:
                    booked_times.add(appointment.appointment_time.strftime('%H:%M'))

                # Calculate the time slots, excluding booked times
                time_slots = []
                time_now = datetime.now()
                current_time = start_time

                while current_time < end_time:
                    # Check if current_time is before now, if so, skip it
                    if current_time < time_now:
                        current_time += timedelta(minutes=avg_consulting_time)
                        continue
                    time_str = current_time.time().strftime('%H:%M')
                    if time_str not in booked_times:
                        time_slots.append(time_str)
                    current_time += timedelta(minutes=avg_consulting_time)

                return Response({"time_slots": time_slots}, status=status.HTTP_200_OK)
            except LabDoctors.DoesNotExist:
                return Response({"Error": "Doctor not found!"}, status=status.HTTP_404_NOT_FOUND)
            except ValueError:
                return Response({"Error": "Invalid date format!"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"Error": "Doctor or Date is not entered!"}, status=status.HTTP_400_BAD_REQUEST)


class SendingAppointmentReminderSMSTOPatientsAPIView(APIView):
    def post(self, request):
        appointment_ids = self.request.data.get('appointment_ids')
        type_id = self.request.data.get('type')
        client = request.client

        appointments = LabAppointmentForPatient.objects.filter(id__in=appointment_ids)
        if str(type_id) == '1':
            for appointment in appointments:
                response = send_and_log_sms(search_id=appointment.id, numbers=appointment.mobile_number,
                                            sms_template=MessagingTemplates.objects.get(pk=3),
                                            messaging_send_type=MessagingSendType.objects.get(pk=5), client=client)
                response_code = response.data.get('response_code')
                if response_code == 200:
                    return Response({"Message sent successfully"})
                else:
                    return Response(
                        {"patient": appointment.name, "status": "Failed", "error": response.data.get('Error')},status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(
                        {"status": "Failed", "error": 'whatsapp messaging has no template'},status=status.HTTP_400_BAD_REQUEST)
            # for appointment in appointments:
            #     response = send_and_log_sms(search_id=appointment.id, numbers=appointment.mobile_number,
            #                                 sms_template=MessagingTemplates.objects.get(pk=3),
            #                                 messaging_send_type=MessagingSendType.objects.get(pk=1), client=client)
            #     response_code = response.data.get('response_code')
            #     if response_code == 200:
            #         return Response({"Message sent successfully"})
            #     else:
            #         return Response(
            #             {"patient": appointment.name, "status": "Failed", "error": response.data.get('Error')})
            #



