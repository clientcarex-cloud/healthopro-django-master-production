from datetime import datetime
from gc import get_objects

from django.db.models import Count
from rest_framework import viewsets
from rest_framework.response import Response

from pro_hospital.models.patient_wise_models import PatientServices, \
    PatientDoctorConsultationDetails, IPRoomBooking, PatientVitals
from pro_hospital.models.universal_models import GlobalRoomBeds
from pro_hospital.serializers.patient_wise_serializers import \
    PatientServicesSerializer, PatientDoctorConsultationDetailsSerializer, IPRoomBookingGetSerializer, \
    PatientVitalsSerializer


class PatientDoctorConsultationDetailsViewSet(viewsets.ModelViewSet):
    queryset = PatientDoctorConsultationDetails.objects.all()
    serializer_class = PatientDoctorConsultationDetailsSerializer


class PatientServicesViewSet(viewsets.ModelViewSet):
    queryset = PatientServices.objects.all()
    serializer_class = PatientServicesSerializer

def get_patient_visit_count(doctor_id, patient_mobile_number):
    visits = (
        PatientDoctorConsultationDetails.objects.filter(
            labdoctors_id=doctor_id,
            patient__mobile_number=patient_mobile_number
        )
        .aggregate(visit_count=Count('id'))
    )
    return visits.get('visit_count', 0)

class IPRoomBookingViewSet(viewsets.ModelViewSet):
    queryset = IPRoomBooking.objects.all()
    serializer_class = IPRoomBookingGetSerializer

    def update(self, request, *args, **kwargs):
        data = request.data
        vacated_date = data.get('vacated_date')
        instance = self.get_object()
        if vacated_date:
            try:
                data['vacated_date'] = datetime.strptime(vacated_date, '%Y-%m-%d, %H:%M')
            except ValueError:
                return Response({"vacated_date": "Invalid format. Use 'YYYY-MM-DD, HH:MM'."})

        if instance.booked_bed_number:
            bed = GlobalRoomBeds.objects.filter(id=instance.booked_bed_number.id).first()
            if bed:
                bed.is_booked = False
                bed.save()
        return super().update(request, *args, **kwargs)


class PatientVitalsViewSet(viewsets.ModelViewSet):
    queryset = PatientVitals.objects.all()
    serializer_class = PatientVitalsSerializer