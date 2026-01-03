from datetime import timedelta, datetime
from django.utils import timezone
from django.utils.text import slugify
from django_filters.rest_framework import DjangoFilterBackend
from django_tenants.utils import schema_context
from rest_framework import status, generics
from rest_framework.exceptions import ValidationError
from rest_framework.generics import (CreateAPIView, RetrieveAPIView,
                                     ListAPIView, ListCreateAPIView,
                                     RetrieveUpdateAPIView, DestroyAPIView)
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from business_messaging.models import BusinessGroup
from healtho_pro.pagination import MessagePagination
from healtho_pro_user.models.users_models import HealthOProUser, HealthOProMessagingUser
from .models import Conversation, Message, Group, MessageReadStatus
from rest_framework.response import Response
from .serializers import (MessagingConversationSerializer,
                          UserEditSerializer, GroupEditSerializer, UserReadConfirmationGroupSerializer,
                          UserReadConfirmationChatSerializer, HealthOProMessagingUserListSerializer,
                          MessagingGroupSerializer, MessagingMessageSerializer)

from django.db.models import Q
from django.http import JsonResponse
from asgiref.sync import async_to_sync
from .models import Message
from django.db.models import Max


# Fetching conversations list order by latest message
def get_conversation_list_by_latest_message(user):
    conversations = Conversation.objects.filter(
        Q(initiator=user) | Q(receiver=user)
    ).annotate(latest_message_time=Max('messages__timestamp')
               ).prefetch_related('messages')

    for convo in conversations:
        convo.latest_message = convo.messages.last()

    return conversations


# Fetching group list order by latest message
def get_group_list_by_latest_message(user):
    groups = Group.objects.filter(
        members=user
    ).annotate(latest_message_time=Max('messages__timestamp')
               ).prefetch_related('messages')

    for group in groups:
        group.latest_message = group.messages.last()

    return groups


# check pro_user existed in messaging or not
class MessagingUserView(RetrieveAPIView):
    serializer_class = HealthOProMessagingUserListSerializer

    def retrieve(self, request, *args, **kwargs):
        pro_user_id = self.kwargs.get('pro_user_id')

        # Check if a messaging user exists for the provided pro_user ID
        try:
            messaging_user = HealthOProMessagingUser.objects.get(pro_user__id=pro_user_id)
            serializer = self.get_serializer(messaging_user)
            return Response([serializer.data])
        except HealthOProMessagingUser.DoesNotExist:
            return Response([])

# class MessagingUserView(RetrieveAPIView):
#     serializer_class = HealthOProMessagingUserListSerializer
#
#     def retrieve(self, request, *args, **kwargs):
#         pro_user_id = self.kwargs.get('pro_user_id')
#
#         # Reference the Firebase users node
#         users_ref = db.reference("users")
#
#         # Fetch all users from Firebase
#         all_users = users_ref.get()
#
#         # Check if a user exists for the provided pro_user_id
#         user_data = None
#         if all_users:
#             for user_id, user_info in all_users.items():
#                 if user_info.get("pro_user_id") == pro_user_id:
#                     user_data = user_info
#                     break
#
#         # Return the user data if found, otherwise return an empty list
#         if user_data:
#             return Response([user_data], status=status.HTTP_200_OK)
#         else:
#             return Response([], status=status.HTTP_404_NOT_FOUND)
#

class UsersSearchView(ListAPIView):
    queryset = HealthOProMessagingUser.objects.all()
    serializer_class = HealthOProMessagingUserListSerializer

    def list(self, request, *args, **kwargs):
        queryset=HealthOProMessagingUser.objects.all()
        username = request.query_params.get('username', '')
        if username:
            users = queryset.filter(username__icontains=username)
        else:
            users = queryset

        serializer = self.get_serializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# class UsersSearchView(ListAPIView):
#     serializer_class = HealthOProMessagingUserListSerializer
#
#     def list(self, request, *args, **kwargs):
#         # Retrieve query parameter
#         username = request.query_params.get('username', '')
#
#         # Reference the Firebase users node
#         users_ref = db.reference("users")
#
#         # Fetch all users from Firebase
#         all_users = users_ref.get()
#
#         # Filter users based on the username
#         if username:
#             filtered_users = [
#                 user_data for user_id, user_data in all_users.items()
#                 if username.lower() in user_data.get('username', '').lower()
#             ]
#         else:
#             filtered_users = list(all_users.values()) if all_users else []
#
#         # Return the filtered users
#         return Response(filtered_users, status=status.HTTP_200_OK)


