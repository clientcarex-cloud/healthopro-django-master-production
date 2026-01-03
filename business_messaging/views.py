from django.shortcuts import render
from django_tenants.utils import schema_context

from business_messaging.models import BusinessMessage, BusinessGroup
from cloud_messaging.models import Conversation, Message, Group


# Create your views here.
def get_latest_business_message(chat):
    if isinstance(chat, Conversation):
        if chat.client:
            with schema_context(chat.client.schema_name):
                message=BusinessMessage.objects.filter(conversation=chat).first()
                return message, message.timestamp
        else:
            message = Message.objects.filter(conversation=chat).first()
            return message, message.timestamp

    elif isinstance(chat, BusinessGroup):
        with schema_context(chat.client.schema_name):
            message = BusinessMessage.objects.filter(group=chat).first()
            return message, message.timestamp

    elif isinstance(chat, Group):
        message = Message.objects.filter(group=chat).first()
        return message, message.timestamp
