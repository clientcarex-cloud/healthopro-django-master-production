from django.contrib import admin

from cloud_messaging.models import Conversation, Message, Group, MessageReadStatus

# Register your models here.
admin.site.register(Conversation)
admin.site.register(Message)
admin.site.register(Group)
admin.site.register(MessageReadStatus)