# getting all users
class UsersListView(ListCreateAPIView):
    queryset = HealthOProMessagingUser.objects.all()
    serializer_class = HealthOProMessagingUserListSerializer

    def create(self, request, *args, **kwargs):
        current_user = self.request.user
        username = request.data.get('username')

        # Check if the user already exists
        if HealthOProMessagingUser.objects.filter(pro_user=current_user).exists():
            raise ValidationError("You already have an account")

        # Append '@healtho' to the username if it doesn't already have it
        if not username.endswith('@healtho'):
            username = f"{username}@healtho"

        data = request.data.copy()
        data['username'] = username

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(pro_user=current_user)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

# class UsersListView(ListCreateAPIView):
#     queryset = HealthOProMessagingUser.objects.all()
#     serializer_class = HealthOProMessagingUserListSerializer
#
#     def create(self, request, *args, **kwargs):
#         current_user = self.request.user
#         username = request.data.get('username')
#
#         # Check if user already exists in Firebase
#         try:
#             firebase_user = auth.get_user_by_email(f"{current_user.email}")
#             if firebase_user:
#                 raise ValidationError("You already have an account in Firebase.")
#         except auth.UserNotFoundError:
#             pass  # User doesn't exist, proceed with creation.
#
#         # Append '@healtho' to the username if necessary
#         if not username.endswith('@healtho'):
#             username = f"{username}@healtho"
#
#         # Create Firebase user
#         firebase_user = auth.create_user(
#             email=f"{current_user.email}",
#             display_name=username
#         )
#
#         # Store user details in Firebase Realtime Database
#         user_data = {
#             "user_id": firebase_user.uid,
#             "username": username,
#             "email": current_user.email,
#         }
#         db.reference("users").child(firebase_user.uid).set(user_data)
#
#         return Response(user_data, status=status.HTTP_201_CREATED)



# Retrieve user and update username
class UserAccountView(RetrieveAPIView):
    queryset = HealthOProMessagingUser.objects.all()
    serializer_class = HealthOProMessagingUserListSerializer
    lookup_url_kwarg = 'pk'
    permission_classes = [IsAuthenticated]

# class UserAccountView(RetrieveAPIView):
#     serializer_class = HealthOProMessagingUserListSerializer
#     permission_classes = [IsAuthenticated]
#     lookup_url_kwarg = 'pk'  # Use 'pk' as the lookup parameter
#
#     def retrieve(self, request, *args, **kwargs):
#         # Get the primary key (user ID) from the URL
#         user_id = self.kwargs.get(self.lookup_url_kwarg)
#
#         # Reference the Firebase users node
#         users_ref = db.reference("users")
#
#         # Fetch all users from Firebase
#         all_users = users_ref.get()
#
#         # Find the user data by ID
#         user_data = None
#         if all_users:
#             user_data = all_users.get(user_id)
#
#         # If user data is found, return it; otherwise, return a 404 response
#         if user_data:
#             return Response(user_data, status=200)
#         else:
#             return Response({"detail": "User not found"}, status=404)


