from django.db import models

class UInternationalDiseases(models.Model):
    icd = models.CharField(max_length=10, unique=True)
    binary_code = models.BooleanField(default=False)
    disease = models.CharField(max_length=255)
