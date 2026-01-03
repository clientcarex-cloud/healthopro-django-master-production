import hashlib
from django.db import models
from django_tenants.utils import schema_context
from rest_framework.exceptions import ValidationError
from cloud_messaging.models import Conversation
from healtho_pro_user.models.users_models import HealthOProMessagingUser, Client


# define models group
class BusinessGroup(models.Model):
    dp = models.TextField(null=True, blank=True)
    name = models.CharField(max_length=50)

    members = models.ManyToManyField(HealthOProMessagingUser, blank=True, related_name='client_group_members')
    creator = models.ForeignKey(HealthOProMessagingUser, on_delete=models.PROTECT, null=True,
                                related_name='client_group_creator')

    admin = models.ManyToManyField(HealthOProMessagingUser, blank=True, related_name='client_group_admin')
    timestamp = models.DateTimeField(auto_now_add=True, null=True)
    room_group_name = models.CharField(max_length=100, unique=True, blank=True, null=True)
    client=models.ForeignKey(Client, on_delete=models.PROTECT)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.room_group_name:
            room_group_name = f"chat_{self.name}".replace("@", "_").replace(" ", "_")

            # Create a unique hash based on the full room_group_name
            unique_hash = hashlib.md5(room_group_name.encode('utf-8')).hexdigest()[:20]
            if len(room_group_name) > 80:
                # Truncate and append the unique hash
                room_group_name = f"{room_group_name[:80]}_{unique_hash}"

            # Ensure uniqueness with numeric suffix if necessary
            suffix = 1
            original_room_group_name = room_group_name
            while BusinessGroup.objects.filter(room_group_name=room_group_name).exists():
                room_group_name = f"{original_room_group_name[:78]}_{unique_hash}_{suffix}"
                suffix += 1
                if len(room_group_name) > 100:
                    room_group_name = f"{original_room_group_name[:78]}_{unique_hash}_{suffix}"

            self.room_group_name = room_group_name

        super().save(*args, **kwargs)



    # def get_latest_message(self):
    #     return BusinessMessage.objects.filter(group=self).last()

    def get_unread_message_count(self, user):
        with schema_context(self.client.schema_name):
            if not self.members.filter(id=user.id).exists():
                raise ValidationError("User is not a member of this group")
            unread_count = BusinessMessageReadStatus.objects.filter(user=user, message__group=self, is_read=False).count()
            return unread_count


class BusinessMessagingFile(models.Model):
    file_name = models.CharField(max_length=200, null=True, blank=True)
    file = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.file_name


class BusinessMessage(models.Model):
    sender = models.ForeignKey(HealthOProMessagingUser, on_delete=models.PROTECT,
                               null=True, related_name='client_message_sender')
    text = models.TextField(blank=True)
    attachment = models.ManyToManyField(BusinessMessagingFile, blank=True)
    conversation = models.ForeignKey(Conversation, on_delete=models.PROTECT, null=True, blank=True,
                                     related_name='business_messages')
    group = models.ForeignKey(BusinessGroup, on_delete=models.PROTECT, null=True, blank=True, related_name='messages')
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False, null=True)

    class Meta:
        ordering = ('-timestamp',)

    def __str__(self):
        return f"{self.sender}->{self.conversation if self.conversation else self.group} : {self.text if self.text else 'Attachment'}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.group:
            for member in self.group.members.all():
                if member != self.sender:
                    BusinessMessageReadStatus.objects.create(user=member, message=self, is_read=False)


class BusinessMessageReadStatus(models.Model):
    user = models.ForeignKey(HealthOProMessagingUser, on_delete=models.CASCADE,related_name='client_user')
    message = models.ForeignKey(BusinessMessage, on_delete=models.CASCADE)
    is_read = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'message')

    def __str__(self):
        return f"{self.user} - {self.message} - {'Read' if self.is_read else 'Unread'}"
