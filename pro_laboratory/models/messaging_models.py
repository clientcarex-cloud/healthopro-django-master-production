from django.db import models
from healtho_pro_user.models.users_models import Client, HealthOProUser
from pro_universal_data.models import MessagingVendors, MessagingSendType, MessagingTemplates


class SendSMSData(models.Model):
    sms_template = models.ForeignKey(MessagingTemplates, on_delete=models.PROTECT, blank=True, null=True)
    search_id = models.CharField(max_length=100, blank=True, null=True)
    numbers = models.CharField(max_length=100, blank=True, null=True)
    messaging_send_type = models.ForeignKey(MessagingSendType, blank=True, null=True, on_delete=models.CASCADE)
    message = models.TextField(blank=True, null=True)
    sent_on = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    from_date = models.DateField(blank=True, null=True)
    to_date = models.DateField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "SendSMSData"


class MessagingLogs(models.Model):
    sms = models.ForeignKey(SendSMSData, on_delete=models.PROTECT, blank=True, null=True)
    messaging_vendor = models.ForeignKey(MessagingVendors, on_delete=models.CASCADE)
    response_code = models.IntegerField(blank=True, null=True)
    status = models.CharField(max_length=255)
    message = models.TextField()
    businessid = models.CharField(max_length=100)
    messaging_send_type = models.ForeignKey(MessagingSendType, on_delete=models.CASCADE)
    numbers = models.CharField(max_length=255)
    sent_on = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        verbose_name_plural = "MessagingLogs"


class SendAndSaveWhatsAppSMSData(models.Model):
    mwa_template = models.ForeignKey(MessagingTemplates, on_delete=models.PROTECT, blank=True, null=True)
    search_id = models.CharField(max_length=100, blank=True, null=True)
    numbers = models.CharField(max_length=100, blank=True, null=True)
    messaging_send_type = models.ForeignKey(MessagingSendType, blank=True, null=True, on_delete=models.CASCADE)
    message = models.TextField(blank=True, null=True)
    sent_on = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        verbose_name_plural = "SendAndSaveWhatsAppSMSData"


class WhatsAppMessagingLogs(models.Model):
    sms = models.ForeignKey(SendAndSaveWhatsAppSMSData, on_delete=models.PROTECT, blank=True, null=True)
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


class WhatsappConfigurations(models.Model):
    secret_key = models.CharField(max_length=500, blank=True, null=True)
    phone_id = models.CharField(max_length=50, blank=True, null=True)
    is_active=models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    last_updated_by = models.ForeignKey(HealthOProUser, on_delete=models.PROTECT, blank=True, null=True)
