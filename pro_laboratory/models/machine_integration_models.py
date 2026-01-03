from django.db import models


class ProcessingMachine(models.Model):
    name=models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

class DataFromProcessingMachine(models.Model):
    machine  = models.ForeignKey(ProcessingMachine, on_delete=models.PROTECT, blank=True, null=True)
    data = models.TextField(blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)
