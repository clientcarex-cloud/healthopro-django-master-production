from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (StartPersonalChatAPIView, GetPersonalChatAPIView,
                    PersonalChatListAPIView, MessageListCreateInPersonalChat,
                    MessageRetrieveUpdateDestroyInPersonalChatAPIView, UsersListView,
                    GroupListView, UserAccountView, AddGroupMembersAPIView, CombinedChatView,
                    RemoveGroupMembersAPIView, GetGroupView, MessageListCreateInGroupChat, SelfRemoveFromGroup,
                    AddAdminsToGroupAPIView, UsersSearchView, UserReadMessages, UserEditView, GroupEditView,
                    UserReadConfirmationInGroup, MessagingUserView, RemoveAdminAccessGroupAPIView,GetAllMessagesCount)


from rest_framework.routers import DefaultRouter

# router = DefaultRouter()
# router.register('group', GroupListView, basename='group_list')

# adding members path  "group/<int:group_id>/add-members/"
# remove members path  "group/<int:group_id>/remove-members/"

urlpatterns = [
    # path('', include(router.urls)),
    # getting all users
    path('check_message_user/<int:pro_user_id>/', MessagingUserView.as_view(), name = 'message-user-view'),
    path('user_list_create/', UsersListView.as_view(), name='Users-list'),
    path('user_search/', UsersSearchView.as_view(), name='users-search'),
    path('get_user/<int:pk>/', UserAccountView.as_view(), name='User-edit'),

    path('start_personal_chat/', StartPersonalChatAPIView.as_view(), name='start_convo'),
    path('personal_chat_list/<int:convo_id>/', GetPersonalChatAPIView.as_view(), name='get_personal_chat'),
    path('personal_chat_list/', PersonalChatListAPIView.as_view(), name='conversations'),

    path('group_list_create/', GroupListView.as_view(), name='group-list'),
    path('get_group/<int:pk>/', GetGroupView.as_view(), name='group-view'), # edit also we pass name and dp
    path('add_members_to_group/<int:pk>/', AddGroupMembersAPIView.as_view(), name='add_members_to_group'),
    path('give_admin_access/<int:pk>/', AddAdminsToGroupAPIView.as_view(), name='add_members_to_group'),

    path('remove_admin_access/<int:pk>/', RemoveAdminAccessGroupAPIView.as_view(), name='add_members_to_group'),

    path('remove_members_in_group/<int:pk>/', RemoveGroupMembersAPIView.as_view(), name='remove_members_in_group'),

    path('message_list_in_group/<int:group_id>/', MessageListCreateInGroupChat.as_view(), name='message-list-view'),
    path('message_list_in_convo/<int:convo_id>/', MessageListCreateInPersonalChat.as_view(), name='message-list-view'),

    path('message/<int:pk>/', MessageRetrieveUpdateDestroyInPersonalChatAPIView.as_view(), name='Message_detail'),

    path('combined_chat/', CombinedChatView.as_view(), name='combined-chat'),

    path('remove_self_in_group/<int:pk>/', SelfRemoveFromGroup.as_view(), name='user-self-remove-from-group'),

    path('user_edit/<int:pk>/', UserEditView.as_view(), name='user_dp_view'),
    path('group_edit/<int:pk>/', GroupEditView.as_view(), name='group_edit_view'),
    # path('mark_as_read/', mark_as_read, name="user_marking_message_as_read"
    path('user_read_confirmation_chat/', UserReadMessages.as_view(), name='user_read_confirmation'),
    path('user_read_confirmation_group/', UserReadConfirmationInGroup.as_view(), name='user_read_confirmation'),
    path('total_messages_count/',GetAllMessagesCount.as_view(), name='total_messages_count'),
]
