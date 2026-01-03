from django.contrib import admin

from interoperability.models import LabTpaType, LabTpaSecretKeys

# Register your models here.
admin.site.register(LabTpaType)
admin.site.register(LabTpaSecretKeys)
