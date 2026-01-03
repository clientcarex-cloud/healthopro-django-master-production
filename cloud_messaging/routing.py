
from django.urls import re_path

from cloud_messaging import consumers

websocket_urlpatterns = [
    re_path(r"ws_chat/", consumers.ChatConsumer.as_asgi()),
]