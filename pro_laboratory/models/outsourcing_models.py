from django.db import models
from healtho_pro_user.models.business_models import BusinessProfiles


# class LabOutsourcingPartners(models.Model):  # Outsourcing
#     for_sending_pending = models.ManyToManyField(BusinessProfiles, related_name='for_sending_pending', blank=True)
#     for_sending_approved = models.ManyToManyField(BusinessProfiles, related_name='for_sending_approved', blank=True)
#     for_sending_removed = models.ManyToManyField(BusinessProfiles, related_name='for_sending_removed', blank=True)
#     for_receiving_pending = models.ManyToManyField(BusinessProfiles, related_name='for_receiving_pending', blank=True)
#     for_receiving_approved = models.ManyToManyField(BusinessProfiles, related_name='for_receiving_approved', blank=True)
#     for_receiving_removed = models.ManyToManyField(BusinessProfiles, related_name='for_receiving_removed', blank=True)

# Just show outsourced Patient info with that LabTests Details!
