import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "healtho_pro.settings")

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

django_asgi_app = get_asgi_application()

from cloud_messaging.routing import websocket_urlpatterns
from healtho_pro_user.middlewares import WebsocketAuthenticationMiddleware

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.


application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            WebsocketAuthenticationMiddleware(
                AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
            )
        ),
    }
)
