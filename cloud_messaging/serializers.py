from django.db import transaction
from django.shortcuts import get_object_or_404
from django_tenants.utils import schema_context

from business_messaging.models import BusinessMessage, BusinessGroup
from business_messaging.serializers import MessagingBusinessGroupSerializer
from healtho_pro_user.models.users_models import HealthOProMessagingUser, HealthOProUser
from healtho_pro_user.serializers.users_serializers import UserSerializer
from .models import Conversation, Message, Group, MessagingFile
from rest_framework import serializers


class HealthOProUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthOProUser
        fields = ['id', 'user_type', 'HealthcareRegistryType', 'full_name']


class HealthOProMessagingUserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthOProMessagingUser
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        pro_user = representation.get('pro_user')
        if pro_user:
            representation['pro_user'] = HealthOProUserSerializer(instance.pro_user).data
        return representation


class MessagingFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessagingFile
        fields = '__all__'


class MessagingMessageSerializer(serializers.ModelSerializer):
    attachment = MessagingFileSerializer(many=True, required=False)

    class Meta:
        model = Message
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['sender_name'] = instance.sender.username

        return representation

    # def create(self, validated_data):
    #     attachments_data = validated_data.pop('attachment', [])
    #     with transaction.atomic():
    #         message = Message.objects.create(**validated_data)
    #         for attachment_data in attachments_data:
    #             file = MessagingFile.objects.create(**attachment_data, message=message)
    #             message.attachment.add(file)
    #
    #     return message


class MessagingConversationSerializer(serializers.ModelSerializer):
    partner = serializers.SerializerMethodField()
    self_unread_messages = serializers.SerializerMethodField()
    latest_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = '__all__'

    def get_partner(self, obj):
        try:
            msg_user = self.context['msg_user']
            partner = obj.initiator if msg_user == obj.receiver else obj.receiver
        except Exception as error:
            raise serializers.ValidationError({"Error": error})
        return HealthOProMessagingUserListSerializer(partner).data

    def get_self_unread_messages(self, obj):
        try:
            msg_user = self.context['msg_user']

            if obj.client and msg_user == obj.initiator:
                with schema_context(obj.client.schema_name):
                    return BusinessMessage.objects.filter(conversation=obj, is_read=False, sender=obj.receiver).count()

            elif obj.client and msg_user == obj.receiver:
                with schema_context(obj.client.schema_name):
                    return BusinessMessage.objects.filter(conversation=obj, is_read=False, sender=obj.initiator).count()

            elif not obj.client and msg_user == obj.initiator:
                return Message.objects.filter(conversation=obj, is_read=False, sender=obj.receiver).count()
            elif not obj.client and msg_user == obj.receiver:
                return Message.objects.filter(conversation=obj, is_read=False, sender=obj.initiator).count()

        except Exception as error:
            raise serializers.ValidationError({"Error": error})

    def get_latest_message(self, instance):
        try:
            if instance.client:
                with schema_context(instance.client.schema_name):
                    latest_message = BusinessMessage.objects.filter(conversation=instance).first()
            else:
                latest_message = Message.objects.filter(conversation=instance).first()

            if latest_message:
                return {
                    'sender': latest_message.sender.id,
                    'text': latest_message.text,
                    'timestamp': latest_message.timestamp
                }
            return None

        except Exception as error:
            raise serializers.ValidationError({"Error": error})

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['is_group'] = False
        latest_message = representation.get('latest_message')
        if latest_message:
            representation['latest_message_time'] = latest_message['timestamp']

        return representation


# return {
#                 'group': self.get_is_group(instance),
#                 'name': f"{instance.initiator} & {instance.receiver}",
#                 'latest_message_time': instance.latest_message_time,
#                 'latest_message': MessageSerializer(
#                     instance.latest_message).data if instance.latest_message else None,
#                 'chat_data': self.get_id(instance),
#             }


