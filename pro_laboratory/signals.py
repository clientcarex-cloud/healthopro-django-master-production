from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from pro_laboratory.models.doctors_models import LabDoctors
from pro_laboratory.models.patient_models import LabPatientTests
from pro_laboratory.views.labtechnicians_views import send_sms_when_reports_completed


@receiver(post_save, sender=LabPatientTests)
def check_and_send_reports_ready_sms(sender, instance, **kwargs):
    if instance.status_id.id in [3,13,17,9,21]:
        send_sms_when_reports_completed(patient=instance.patient)



from django.db import connection

@receiver(post_save, sender=LabDoctors)
@receiver(post_delete, sender=LabDoctors)
def invalidate_lab_doctors_cache(sender, instance, **kwargs):
    try:
        client_id = connection.schema_name  # This works with django-tenants
        cache_key_prefix = f'lab_referral_doctors_{client_id}_'

        # Fetch all cache keys that match the pattern and delete them
        keys_to_delete = cache.keys(f'{cache_key_prefix}*')
        for key in keys_to_delete:
            cache.delete(key)
            print(f"Deleted cache key: {key}")

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Cache invalidation failed for LabDoctors: {e}")