class StartPersonalChatAPIView(CreateAPIView):
    serializer_class = MessagingMessageSerializer

    def create(self, request, *args, **kwargs):
        current_user = self.request.user
        try:
            sender = HealthOProMessagingUser.objects.get(pro_user=current_user)
        except HealthOProMessagingUser.DoesNotExist:
            return Response({'message': 'Sender does not exist'}, status=status.HTTP_400_BAD_REQUEST)

        receiver_id = request.data.get('receiver')
        message_text = request.data.get('text')

        if not receiver_id or not message_text:
            return Response({'message': 'Receiver and text are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            receiver = HealthOProMessagingUser.objects.get(id=receiver_id)
        except HealthOProMessagingUser.DoesNotExist:
            return Response({'message': 'Receiver does not exist'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if a conversation already exists
        conversation = Conversation.objects.filter(
            Q(initiator=sender, receiver=receiver) | Q(initiator=receiver, receiver=sender)
        ).first()

        if not conversation:
            # Create a new conversation if it doesn't exist
            conversation = Conversation.objects.create(initiator=sender, receiver=receiver)

        # Create a new message in the conversation
        message = Message.objects.create(conversation=conversation, sender=sender, text=message_text)

        # Serialize the conversation and message data with context
        conversation_serializer = MessagingConversationSerializer(conversation, context={'request': request})
        message_serializer = self.get_serializer(message, context={'request': request})

        response_data = {
            'conversation': conversation_serializer.data,
            'message': message_serializer.data
        }

        return Response(response_data, status=status.HTTP_201_CREATED)

#
# class StartPersonalChatAPIView(CreateAPIView):
#     serializer_class = MessagingMessageSerializer
#
#     def create(self, request, *args, **kwargs):
#         current_user = self.request.user
#
#         # Retrieve sender details
#         try:
#             sender = HealthOProMessagingUser.objects.get(pro_user=current_user)
#             sender_data = {"id": sender.id, "username": sender.username}
#         except ObjectDoesNotExist:
#             return Response({'message': 'Sender does not exist'}, status=status.HTTP_400_BAD_REQUEST)
#
#         receiver_id = request.data.get('receiver')
#         message_text = request.data.get('text')
#
#         if not receiver_id or not message_text:
#             return Response({'message': 'Receiver and text are required'}, status=status.HTTP_400_BAD_REQUEST)
#
#         # Retrieve receiver details
#         try:
#             receiver = HealthOProMessagingUser.objects.get(id=receiver_id)
#             receiver_data = {"id": receiver.id, "username": receiver.username}
#         except ObjectDoesNotExist:
#             return Response({'message': 'Receiver does not exist'}, status=status.HTTP_400_BAD_REQUEST)
#
#         # Reference Firebase chat node
#         chats_ref = db.reference("chats")
#
#         # Check if a conversation already exists
#         conversation_key = None
#         all_conversations = chats_ref.get()
#
#         if all_conversations:
#             for key, value in all_conversations.items():
#                 participants = value.get("participants", [])
#                 if {sender_data['id'], receiver_data['id']} == set(participants):
#                     conversation_key = key
#                     break
#
#         if not conversation_key:
#             # Create a new conversation if it doesn't exist
#             conversation_key = chats_ref.push({
#                 "participants": [sender_data['id'], receiver_data['id']],
#                 "messages": []
#             }).key
#
#         # Add the new message to the conversation
#         message_data = {
#             "sender": sender_data['id'],
#             "text": message_text,
#             "timestamp": db.SERVER_TIMESTAMP
#         }
#         chats_ref.child(conversation_key).child("messages").push(message_data)
#
#         # Response with conversation and message details
#         response_data = {
#             "conversation": {
#                 "id": conversation_key,
#                 "participants": [sender_data, receiver_data]
#             },
#             "message": message_data
#         }
#
#         return Response(response_data, status=status.HTTP_201_CREATED)



# getting one particular conversation by passing conversation_id
class GetPersonalChatAPIView(RetrieveAPIView):
    queryset = Conversation.objects.all()
    serializer_class = MessagingConversationSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'convo_id'
    pagination_class = MessagePagination

    def retrieve(self, request, *args, **kwargs):
        try:
            convo_id = kwargs.get(self.lookup_url_kwarg)
            conversation = self.queryset.get(id=convo_id)

            # Ensure the requesting user is part of the conversation
            if request.user not in [conversation.initiator.pro_user, conversation.receiver.pro_user]:
                return Response({'detail': 'You do not have permission to access this conversation.'}, status=403)

            serializer = self.get_serializer(conversation)
            return Response(serializer.data)

        except Conversation.DoesNotExist:
            return Response({'detail': 'Conversation not found.'}, status=404)
        except Exception as e:
            return Response({'detail': str(e)}, status=400)


# getting current user conversation list
class PersonalChatListAPIView(ListAPIView):
    serializer_class = MessagingConversationSerializer

    def get_queryset(self):
        current_user = self.request.user
        messaging_user = HealthOProMessagingUser.objects.get(pro_user=current_user)
        return Conversation.objects.filter(Q(initiator=messaging_user) | Q(receiver=messaging_user))


# create group list
class GroupListView(ListCreateAPIView):
    serializer_class = MessagingGroupSerializer

    def get_queryset(self):
        current_user = self.request.user
        creator = HealthOProMessagingUser.objects.get(pro_user=current_user)
        return Group.objects.filter(members=creator)

    def create(self, request, *args, **kwargs):
        current_user = self.request.user
        try:
            creator = HealthOProMessagingUser.objects.get(pro_user=current_user)
        except HealthOProMessagingUser.DoesNotExist:
            return Response({'message': 'Creator does not exist'}, status=status.HTTP_400_BAD_REQUEST)

        # Create a mutable copy of the request data
        data = request.data.copy()
        data['creator'] = creator.id

        # Add the creator to the members list
        members = data.get('members', [])
        if not isinstance(members, list):
            members = []
        if creator.id not in members:
            members.append(creator.id)

        # Add the creator to the admin list
        admin = data.get('admin', [])
        if not isinstance(admin, list):
            admin = []
        if creator.id not in admin:
            admin.append(creator.id)

        data['admin'] = admin
        data['members'] = members

        serializer = self.get_serializer(data=data)

        if serializer.is_valid():
            group = serializer.save()
            # print("group", group)
            group.members.add(*members)
            group.admin.add(*admin)
            group.save()
            # print("group------", group)

            # Create the initial message if provided
            message_text = data.get('text')
            if message_text:
                message = Message.objects.create(group=group, sender=creator, text=message_text)

            # Serialize the conversation and message data with context
            conversation_serializer = MessagingGroupSerializer(group, context={'request': request})
            message_serializer = MessagingMessageSerializer(message, context={'request': request})

            response_data = {
                'conversation': serializer.data,
                'message': message_serializer.data
            }
            return Response(response_data, status=status.HTTP_201_CREATED)

        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GetGroupView(RetrieveUpdateAPIView):
    queryset = Group.objects.all()
    serializer_class = MessagingGroupSerializer
    pagination_class = MessagePagination

    def retrieve(self, request, *args, **kwargs):
        current_user = self.request.user
        try:
            messaging_user = HealthOProMessagingUser.objects.get(pro_user=current_user)
        except HealthOProMessagingUser.DoesNotExist:
            raise ValidationError("User not found")

        try:
            group_id = self.kwargs.get('pk')
            group = Group.objects.get(id=group_id)

            # check if current user in the group then access otherwise can't
            if messaging_user in group.members.all():
                serializer = self.get_serializer(group)
                return Response(serializer.data)

            else:
                raise ValidationError({"message": "You are not in this group, so you can't access it."})
        except Group.DoesNotExist:
            raise ValidationError("Group not found")

    def update(self, request, *args, **kwargs):
        try:
            messaging_user = HealthOProMessagingUser.objects.get(pro_user=self.request.user)
        except HealthOProMessagingUser.DoesNotExist:
            raise ValidationError("User not found")

        group = self.get_object()

        # Check if the user is an admin of the group
        if messaging_user in group.admin.all():
            serializer = self.get_serializer(group, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return ValidationError({"error": "You are not an admin of this group."})


class AddGroupMembersAPIView(CreateAPIView):
    queryset = Group.objects.all()
    serializer_class = MessagingGroupSerializer
    lookup_field = 'pk'

    def create(self, request, *args, **kwargs):
        current_user = self.request.user
        try:
            messaging_user = HealthOProMessagingUser.objects.get(pro_user=current_user)
        except HealthOProMessagingUser.DoesNotExist:
            return Response({"message": "User Does Not Exist"})

        group = self.get_object()
        # print("group", group)
        group_admins = group.admin.all()
        # print("group_amins", group_admins)

        if messaging_user in group_admins:
            member_ids = request.data.get("members", [])
            # print("member_ids", member_ids)

            if not isinstance(member_ids, list):
                return Response({'error': 'members must be a list of user IDs'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                users = HealthOProMessagingUser.objects.filter(id__in=member_ids)
                if not users.exists():
                    return Response({'error': 'One or more users not found'}, status=status.HTTP_404_NOT_FOUND)

                group.members.add(*users)
                group.save()

                serializer = self.get_serializer(group)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"message": "you are not admin of this group, can't add members "},
                            status=status.HTTP_400_BAD_REQUEST)


# give admin power to one or more members in that group members only
class AddAdminsToGroupAPIView(CreateAPIView):
    queryset = Group.objects.all()
    serializer_class = MessagingGroupSerializer
    lookup_field = 'pk'

    def create(self, request, *args, **kwargs):
        current_user = self.request.user
        try:
            messaging_user = HealthOProMessagingUser.objects.get(pro_user=current_user)
        except HealthOProMessagingUser.DoesNotExist:
            return Response({"message": "User Does Not Exist"})

        group = self.get_object()
        # print("group", group)
        group_admins = group.admin.all()
        # print("group_amins", group_admins)

        if messaging_user in group_admins:
            member_ids = request.data.get("members", [])

            if not isinstance(member_ids, list):
                return Response({'error': 'members must be a list of user IDs'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                users = HealthOProMessagingUser.objects.filter(id__in=member_ids)
                if not users.exists():
                    return Response({'error': 'One or more users not found'}, status=status.HTTP_404_NOT_FOUND)
                for user in users:
                    if user not in group.members.all():
                        return Response({'error': 'you only give access to members, who are in this group '})

                group.admin.add(*users)
                group.save()

                serializer = self.get_serializer(group)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"message": "you are not admin of this group "},
                            status=status.HTTP_400_BAD_REQUEST)


class RemoveAdminAccessGroupAPIView(CreateAPIView):
    queryset = Group.objects.all()
    serializer_class = MessagingGroupSerializer
    lookup_field = 'pk'

    def create(self, request, *args, **kwargs):
        current_user = self.request.user
        try:
            messaging_user = HealthOProMessagingUser.objects.get(pro_user=current_user)
        except HealthOProMessagingUser.DoesNotExist:
            return Response({"message": "User Does Not Exist"})

        group = self.get_object()
        # print("group", group)
        group_admins = group.admin.all()
        # print("group_amins", group_admins)

        if messaging_user in group_admins:
            if len(group_admins) > 1:
                admin_ids = request.data.get("admin", [])

                if not isinstance(admin_ids, list):
                    return Response({'error': 'admin must be a list of user IDs'}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    users = HealthOProMessagingUser.objects.filter(id__in=admin_ids)
                    if not users.exists():
                        return Response({'error': 'One or more users not found'}, status=status.HTTP_404_NOT_FOUND)

                    for user in users:
                        if user not in group.admin.all():
                            return Response({'error': 'Only remove admin access from admins, who are in this group'},
                                            status=status.HTTP_400_BAD_REQUEST)

                    group.admin.remove(*users)

                    group.save()
                    # return Response({"message": "admin access removed"})
                    serializer = self.get_serializer(group)
                    return Response(serializer.data, status=status.HTTP_200_OK)
                except Exception as e:
                    return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'error': 'You only the admin'},
                                status=status.HTTP_400_BAD_REQUEST)


class RemoveGroupMembersAPIView(CreateAPIView):
    queryset = Group.objects.all()
    serializer_class = MessagingGroupSerializer
    lookup_field = 'pk'

    def create(self, request, *args, **kwargs):
        current_user = self.request.user
        try:
            messaging_user = HealthOProMessagingUser.objects.get(pro_user=current_user)
        except HealthOProMessagingUser.DoesNotExist:
            return Response({"message": "User Does Not Exist"})

        group = self.get_object()

        group_admins = group.admin.all()

        if messaging_user in group_admins:
            member_ids = request.data.get('members', [])

            if not isinstance(member_ids, list):
                return Response({'error': 'members must be a list of user IDs'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                users = HealthOProMessagingUser.objects.filter(id__in=member_ids)
                if not users.exists():
                    return Response({'error': 'One or more users not found'}, status=status.HTTP_404_NOT_FOUND)

                # Remove the admin_ID from the list of member IDs if he pass his id
                if messaging_user in users:
                    users = users.exclude(id=messaging_user.id)

                group.members.remove(*users)
                group.admin.remove(*users)
                group.save()

                serializer = self.get_serializer(group)
                return Response(serializer.data, status=status.HTTP_200_OK)

            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"message": "you are not admin of this group, can't remove members "},
                            status=status.HTTP_400_BAD_REQUEST)


# get list of messages in a conversation and create view
class MessageListCreateInPersonalChat(generics.ListCreateAPIView):
    serializer_class = MessagingMessageSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = MessagePagination

    def get_queryset(self):
        conversation_id = self.kwargs.get('convo_id')
        current_user = self.request.user
        try:
            messaging_user = HealthOProMessagingUser.objects.get(pro_user=current_user)
        except HealthOProMessagingUser.DoesNotExist:
            raise ValidationError({"message": "user does not exist"})

        try:
            conversation = Conversation.objects.get(id=conversation_id)
            if messaging_user in [conversation.receiver, conversation.initiator]:
                return Message.objects.filter(conversation_id=conversation_id)
            else:
                raise ValidationError({"message": "You are not in that conversation, you can't access"})
        except Conversation.DoesNotExist:
            raise ValidationError({"message": "Conversation not found"})

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(queryset, request)
            # page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return paginator.get_paginated_response(serializer.data)

            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        current_user = self.request.user

        try:
            messaging_user = User.objects.get(pro_user=current_user)
            # print("messaging user----", messaging_user)
        except User.DoesNotExist:
            return Response({"message": "user does not exist"},status=status.HTTP_400_BAD_REQUEST)
        conversation_id = self.kwargs.get('convo_id')

        conversation = Conversation.objects.get(id=conversation_id)

        if messaging_user in [conversation.initiator, conversation.receiver]:
            serializer.save(sender=messaging_user, conversation=conversation)
            serializer.data['message'] = "Message sent successfully"
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        else:
            return Response({"message": "you are not in this conversation,so you can't send messages"},
                            status=status.HTTP_400_BAD_REQUEST)

    # def create(self, request, *args, **kwargs):
    #     response = super().create(request, *args, **kwargs)
    #
    #     response['message'] = "Message sent successfully"
    #     return Response(response.data, status=status.HTTP_201_CREATED)


class MessageRetrieveUpdateDestroyInPersonalChatAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = MessagingMessageSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        message_id = self.kwargs.get('pk')
        current_user = self.request.user
        try:
            messaging_user = HealthOProMessagingUser.objects.get(pro_user=current_user)
        except HealthOProMessagingUser.DoesNotExist:
            raise ValidationError({"message": "user does not exist"})

        # print("messaging user", messaging_user)

        try:
            message_obj = Message.objects.get(id=message_id)
            # print(message_obj, "message_obj")
            # print("messaging sender", message_obj.sender)

            if messaging_user == message_obj.sender:
                return Message.objects.filter(id=message_id)
            else:
                # If the user is not part of the conversation, raise a 404 error
                raise ValidationError("You don't have permission to access this message.")

        except Message.DoesNotExist:
            raise ValidationError({"message": 'message obj does not exists'})

    def perform_update(self, serializer):
        current_user = self.request.user
        messaging_user = User.objects.get(pro_user=current_user)
        if serializer.instance.sender != messaging_user:
            raise ValidationError("You can only update your own messages.")
        if timezone.now() - serializer.instance.timestamp > timedelta(hours=1):
            raise ValidationError("You can only edit messages within 24 hours of sending.")
        serializer.save()

        # Send message update to WebSocket clients
        # channel_layer = get_channel_layer()
        # async_to_sync(channel_layer.group_send)(
        #     f'chat_{serializer.instance.conversation_id.id}',
        #     {
        #         'type': 'update_message',
        #         'message': serializer.instance.text,
        #         'sender': current_user.id,
        #         'attachment': serializer.instance.attachment.url if serializer.instance.attachment else None,
        #         'message_id': serializer.instance.id
        #     }
        # )

    def perform_destroy(self, instance):
        current_user = self.request.user
        messaging_user = HealthOProMessagingUser.objects.get(pro_user=current_user)
        if instance.sender != messaging_user:
            raise ValidationError("You can only delete your own messages.")
        if timezone.now() - instance.timestamp > timedelta(hours=1):
            raise ValidationError("You can only delete messages within 24 hours of sending.")
        # conversation_id = instance.conversation_id.id
        instance.delete()

        # Send message delete to WebSocket clients
        # channel_layer = get_channel_layer()
        # async_to_sync(channel_layer.group_send)(
        #     f'chat_{conversation_id}',
        #     {
        #         'type': 'delete_message',
        #         'message_id': instance.id
        #     }
        # )

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        response.data["message"] = "message edited successfully"
        return JsonResponse(response.data,
                            status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        response = super().destroy(request, *args, **kwargs)
        return JsonResponse({'message': 'message deleted successfully'})


class MessageListCreateInGroupChat(generics.ListCreateAPIView):
    serializer_class = MessagingMessageSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = MessagePagination

    def get_queryset(self):
        current_user = self.request.user
        group_id = self.kwargs.get('group_id')

        try:
            messaging_user = HealthOProMessagingUser.objects.get(pro_user=current_user)
        except HealthOProMessagingUser.DoesNotExist:
            raise ValidationError({"message": "user does not exist"})

        try:
            group = Group.objects.get(id=group_id)
            if messaging_user in group.members.all():
                return Message.objects.filter(group=group)
            else:
                raise ValidationError({"message": "You are not in this group, you can't access"})
        except Group.DoesNotExist:
            raise ValidationError({"message": "Group not found"})

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(queryset, request)
            # page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return paginator.get_paginated_response(serializer.data)

            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response({"message": "Group does not exist"}, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        current_user = self.request.user

        try:
            messaging_user = HealthOProMessagingUser.objects.get(pro_user=current_user)
            # print("messaging user----", messaging_user)
        except HealthOProMessagingUser.DoesNotExist:
            raise ValidationError({"message": "user does not exist"})
        group_id = self.kwargs.get('group_id')
        try:
            group = Group.objects.get(id=group_id)
            # print("conversation users----", [member for member in group.members.all()])
        except Group.DoesNotExist:
            raise ValidationError({"message": "Group does not exist"})
        if messaging_user in group.members.all():
            serializer.save(sender=messaging_user, group=group)
        else:
            raise ValidationError({"message": "you are not in this conversation,so you can't send messages"})

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        # response.data['message'] = 'Message sent successfully'
        # return JsonResponse(response.data, status=201)
        return Response({"message": "Message sent successfully"})


# define user self remove from one group
class SelfRemoveFromGroup(DestroyAPIView):
    queryset = Group.objects.all()
    serializer_class = MessagingGroupSerializer
    lookup_field = 'pk'
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def perform_destroy(self, instance):
        current_user = self.request.user
        try:
            messaging_user = HealthOProMessagingUser.objects.get(pro_user=current_user)
        except HealthOProMessagingUser.DoesNotExist:
            raise ValidationError({"message": "User Does not Exist"})

        group = self.get_object()
        # print("group_obj ", group.name)

        group_admins = group.admin.all()
        # print("group_admins", group_admins)
        # print("admins count", len(group_admins))
        if messaging_user in group_admins:
            if len(group_admins) != 1:
                instance.members.remove(messaging_user)
                instance.admin.remove(messaging_user)
                instance.save()
            else:
                raise ValidationError({"message": "you want to remove yourself first you add a admin "})
        elif messaging_user in group.members.all():
            instance.members.remove(messaging_user)
            instance.save()
        else:
            raise ValidationError({"message": "you are not in this group"})

    def destroy(self, request, *args, **kwargs):
        group = self.get_object()
        self.perform_destroy(group)
        return Response({'message': 'You have been removed from the group successfully'}, status=status.HTTP_200_OK)




class CombinedChatView(generics.ListAPIView):
    serializer_class =  MessagingConversationSerializer # A custom serializer you'll define
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def list(self=None, msg_user=None, *args, **kwargs):
        try:
            messaging_user = msg_user

        except User.DoesNotExist:
            raise ValidationError({"message": "Messaging user does not exist"})

        conversations = get_conversation_list_by_latest_message(messaging_user)
        groups = get_group_list_by_latest_message(messaging_user)

        # Combine and sort by latest message time
        combined_chat_list = list(groups)
        default_time = datetime.min
        combined_chat_list.sort(key=lambda x: x.latest_message_time or default_time, reverse=True)

        serializer=CombinedChatSerializer(combined_chat_list,many=True, context={"msg_user":msg_user})
        return Response(serializer.data)


    def get_serializer_context(self):
        return {'request': self.request}

    def get(self, request, *args, **kwargs):
        if 'username' in request.query_params:
            return self.search_chats(request)
        else:
            return super().get(request, *args, **kwargs)

    def search_chats(self, request):

        current_user = self.request.user
        # print("views---current_user", current_user)

        try:
            messaging_user = HealthOProMessagingUser.objects.get(pro_user=current_user)
        except HealthOProMessagingUser.DoesNotExist:
            raise ValidationError({"message": "Messaging user does not exist"})

        search_term = request.query_params.get('username', '').lower()
        queryset = self.get_queryset()

        # Filter the combined list based on the search term
        filtered_queryset = []
        for obj in queryset:
            if isinstance(obj, Group):
                if search_term in obj.name.lower():
                    filtered_queryset.append(obj)
            elif isinstance(obj, Conversation):
                partner = obj.receiver if obj.initiator == messaging_user else obj.initiator
                if search_term in partner.username.lower():
                    filtered_queryset.append(obj)

        page = self.paginate_queryset(filtered_queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        else:
            serializer = self.get_serializer(filtered_queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)


class UserReadMessages(generics.CreateAPIView):
    def create(msg_user=None,room_group_name=None, *args, **kwargs):
        try:
            messaging_user = msg_user
            # print("messaging_user", messaging_user)
        except User.DoesNotExist:
            return Response({"message": "User Does Not Exist"}, status=status.HTTP_404_NOT_FOUND)
        try:
            conversation = Conversation.objects.get(room_group_name=room_group_name)
        except Conversation.DoesNotExist:
            return Response({'message': "Conversation Not Found"}, status=status.HTTP_404_NOT_FOUND)

        # Check if the current user is a part of the conversation
        if messaging_user == conversation.initiator or messaging_user == conversation.receiver:
            if messaging_user == conversation.initiator:
                partner = conversation.receiver
            else:
                partner = conversation.initiator

            # Filter messages by conversation ID and check if the current user is the receiver
            messages = Message.objects.filter(conversation=conversation, sender=partner, is_read=False)

            # Update is_read status for messages
            for message in messages:
                message.is_read = True
                message.save()

            return Response({"message": "Messages updated successfully"}, status=status.HTTP_200_OK)
        else:
            return Response({'message': 'You are not in this conversation'}, status=status.HTTP_400_BAD_REQUEST)



class UserReadConfirmationInGroup(generics.CreateAPIView):
    def create(msg_user=None,room_group_name=None, *args, **kwargs):
        try:
            # Fetch the messaging user based on the authenticated user
            messaging_user = msg_user
        except User.DoesNotExist:
            return Response({"message": "User Does Not Exist"}, status=404)

        if not room_group_name:
            return Response({"message": "Group ID is required"}, status=400)

        try:
            group = Group.objects.get(room_group_name=room_group_name)
        except Group.DoesNotExist:
            return Response({"message": "Group Does Not Exist"}, status=404)

        if messaging_user not in group.members.all():
            return Response({"message": "You are not in this group"}, status=403)

        # Get all messages in the group sent by other members
        messages = Message.objects.filter(group=group).exclude(sender=messaging_user)

        # Update read status for each message for the user
        MessageReadStatus.objects.filter(
            user=messaging_user,
            message__in=messages
        ).update(is_read=True)

        return Response({"message": "message updated as read"})



class UserEditView(generics.UpdateAPIView):
    queryset = HealthOProMessagingUser.objects.all()
    serializer_class = UserEditSerializer
    lookup_url_kwarg = 'pk'

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance == HealthOProMessagingUser.objects.get(pro_user=self.request.user.id):
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            # username = serializer.validated_data.get('username')
            #
            # # Ensure username ends with '@healtho'
            # if not username.endswith('@healtho'):
            #     cleaned_username = slugify(username)
            #     username = f"{cleaned_username}@healtho"
            #
            # # Check if the username already exists
            # if User.objects.filter(username__iexact=username).exclude(id=instance.id).exists():
            #     return Response({"error": "User with this username already exists"}, status=status.HTTP_400_BAD_REQUEST)
            #
            # # Update the validated data with the cleaned username
            # serializer.validated_data['username'] = username

            # if instance.username
            serializer.save()

            return Response(serializer.data, status=status.HTTP_200_OK)
            # return Response({"message": "your profile picture updated successfully"}, status=status.HTTP_200_OK)

        else:
            return Response({"message": "This is not your profile"})


class GroupEditView(generics.UpdateAPIView):
    queryset = Group.objects.all()
    serializer_class = GroupEditSerializer
    lookup_url_kwarg = 'pk'

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        messaging_user = HealthOProMessagingUser.objects.get(pro_user=self.request.user)
        if messaging_user in instance.admin.all():
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({"message": "you are not admin"})


class GetAllMessagesCount(APIView):
    def get(self, msg_user):
        messages_count = 0
        messaging_user = msg_user
        try:
            personal_chats = Conversation.objects.filter(
                Q(initiator=messaging_user) | Q(receiver=messaging_user))
            groups = Group.objects.filter(members=messaging_user)

            # Some all messages count in all chats and
            for chat in personal_chats.all():
                # print(chat)
                serializer = MessagingConversationSerializer(chat, context={'msg_user': msg_user})
                messages_count += serializer.get_self_unread_messages(chat)
            for group in groups.all():
                serializer = MessagingGroupSerializer(group, context={'msg_user': msg_user})
                messages_count += serializer.get_current_user_unread_messages_count(group)

            if messaging_user.client:
                with schema_context(messaging_user.client.schema_name):
                    business_groups = BusinessGroup.objects.filter(members=messaging_user)
                    for group in business_groups.all():
                        serializer = MessagingGroupSerializer(group, context={'msg_user': msg_user})
                        messages_count += serializer.get_current_user_unread_messages_count(group)


            return Response({"total_messages_count": messages_count}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