class MessagingGroupSerializer(serializers.ModelSerializer):
    total_members = serializers.SerializerMethodField()
    latest_message = serializers.SerializerMethodField()
    current_user_unread_messages_count = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = '__all__'

    def get_total_members(self, obj):
        return len(obj.members.all())

    def get_latest_message(self, obj):
        latest_message = obj.messages.first()
        if latest_message:
            return {
                'sender': latest_message.sender.id,
                'text': latest_message.text,
                'timestamp': latest_message.timestamp
            }
        return None

    def get_current_user_unread_messages_count(self, obj):
        messaging_user = self.context['msg_user']
        unread_count = obj.get_unread_message_count(messaging_user)
        return unread_count

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['is_group'] = True
        representation['latest_message_time'] = instance.latest_message.timestamp
        representation['members']=HealthOProMessagingUserListSerializer(instance.members, many=True).data
        # representation['admin'] = HealthOProMessagingUserListSerializer(instance.admin, many=True).data
        representation['creator'] = HealthOProMessagingUserListSerializer(instance.creator).data
        return representation


class MessagingCombinedChatSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    is_group = serializers.SerializerMethodField()
    name = serializers.CharField()
    latest_message_time = serializers.DateTimeField()
    latest_message = serializers.SerializerMethodField()

    def get_id(self, instance):
        if isinstance(instance, Group):
            return MessagingGroupSerializer(instance, context={"msg_user": self.context['msg_user']}).data

        elif isinstance(instance, BusinessGroup):
            return MessagingBusinessGroupSerializer(instance, context={"msg_user": self.context['msg_user']}).data

        elif isinstance(instance, Conversation):
            return MessagingConversationSerializer(instance, context={"msg_user": self.context['msg_user']}).data

    def get_id(self, instance):
        if isinstance(instance, Group):
            return MessagingGroupSerializer(instance, context={"msg_user": self.context['msg_user']}).data

        elif isinstance(instance, BusinessGroup):
            with schema_context(instance.client.schema_name):
                return MessagingBusinessGroupSerializer(instance, context={"msg_user": self.context['msg_user']}).data

        elif isinstance(instance, Conversation):
            return MessagingConversationSerializer(instance, context={"msg_user": self.context['msg_user']}).data


    def get_is_group(self, instance):
        return isinstance(instance, (Group, BusinessGroup))

    def to_representation(self, instance):
        if isinstance(instance, Conversation):
            if instance.client:
                return {
                    'group': self.get_is_group(instance),
                    'name': f"{instance.initiator} & {instance.receiver}",
                    'latest_message_time': instance.latest_message_time,
                    # 'latest_message': MessagingMessageSerializer(
                    #     instance.latest_message).data if instance.latest_message else None,
                    'chat_data': self.get_id(instance),
                }
            else:
                return {
                    'group': self.get_is_group(instance),
                    'name': f"{instance.initiator} & {instance.receiver}",
                    'latest_message_time': instance.latest_message_time,
                    # 'latest_message': MessagingMessageSerializer(
                    #     instance.latest_message).data if instance.latest_message else None,
                    'chat_data': self.get_id(instance),
                }
        elif isinstance(instance, Group):
            return {
                'group': self.get_is_group(instance),
                'name': instance.name,
                'latest_message_time': instance.latest_message_time,
                # 'latest_message': MessagingGroupSerializer(
                #     instance.latest_message).data if instance.latest_message else None,
                'group_data': self.get_id(instance),
            }

        elif isinstance(instance, BusinessGroup):
            return {
                'group': self.get_is_group(instance),
                'name': instance.name,
                'latest_message_time': instance.latest_message_time,
                # 'latest_message': MessagingGroupSerializer(
                #     instance.latest_message).data if instance.latest_message else None,
                'group_data': self.get_id(instance),
            }


class UserReadConfirmationChatSerializer(serializers.Serializer):
    conversation_id = serializers.IntegerField()
    is_read = serializers.BooleanField()


class UserReadConfirmationGroupSerializer(serializers.Serializer):
    group_id = serializers.IntegerField()
    is_read = serializers.BooleanField()


class UserEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthOProMessagingUser
        fields = ['dp', 'username']

    def validate(self, attrs):
        if 'username' in attrs or 'dp' in attrs:
            return attrs
        raise serializers.ValidationError("dp or username must taken")


class GroupEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        # fields = ['name', 'dp']
        fields = "__all__"

    def validate(self, attrs):
        if 'name' in attrs or 'dp' in attrs:
            return attrs
        raise serializers.ValidationError("dp or name must taken")
