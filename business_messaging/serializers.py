from django_tenants.utils import schema_context
from rest_framework import serializers

from business_messaging.models import BusinessGroup, BusinessMessage, BusinessMessagingFile
from business_messaging.views import get_latest_business_message
from healtho_pro_user.models.users_models import HealthOProMessagingUser


class HealthOProMessagingUserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthOProMessagingUser
        fields = '__all__'

    # def to_representation(self, instance):
    #     representation = super().to_representation(instance)
    #     pro_user = representation.get('pro_user')
    #     if pro_user:
    #         representation['pro_user'] = HealthOProUserSerializer(instance.pro_user).data
    #     return representation



class MessagingBusinessGroupSerializer(serializers.ModelSerializer):
    total_members = serializers.SerializerMethodField()
    latest_message = serializers.SerializerMethodField()
    current_user_unread_messages_count = serializers.SerializerMethodField()

    class Meta:
        model = BusinessGroup
        fields = '__all__'

    def get_total_members(self, obj):
        with schema_context(obj.client.schema_name):
            return len(obj.members.all())

    def get_latest_message(self, obj):
        with schema_context(obj.client.schema_name):
            latest_message = obj.messages.first()
            if latest_message:
                return {
                    'sender': latest_message.sender.id,
                    'text': latest_message.text,
                    'timestamp': latest_message.timestamp
                }
            return None

    def get_current_user_unread_messages_count(self, obj):
        with schema_context(obj.client.schema_name):
            messaging_user = self.context['msg_user']
            unread_count = obj.get_unread_message_count(messaging_user)
            return unread_count

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['is_group'] = True

        latest_message, latest_message_time = get_latest_business_message(instance)
        representation['latest_message_time'] = latest_message_time
        representation['members'] = HealthOProMessagingUserListSerializer(instance.members, many=True).data
        # representation['admin'] = HealthOProMessagingUserListSerializer(instance.admin, many=True).data
        representation['creator'] = HealthOProMessagingUserListSerializer(instance.creator).data

        return representation


class BusinessMessagingFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessMessagingFile
        fields = '__all__'


class BusinessMessagingMessageSerializer(serializers.ModelSerializer):
    attachment = BusinessMessagingFileSerializer(many=True, required=False)

    class Meta:
        model = BusinessMessage
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
