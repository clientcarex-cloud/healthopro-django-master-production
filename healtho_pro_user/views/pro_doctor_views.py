from rest_framework import viewsets, status
from healtho_pro_user.models.pro_doctor_models import ProDoctorConsultation, ProdoctorAppointmentSlot
from healtho_pro_user.serializers.pro_doctor_serializers import ProDoctorConsultationSerializer, \
    ProdoctorAppointmentSlotSerializer
from datetime import datetime, timedelta
from rest_framework.response import Response


class ProDoctorConsultationViewSet(viewsets.ModelViewSet):
    queryset = ProDoctorConsultation.objects.all()
    serializer_class = ProDoctorConsultationSerializer


class ProdoctorAppointmentSlotViewSet(viewsets.ModelViewSet):
    queryset = ProdoctorAppointmentSlot.objects.all()
    serializer_class = ProdoctorAppointmentSlotSerializer

    def create(self, request, *args, **kwargs):
        data = request.data

        pro_doctor_id = data.get('pro_doctor')
        consultation_type_id = data.get('consultation_type')
        date = data.get('date')
        start_time_str = data.get('start_time')
        end_time_str = data.get('end_time')
        session_duration_minutes = int(data.get('session_duration'))

        start_time = datetime.strptime(start_time_str, '%H:%M:%S').time()
        end_time = datetime.strptime(end_time_str, '%H:%M:%S').time()
        session_duration = timedelta(minutes=session_duration_minutes)

        current_time = datetime.combine(datetime.strptime(date, '%Y-%m-%d').date(), start_time)
        end_time_dt = datetime.combine(datetime.strptime(date, '%Y-%m-%d').date(), end_time)
        slots = []

        while current_time < end_time_dt:
            session_start_time = current_time.time()
            session_end_time = (current_time + session_duration).time()

            if datetime.combine(datetime.strptime(date, '%Y-%m-%d').date(), session_end_time) > end_time_dt:
                session_end_time = end_time

            slot_data = {
                'pro_doctor': pro_doctor_id,
                'consultation_type': consultation_type_id,
                'date': date,
                'session_start_time': session_start_time,
                'session_end_time': session_end_time,
                'session_duration': str(session_duration),
                'is_active': data.get('is_active', True),
                'is_booked': data.get('is_booked', False),
            }

            serializer = self.get_serializer(data=slot_data)
            serializer.is_valid(raise_exception=True)

            self.perform_create(serializer)
            slots.append(serializer.data)

            current_time += session_duration

        queryset = ProdoctorAppointmentSlot.objects.filter(pro_doctor=pro_doctor_id)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
