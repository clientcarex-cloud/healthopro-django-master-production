from django.db import models

from healtho_pro_user.models.pro_doctor_models import ProDoctorConsultation, ProdoctorAppointmentSlot
from healtho_pro_user.models.universal_models import ProDoctor
from pro_laboratory.models.patient_models import Patient
from pro_universal_data.models import ULabPaymentModeType


class AppointmentDetails(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, null=True)
    appointment_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Appt. details of {self.patient.name}"


class PatientAppointmentWithDoctor(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, null=True)
    pro_doctor = models.ForeignKey(ProDoctor, on_delete=models.PROTECT)
    consultation = models.ForeignKey(ProDoctorConsultation, on_delete=models.PROTECT)
    appointment_slot = models.ForeignKey(ProdoctorAppointmentSlot, on_delete=models.PROTECT)
    pay_mode = models.ForeignKey(ULabPaymentModeType, on_delete=models.PROTECT)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
