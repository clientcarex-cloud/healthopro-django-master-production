import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async  # Import for async database operations
from django.db import transaction
from django.db.models import Q
from django.forms import model_to_dict
from django_tenants.utils import schema_context
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from business_messaging.models import BusinessGroup, BusinessMessage, BusinessMessagingFile, BusinessMessageReadStatus
from business_messaging.serializers import BusinessMessagingMessageSerializer, MessagingBusinessGroupSerializer
from business_messaging.views import get_latest_business_message
from cloud_messaging.models import Conversation, Group, Message, MessagingFile, MessageReadStatus
from cloud_messaging.serializers import HealthOProMessagingUserListSerializer, MessagingConversationSerializer, \
    MessagingCombinedChatSerializer, MessagingMessageSerializer, MessagingGroupSerializer
from cloud_messaging.views import CombinedChatView, GetAllMessagesCount, UserReadMessages, UserReadConfirmationInGroup
from healtho_pro_user.models.users_models import HealthOProMessagingUser, Client


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        self.client = self.scope['client']
        self.msg_user = self.scope['msg_user']

        self.user_chats = await self.get_user_chats_room_names(self.msg_user)

        for room_group_name in self.user_chats:
            await self.channel_layer.group_add(room_group_name, self.channel_name)

        await self.accept()

        msg_user_data = await self.get_messaging_user()

        # Send message to WebSocket
        await self.send(text_data=json.dumps({"type": "get_messaging_user", "msg_user": msg_user_data}, default=str))

    async def disconnect(self, close_code):
        for room_group_name in self.user_chats:
            await self.channel_layer.group_discard(room_group_name, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        self.room_group_name = str(text_data_json["room_group_name"])
        data = text_data_json["data"]
        message_type = text_data_json["type"]

        if message_type == "get_messaging_user":
            msg_user_data = await self.get_messaging_user()

            # Send message to WebSocket
            await self.send(
                text_data=json.dumps({"type": "get_messaging_user", "msg_user": msg_user_data}, default=str))

        elif message_type == "get_total_messages_count":
            total_unread_messages_count = await self.get_total_unread_messages_count()

            # Send message to WebSocket
            await self.send(
                text_data=json.dumps(
                    {"type": "get_total_messages_count", "total_unread_messages_count": total_unread_messages_count},
                    default=str))

        elif message_type == "get_all_messaging_users":
            all_messaging_users = await self.get_all_messaging_users(data)

            # Send message to WebSocket
            await self.send(
                text_data=json.dumps({"type": "get_all_messaging_users", "all_messaging_users": all_messaging_users},
                                     default=str))

        elif message_type == "get_all_messaging_users":
            all_messaging_users = await self.get_all_messaging_users(data)

            # Send message to WebSocket
            await self.send(
                text_data=json.dumps({"type": "get_all_messaging_users", "all_messaging_users": all_messaging_users},
                                     default=str))

        elif message_type == "start_conversation":
            conversation, room_group_name = await self.start_conversation_with_msg_user(data)
            self.room_group_name = room_group_name

            await self.channel_layer.group_send(
                self.room_group_name, {
                    "type": "handle_start_conversation_with_msg_user",
                    "room_group_name": self.room_group_name,
                    "sender": self.msg_user.username,
                    "data": conversation
                }
            )

            # Send message to WebSocket
            await self.send(
                text_data=json.dumps({"type": "start_conversation", "conversation": conversation}, default=str))

        elif message_type == "create_or_edit_group":
            group, room_group_name = await self.create_or_edit_group_with_msg_user(data)
            self.room_group_name = room_group_name

            await self.channel_layer.group_send(
                self.room_group_name, {
                    "type": "handle_create_or_edit_group_with_msg_user",
                    "room_group_name": self.room_group_name,
                    "sender": self.msg_user.username,
                    "data": group
                }
            )

            # Send message to WebSocket
            await self.send(
                text_data=json.dumps({"type": "create_or_edit_group", "group": group}, default=str))


        elif message_type == "send_messages_in_conversation":
            message = await self.send_and_save_message_in_conversation(data)
            await self.channel_layer.group_send(
                self.room_group_name, {
                    "type": "send_messages_in_conversation",
                    "room_group_name": self.room_group_name,
                    "sender": self.msg_user.username,
                    "data": message
                }
            )

        elif message_type == "send_messages_in_group":
            message = await self.send_and_save_message_in_group(data)
            await self.channel_layer.group_send(
                self.room_group_name, {
                    "type": "send_messages_in_group",
                    "room_group_name": self.room_group_name,
                    "sender": self.msg_user.username,
                    "data": message
                }
            )

        elif message_type == "get_combined_chats":
            combined_chats = await self.get_user_combined_chats()

            # Send message to WebSocket
            await self.send(
                text_data=json.dumps({"type": "get_combined_chats", "combined_chats": combined_chats}, default=str))

        elif message_type == "get_user_conversations":
            user_conversations = await self.get_user_conversations()

            # Send message to WebSocket
            await self.send(
                text_data=json.dumps({"type": "get_user_conversations", "user_conversations": user_conversations}, default=str))


        elif message_type == "get_user_groups":
            user_groups = await self.get_user_groups()

            # Send message to WebSocket
            await self.send(
                text_data=json.dumps({"type": "get_user_groups", "user_groups": user_groups}, default=str))


        elif message_type == "get_personal_chats":
            messages = await self.get_personal_messages(data)

            # Send message to WebSocket
            await self.send(
                text_data=json.dumps({"type": "get_personal_chats", "messages": messages}, default=str))


        elif message_type == "get_group_chats":
            messages = await self.get_group_messages(data)

            # Send message to WebSocket
            await self.send(
                text_data=json.dumps({"type": "get_group_chats", "messages": messages}, default=str))

        elif message_type == "mark_personal_chats_as_read":
            chats = await self.mark_personal_chats_as_read(self.room_group_name)
            combined_chats = await self.get_user_combined_chats()

            # Send message to WebSocket
            await self.send(
                text_data=json.dumps({"type": "get_combined_chats", "combined_chats": combined_chats}, default=str))

        elif message_type == "mark_group_messages_as_read":
            chats = await self.mark_group_messages_as_read(self.room_group_name)
            combined_chats = await self.get_user_combined_chats()

            # Send message to WebSocket
            await self.send(
                text_data=json.dumps({"type": "get_combined_chats", "combined_chats": combined_chats}, default=str))


        elif message_type == "change_admin_or_group_access":
            await self.change_admin_or_group_access(data)
            combined_chats = await self.get_user_combined_chats()

            # Send message to WebSocket
            await self.send(
                text_data=json.dumps({"type": "get_combined_chats", "combined_chats": combined_chats}, default=str))



    @database_sync_to_async
    def change_admin_or_group_access(self, data):
        remove_admin=data.get('remove_admin')
        leave_group = data.get('leave_group')
        add_in_group = data.get('add_in_group')
        make_admin = data.get('make_admin')
        members=data.get('members')

        if members:
            members=HealthOProMessagingUser.objects.filter(id__in=members)
        else:
            members=HealthOProMessagingUser.objects.filter(id=self.msg_user.id)

        if self.msg_user.client:
            with schema_context(self.msg_user.client.schema_name):
                group = BusinessGroup.objects.get(room_group_name=self.room_group_name)

                if self.msg_user in group.members.all() or group.admin.all():
                   if leave_group:
                       group.members.remove(*members)
                       group.admin.remove(*members)
                   elif add_in_group:
                       group.admin.add(*members)
                   elif remove_admin:
                       group.admin.remove(*members)
                   elif make_admin:
                       group.admin.add(*members)
        else:
            group = Group.objects.get(room_group_name=self.room_group_name)

            if self.msg_user in group.members.all() or group.admin.all():
                if leave_group:
                    group.members.remove(*members)
                    group.admin.remove(*members)
                elif remove_admin:
                    group.admin.remove(*members)
                elif make_admin:
                   group.admin.add(*members)




    # Function to get Room Group names for the user.
    @database_sync_to_async
    def get_user_combined_chats(self):
        combined_list = []
        personal_chats = Conversation.objects.filter(Q(initiator=self.msg_user) | Q(receiver=self.msg_user))
        combined_list.extend(personal_chats)

        if self.client:
            # Use schema_context to wrap the query
            with schema_context(self.client.schema_name):
                # Efficiently fetch business group chats related to the current user within the client's schema
                business_group_chats = BusinessGroup.objects.filter(members=self.msg_user)
                combined_list.extend(business_group_chats)

        group_chats = Group.objects.filter(members=self.msg_user)
        combined_list.extend(group_chats)

        # Extract last message timestamps
        for chat in combined_list:
            chat.latest_message, chat.latest_message_time = get_latest_business_message(chat)

        # Sort by last message timestamp
        sorted_list = sorted(combined_list, key=lambda x: x.latest_message_time, reverse=True)

        serializer = MessagingCombinedChatSerializer(sorted_list, many=True, context={"msg_user": self.msg_user})

        return serializer.data

    @database_sync_to_async
    def get_user_conversations(self):
        personal_chats = Conversation.objects.filter(Q(initiator=self.msg_user) | Q(receiver=self.msg_user))

        # Extract last message timestamps
        for chat in personal_chats:
            chat.latest_message, chat.latest_message_time = get_latest_business_message(chat)

        # Sort by last message timestamp
        sorted_list = sorted(personal_chats, key=lambda x: x.latest_message_time, reverse=True)

        serializer = MessagingCombinedChatSerializer(personal_chats, many=True, context={"msg_user": self.msg_user})

        return serializer.data

    @database_sync_to_async
    def get_user_groups(self):
        combined_list = []

        if self.client:
            # Use schema_context to wrap the query
            with schema_context(self.client.schema_name):
                # Efficiently fetch business group chats related to the current user within the client's schema
                business_group_chats = BusinessGroup.objects.filter(members=self.msg_user)
                combined_list.extend(business_group_chats)

        group_chats = Group.objects.filter(members=self.msg_user)
        combined_list.extend(group_chats)

        # Extract last message timestamps
        for chat in combined_list:
            chat.latest_message, chat.latest_message_time = get_latest_business_message(chat)

        # Sort by last message timestamp
        sorted_list = sorted(combined_list, key=lambda x: x.latest_message_time, reverse=True)

        serializer = MessagingCombinedChatSerializer(sorted_list, many=True, context={"msg_user": self.msg_user})

        return serializer.data

    @database_sync_to_async
    def get_total_unread_messages_count(self):
        total_unread_messages_count = GetAllMessagesCount.get(self, msg_user=self.msg_user)
        return total_unread_messages_count.data

    @database_sync_to_async
    def mark_personal_chats_as_read(self, room_group_name):
        # Check if the current user is a part of the conversation
        conversation = Conversation.objects.get(room_group_name=room_group_name)
        if self.msg_user == conversation.initiator or self.msg_user == conversation.receiver:
            if self.msg_user == conversation.initiator:
                partner = conversation.receiver
            else:
                partner = conversation.initiator

            if conversation.client:
                with schema_context(conversation.client.schema_name):
                    messages = BusinessMessage.objects.filter(conversation=conversation, sender=partner, is_read=False)
                    # Update is_read status for messages
                    for message in messages:
                        message.is_read = True
                        message.save()
            else:
                # Filter messages by conversation ID and check if the current user is the receiver
                messages = Message.objects.filter(conversation=conversation, sender=partner, is_read=False)
                # Update is_read status for messages
                for message in messages:
                    message.is_read = True
                    message.save()


    @database_sync_to_async
    def mark_group_messages_as_read(self, room_group_name):
        if self.msg_user.client:
            with schema_context(self.msg_user.client.schema_name):
                try:
                    group = BusinessGroup.objects.get(room_group_name=room_group_name)
                except BusinessGroup.DoesNotExist:
                    return Response({"message": "Group Does Not Exist"}, status=404)

                if self.msg_user not in group.members.all():
                    return Response({"message": "You are not in this group"}, status=403)

                # Get all messages in the group sent by other members
                messages = BusinessMessage.objects.filter(group=group).exclude(sender=self.msg_user)

                # Update read status for each message for the user
                BusinessMessageReadStatus.objects.filter(
                    user=self.msg_user,
                    message__in=messages
                ).update(is_read=True)
        else:
            try:
                group = Group.objects.get(room_group_name=room_group_name)
            except Group.DoesNotExist:
                return Response({"message": "Group Does Not Exist"}, status=404)

            if self.msg_user not in group.members.all():
                return Response({"message": "You are not in this group"}, status=403)

            # Get all messages in the group sent by other members
            messages = Message.objects.filter(group=group).exclude(sender=self.msg_user)

            # Update read status for each message for the user
            MessageReadStatus.objects.filter(
                user=self.msg_user,
                message__in=messages
            ).update(is_read=True)


    @database_sync_to_async
    def get_combined_chats(self):
        response = MessagingCombinedChatSerializer(msg_user=self.msg_user)
        return response.data


    @database_sync_to_async
    def get_messaging_user(self):
        serializer = HealthOProMessagingUserListSerializer(self.msg_user)
        return serializer.data

    @database_sync_to_async
    def get_all_messaging_users(self, data):
        client = data.get('client')
        username = data.get('username')

        if client:
            users = HealthOProMessagingUser.objects.filter(client__id=client)
        else:
            users = HealthOProMessagingUser.objects.all()

        if username:
            users = users.filter(username__icontains=username)

        serializer = HealthOProMessagingUserListSerializer(users, many=True)
        return serializer.data

    @database_sync_to_async
    def start_conversation_with_msg_user(self, data):
        receiver_id = data.get('receiver')
        message_text = data.get('text')

        receiver = HealthOProMessagingUser.objects.get(id=receiver_id)

        # Check if a conversation already exists
        conversation = Conversation.objects.filter(
            Q(initiator=self.msg_user, receiver=receiver) | Q(initiator=receiver, receiver=self.msg_user)
        ).first()

        if not conversation:
            # Create a new conversation if it doesn't exist
            conversation = Conversation.objects.create(initiator=self.msg_user, receiver=receiver)

        if conversation.client:
            with schema_context(conversation.client.schema_name):
                message = BusinessMessage.objects.create(conversation=conversation, sender=self.msg_user,
                                                         text=message_text)
        else:
            # Create a new message in the conversation
            message = Message.objects.create(conversation=conversation, sender=self.msg_user, text=message_text)

        # Serialize the conversation and message data with context
        conversation_serializer = MessagingConversationSerializer(conversation, context={'msg_user': self.msg_user})

        return conversation_serializer.data, conversation.room_group_name

    @database_sync_to_async
    def create_or_edit_group_with_msg_user(self, data):
        members = data.get('members')
        admin = data.get('admin')
        name=data.get('name')
        dp = data.get('dp')
        text = data.get('text')
        group_id = data.get('group_id')

        if not group_id:
            if members and name and text:
                if self.msg_user.id not in members:
                    members.append(self.msg_user.id)

                group_members = HealthOProMessagingUser.objects.filter(id__in=members)
                # Add self.msg_user if not already in members
                client_ids = list(set(group_members.values_list('client__id', flat=True).distinct()))

                if len(client_ids) > 1:
                    raise ValueError("All group members must belong to the same client!")

                creator = self.msg_user
                client=self.client

                if self.msg_user.id not in admin:
                    admin.append(self.msg_user.id)
                group_admin = HealthOProMessagingUser.objects.filter(id__in=admin)

                if self.msg_user.client:
                    with schema_context(self.msg_user.client.schema_name):
                        group = BusinessGroup.objects.create(name=name, dp=dp, creator=creator, client=client)
                        group.members.set(group_members)
                        group.admin.set(group_admin)

                        message=BusinessMessage.objects.create(sender=creator, text=text, group=group)

                        serializer = MessagingBusinessGroupSerializer(group, context={"msg_user":self.msg_user})
                        return serializer.data, group.room_group_name

                else:
                    group = Group.objects.create(name=name, dp=dp,creator=creator)
                    group.members.set(group_members)
                    group.admin.set(group_admin)
                    message = Message.objects.create(sender=creator, text=text, group=group)
                    serializer=MessagingGroupSerializer(group, context={"msg_user":self.msg_user})
                    return serializer.data, group.room_group_name
        else:

            if self.msg_user.client:
                with schema_context(self.msg_user.client.schema_name):
                    group = BusinessGroup.objects.get(pk=group_id)

                    if not self.msg_user in group.admin.all():
                        return "User is not Admin of Group"
                    group.dp = dp if dp else group.dp
                    group.name = name if name else group.name
                    if members:
                        group_members = HealthOProMessagingUser.objects.filter(id__in=members)
                        group.members.set(group_members)

                    if admin:
                        group_admin = HealthOProMessagingUser.objects.filter(id__in=admin)
                        group.admin.set(group_admin)

                    group.save()

                    serializer = MessagingBusinessGroupSerializer(group, context={"msg_user":self.msg_user})
                    return serializer.data, group.room_group_name

            else:
                group = Group.objects.get(pk=group_id)
                if not self.msg_user in group.admin.all():
                    return "User is not Admin of Group"
                group.dp = dp if dp else group.dp
                group.name = name if name else group.name
                if admin:
                    group_admin = HealthOProMessagingUser.objects.filter(id__in=admin)
                    group.admin.set(group_admin)

                if members:
                    group_members = HealthOProMessagingUser.objects.filter(id__in=members)
                    group.members.set(group_members)

                group.save()

                serializer = MessagingGroupSerializer(group, context={"msg_user":self.msg_user})
                return serializer.data, group.room_group_name


    @database_sync_to_async
    def send_and_save_message_in_group(self, data):
        text = data.get('text')
        attachments = data.get('attachment')

        if self.msg_user.client:
            with schema_context(self.msg_user.client.schema_name):
                group = BusinessGroup.objects.get(room_group_name=self.room_group_name)
                message = BusinessMessage.objects.create(sender=self.msg_user,
                                                         group=group,
                                                         text=text)

                if attachments:
                    for attachment in attachments:
                        file = BusinessMessagingFile.objects.create(file=attachment['file'],
                                                                    file_name=attachment['file_name'])
                        message.attachment.add(file)

                return BusinessMessagingMessageSerializer(message).data
        else:
            group = BusinessGroup.objects.get(room_group_name=self.room_group_name)
            message = BusinessMessage.objects.create(sender=self.msg_user,
                                                     group=group,
                                                     text=text)

            if attachments:
                for attachment in attachments:
                    file = BusinessMessagingFile.objects.create(file=attachment['file'],
                                                                file_name=attachment['file_name'])
                    message.attachment.add(file)

            return BusinessMessagingMessageSerializer(message).data



    @database_sync_to_async
    def send_and_save_message_in_conversation(self, data):
        text = data.get('text')
        attachments = data.get('attachment')

        # Check if a conversation already exists
        conversation = Conversation.objects.get(room_group_name=self.room_group_name)

        if self.msg_user in [conversation.initiator, conversation.receiver]:
            if conversation.client:
                with schema_context(conversation.client.schema_name):
                    message = BusinessMessage.objects.create(sender=self.msg_user,
                                                             conversation=conversation,
                                                             text=text)

                    if attachments:
                        for attachment in attachments:
                            file = BusinessMessagingFile.objects.create(file=attachment['file'],
                                                                file_name=attachment['file_name'])
                            message.attachment.add(file)

                    return BusinessMessagingMessageSerializer(message).data
            else:
                message = Message.objects.create(sender=self.msg_user,
                                                 conversation=conversation,
                                                 text=text)
                if attachments:
                    for attachment in attachments:
                        file = MessagingFile.objects.create(file=attachment['file'],
                                                            file_name=attachment['file_name'])
                        message.attachment.add(file)

                return MessagingMessageSerializer(message).data

    async def handle_start_conversation_with_msg_user(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            "type": "start_conversation",
            "room_group_name": event["room_group_name"],
            "personal_messages": event["data"]
        }, default=str))

        combined_chats = await self.get_user_combined_chats()

        # Send message to WebSocket
        await self.send(
            text_data=json.dumps({"type": "get_combined_chats", "combined_chats": combined_chats}, default=str))


    async def handle_create_or_edit_group_with_msg_user(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            "type": "create_or_edit_group",
            "room_group_name": event["room_group_name"],
            "group": event["data"]
        }, default=str))

        combined_chats = await self.get_user_combined_chats()

        # Send message to WebSocket
        await self.send(
            text_data=json.dumps({"type": "get_combined_chats", "combined_chats": combined_chats}, default=str))


    async def send_messages_in_conversation(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            "type": "send_messages_in_conversation",
            "room_group_name": event["room_group_name"],
            "message": event["data"]
        }, default=str))

        combined_chats = await self.get_user_combined_chats()

        # Send message to WebSocket
        await self.send(
            text_data=json.dumps({"type": "get_combined_chats", "combined_chats": combined_chats}, default=str))


    async def send_messages_in_group(self, event):

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            "type": "send_messages_in_group",
            "room_group_name": event["room_group_name"],
            "message": event["data"]
        }, default=str))

        combined_chats = await self.get_user_combined_chats()

        # Send message to WebSocket
        await self.send(
            text_data=json.dumps({"type": "get_combined_chats", "combined_chats": combined_chats}, default=str))


    @database_sync_to_async
    def get_group_messages(self, data):
        sender = self.msg_user
        if self.msg_user.client:
            with schema_context(self.msg_user.client.schema_name):
                group=BusinessGroup.objects.get(room_group_name=self.room_group_name)
                page_size = data.get('page_size')
                if not page_size:
                    page_size = 25
                latest_message_id = data.get('latest_message_id')
                if self.msg_user in group.members.all():
                    messages=BusinessMessage.objects.filter(group=group)[:int(page_size)]

                    if latest_message_id:
                        messages = BusinessMessage.objects.filter(group=group, id__lt=int(latest_message_id))[
                                   :int(page_size)]

                    serializer = BusinessMessagingMessageSerializer(messages, many=True)
                    return serializer.data

        else:
            group = Group.objects.get(room_group_name=self.room_group_name)
            page_size = data.get('page_size')
            if not page_size:
                page_size = 25
            latest_message_id = data.get('latest_message_id')
            if self.msg_user in group.members.all():
                messages = Message.objects.filter(group=group)[:int(page_size)]

                if latest_message_id:
                    messages = Message.objects.filter(group=group, id__lt=int(latest_message_id))[
                               :int(page_size)]

                serializer = MessagingMessageSerializer(messages, many=True)
                return serializer.data


    @database_sync_to_async
    def get_personal_messages(self, data):
        sender = self.msg_user
        conversation = Conversation.objects.get(room_group_name=self.room_group_name)
        page_size = data.get('page_size')

        if not page_size:
            page_size = 25

        latest_message_id = data.get('latest_message_id')

        if sender in [conversation.initiator, conversation.receiver]:
            if conversation.client:
                with schema_context(conversation.client.schema_name):
                    messages = BusinessMessage.objects.filter(conversation=conversation)[:int(page_size)]
                    if latest_message_id:
                        messages = BusinessMessage.objects.filter(conversation=conversation, id__lt=int(latest_message_id))[
                                   :int(page_size)]

                    serializer = BusinessMessagingMessageSerializer(messages, many=True)
                    return serializer.data
            else:
                messages = Message.objects.filter(conversation=conversation)[:int(page_size)]

                if latest_message_id:
                    messages = Message.objects.filter(conversation=conversation, id__lt=int(latest_message_id))[
                               :int(page_size)]

                serializer = MessagingMessageSerializer(messages, many=True)
                return serializer.data


    # Function to get Room Group names for the user.
    @database_sync_to_async
    def get_user_chats_room_names(self, msg_user):
        room_group_names = []
        personal_chats = Conversation.objects.filter(Q(initiator=msg_user) | Q(receiver=msg_user)).values_list(
            'room_group_name',
            flat=True)
        room_group_names.extend(personal_chats)

        if self.client:
            # Use schema_context to wrap the query
            with schema_context(self.client.schema_name):
                # Efficiently fetch business group chats related to the current user within the client's schema
                business_group_chats = BusinessGroup.objects.filter(members=msg_user).values_list('room_group_name',
                                                                                                  flat=True)
                room_group_names.extend(business_group_chats)

        group_chats = Group.objects.filter(members=msg_user).values_list('room_group_name', flat=True)
        room_group_names.extend(group_chats)

        return room_group_names
