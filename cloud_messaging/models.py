import hashlib
from django.db import models
from django.utils.text import slugify
from django_tenants.utils import schema_context
from rest_framework.exceptions import ValidationError
from healtho_pro_user.models.users_models import HealthOProMessagingUser, Client


# define models group
class Group(models.Model):
    dp = models.TextField(null=True, blank=True)
    name = models.CharField(max_length=50)
    members=models.ManyToManyField(HealthOProMessagingUser, blank=True)
    creator = models.ForeignKey(HealthOProMessagingUser, on_delete=models.PROTECT, null=True,
                                related_name='group_creator')

    admin = models.ManyToManyField(HealthOProMessagingUser, blank=True, related_name='cloud_messaging_group_admin')
    timestamp = models.DateTimeField(auto_now_add=True, null=True)
    room_group_name=models.CharField(max_length=100,unique=True, blank=True, null=True)

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
            while Group.objects.filter(room_group_name=room_group_name).exists():
                room_group_name = f"{original_room_group_name[:78]}_{unique_hash}_{suffix}"
                suffix += 1
                if len(room_group_name) > 100:
                    room_group_name = f"{original_room_group_name[:78]}_{unique_hash}_{suffix}"

            self.room_group_name = room_group_name

        super().save(*args, **kwargs)

    def get_latest_message(self):
        return Message.objects.filter(group=self).last()

    def get_unread_message_count(self, user):
        unread_count = MessageReadStatus.objects.filter(user=user, message__group=self, is_read=False).count()
        return unread_count


# define conversation model
class Conversation(models.Model):
    initiator = models.ForeignKey(
        HealthOProMessagingUser, on_delete=models.PROTECT, null=True, related_name="convo_starter"
    )
    receiver = models.ForeignKey(
        HealthOProMessagingUser, on_delete=models.PROTECT, null=True, related_name="convo_participant"
    )
    start_time = models.DateTimeField(auto_now_add=True)
    room_group_name=models.CharField(max_length=100,unique=True, blank=True, null=True)
    client=models.ForeignKey(Client, on_delete=models.PROTECT, blank=True, null=True)

    def __str__(self):
        return f"{self.initiator} & {self.receiver}"

    def save(self, *args, **kwargs):
        if not self.client:
            if self.initiator.client == self.receiver.client:
                self.client=self.receiver.client
        if not self.room_group_name:
            room_group_name = f"chat_{self.initiator.username}_{self.receiver.username}".replace("@", "_").replace(" ",
                                                                                                                   "_")
            if len(room_group_name) > 100:
                # Create a unique hash based on the full room_group_name
                unique_hash = hashlib.md5(room_group_name.encode('utf-8')).hexdigest()[:8]
                # Truncate and append the unique hash
                room_group_name = f"{room_group_name[:92]}_{unique_hash}"
            self.room_group_name = room_group_name
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ('initiator', 'receiver')


class MessagingFile(models.Model):
    file_name = models.CharField(max_length=200, null=True, blank=True)
    file = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.file_name



class Message(models.Model):
    sender = models.ForeignKey(HealthOProMessagingUser, on_delete=models.PROTECT,
                               null=True, related_name='message_sender')
    text = models.TextField(blank=True)
    attachment = models.ManyToManyField(MessagingFile, blank=True)
    conversation = models.ForeignKey(Conversation, on_delete=models.PROTECT, null=True, blank=True,
                                     related_name='messages')
    group = models.ForeignKey(Group, on_delete=models.PROTECT, null=True, blank=True, related_name='messages')
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False, null=True)

    def __str__(self):
        return f"{self.sender}->{self.conversation if self.conversation else self.group} : {self.text if self.text else 'Attachment'}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.group:
            for member in self.group.members.exclude(id=self.sender.id):
                MessageReadStatus.objects.create(user=member, message=self, is_read=False)

    class Meta:
        ordering = ('-timestamp',)



class MessageReadStatus(models.Model):
    user = models.ForeignKey(HealthOProMessagingUser, on_delete=models.CASCADE)
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    is_read = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'message')

    def __str__(self):
        return f"{self.user} - {self.message} - {'Read' if self.is_read else 'Unread'}"
