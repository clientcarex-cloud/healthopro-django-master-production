from django.db import models

from healtho_pro_user.models.business_models import BusinessProfiles
from healtho_pro_user.models.universal_models import ProDoctor, Consultation


class ProDoctorConsultation(models.Model):
    pro_doctor = models.ForeignKey(ProDoctor, on_delete=models.PROTECT, related_name='consultation')
    hospital = models.ForeignKey(BusinessProfiles, on_delete=models.PROTECT, null=True)
    consultation_type = models.ForeignKey(Consultation, on_delete=models.PROTECT)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_active = models.BooleanField(default=True)


class ProdoctorAppointmentSlot(models.Model):
    pro_doctor = models.ForeignKey(ProDoctor, on_delete=models.PROTECT,blank=True, null=True, related_name='appointment_slots')
    hospital = models.ForeignKey(BusinessProfiles, on_delete=models.PROTECT, null=True)
    consultation_type = models.ForeignKey(ProDoctorConsultation, on_delete=models.PROTECT)
    date = models.DateField()
    session_start_time = models.TimeField()
    session_end_time = models.TimeField()
    session_duration = models.DurationField()
    is_active = models.BooleanField(default=True)
    is_booked = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Appointment Slot"
        verbose_name_plural = "Appointment Slots"
