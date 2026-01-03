from django.db import models

from healtho_pro_user.models.users_models import Client, HealthOProUser
from pro_laboratory.models.global_models import LabStaff
from pro_universal_data.models import MessagingVendors, MessagingSendType, MessagingServiceTypes, MessagingCategory, \
    MessagingTemplates


class BusinessMessagesCredits(models.Model):
    messaging_service_types = models.ForeignKey(MessagingServiceTypes, on_delete=models.PROTECT, null=True)
    new_credits = models.IntegerField()
    total_messages = models.IntegerField()
    remarks=models.CharField(max_length=300, blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(HealthOProUser, on_delete=models.PROTECT, blank=True, null=True, related_name='credits_added_by')
    last_updated = models.DateTimeField(auto_now=True)
    last_updated_by = models.ForeignKey(HealthOProUser, on_delete=models.PROTECT, blank=True, null=True, related_name='credits_updated_by')


class BulkMessagingTemplates(models.Model):
    templateName = models.CharField(max_length=100)
    messaging_service_types = models.ForeignKey(MessagingServiceTypes, on_delete=models.CASCADE)
    templateContent = models.TextField()
    templateId = models.CharField(max_length=100, null=True, blank=True)
    messaging_category = models.ForeignKey(MessagingCategory, null=True, blank=True, on_delete=models.CASCADE)
    sender_id = models.CharField(max_length=10, default=None, blank=True, null=True)
    route = models.CharField(max_length=10, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.templateName

    class Meta:
        verbose_name_plural = "BulkMessagingTemplates"


class BulkSendSMSData(models.Model):
    sms_template = models.ForeignKey(BulkMessagingTemplates, on_delete=models.PROTECT, blank=True, null=True)
    search_id = models.CharField(max_length=100, blank=True, null=True)
    numbers = models.CharField(max_length=100, blank=True, null=True)
    messaging_send_type = models.ForeignKey(MessagingSendType, blank=True, null=True, on_delete=models.CASCADE)
    message = models.TextField(blank=True, null=True)
    sent_on = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    from_date = models.DateField(blank=True, null=True)
    to_date = models.DateField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "BulkSendSMSData"


class BulkMessagingLogs(models.Model):
    sms = models.ForeignKey(BulkSendSMSData, on_delete=models.PROTECT, blank=True, null=True)
    messaging_vendor = models.ForeignKey(MessagingVendors, on_delete=models.CASCADE)
    response_code = models.IntegerField(blank=True, null=True)
    status = models.CharField(max_length=255)
    message = models.TextField()
    businessid = models.CharField(max_length=100)
    messaging_send_type = models.ForeignKey(MessagingSendType, on_delete=models.CASCADE)
    numbers = models.CharField(max_length=255)
    sent_on = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        verbose_name_plural = "BulkMessagingLogs"


class BulkSendAndSaveWhatsAppSMSData(models.Model):
    mwa_template = models.ForeignKey(BulkMessagingTemplates, on_delete=models.PROTECT, blank=True, null=True)
    search_id = models.CharField(max_length=100, blank=True, null=True)
    numbers = models.CharField(max_length=100, blank=True, null=True)
    messaging_send_type = models.ForeignKey(MessagingSendType, blank=True, null=True, on_delete=models.CASCADE)
    message = models.TextField(blank=True, null=True)
    sent_on = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        verbose_name_plural = "BulkSendAndSaveWhatsAppSMSData"


class BulkWhatsAppMessagingLogs(models.Model):
    sms = models.ForeignKey(BulkSendAndSaveWhatsAppSMSData, on_delete=models.PROTECT, blank=True, null=True)
    messaging_vendor = models.ForeignKey(MessagingVendors, on_delete=models.PROTECT)
    response_code = models.IntegerField(blank=True, null=True)
    status = models.CharField(max_length=300)
    message = models.TextField()
    businessid = models.CharField(max_length=100)
    messaging_send_type = models.ForeignKey(MessagingSendType, on_delete=models.CASCADE)
    numbers = models.CharField(max_length=255)
    sent_on = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        verbose_name_plural = "WhatsAppMessagingLogs"


class BulkMessagingHistory(models.Model):
    template = models.ForeignKey(BulkMessagingTemplates, on_delete=models.PROTECT, blank=True, null=True)
    sent_messages=models.IntegerField(blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(LabStaff, on_delete=models.PROTECT, blank=True, null=True)