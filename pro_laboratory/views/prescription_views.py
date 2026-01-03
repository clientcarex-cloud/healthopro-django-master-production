from rest_framework import viewsets

from pro_hospital.models.prescription_models import PatientPrescription
from pro_hospital.serializers.prescription_serializers import PatientPrescriptionSerializer


class PatientPrescriptionViewSet(viewsets.ModelViewSet):
    queryset = PatientPrescription.objects.all()
    serializer_class = PatientPrescriptionSerializer

    def get_queryset(self):
        queryset = PatientPrescription.objects.all()

        return queryset
