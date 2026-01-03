from urllib.parse import parse_qs

import jwt
from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from django.http import HttpResponseForbidden

from healtho_pro_user.models.users_models import HealthOProMessagingUser
from healtho_pro_user.models.users_models import HealthOProUser, Client


def get_token_from_request(request):
    """
    Extracts the JWT token from the request's Authorization header.
    """
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]  # Strip 'Bearer ' from the beginning
    return None


def get_user_from_token(token):
    """
    Decodes the JWT token to get the user.
    """
    try:
        decoded_data = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = decoded_data.get('user_id')
        # print(user_id)
        # print('userid')
        # print(type(user_id))
        User = get_user_model()

        # if user_id==1:
        #     print('inside')
        #     jti_secret_key=decoded_data.get('jti')
        #     if jti_secret_key != settings.HEALTHO_SECRET_KEY:
        #         raise PermissionDenied("Invalid token to access data for Mobile Application")
        #     else:
        #         pass

        return User.objects.get(id=user_id)
    except jwt.ExpiredSignatureError:
        raise PermissionDenied("Token has expired")
    except jwt.InvalidTokenError:
        raise PermissionDenied("Invalid token")
    except User.DoesNotExist:
        raise PermissionDenied("User does not exist")


def jwt_authentication_middleware(get_response):
    def middleware(request):
        token = get_token_from_request(request)

        if token:
            try:
                user = get_user_from_token(token)

                # Assuming session_id is stored in the user model; adjust if it's stored elsewhere
                session_id = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"]).get('session_id')

                if user.session_id != session_id:
                    raise PermissionDenied("Token invalid or expired")

                # url_list = ['/user/businessprofiles/']
                # print(request.path)

                #
                # if user.id==1:
                #     if request.path not in url_list:
                #         raise PermissionDenied("no access for this url")

            except HealthOProUser.DoesNotExist:
                raise PermissionDenied("No active session found")
            except PermissionDenied as e:
                return JsonResponse({'error': str(e)}, status=403)

        return get_response(request)

    return middleware


import logging

logger = logging.getLogger(__name__)


def get_schema_name_from_tenant_id(client_id):
    try:
        tenant = Client.objects.get(id=client_id)
        return tenant.schema_name
    except Client.DoesNotExist:
        raise ValueError("Invalid Client/Tenant ID")


class TenantContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Extract the token from the Authorization header
        token = request.META.get('HTTP_AUTHORIZATION', '').split(' ')[-1]

        # Decode the token to extract the client_id
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        except jwt.InvalidTokenError:
            payload = {}

        client_id = payload.get('client_id')

        if client_id:
            try:
                request.client=Client.objects.get(pk=client_id)
                # Assuming get_schema_name_from_tenant_id is a function that retrieves the schema name
                schema_name = get_schema_name_from_tenant_id(client_id)
                if schema_name:
                    connection.set_schema(schema_name)

            except Client.DoesNotExist:
                # If the client doesn't exist, handle accordingly
                pass
        else:
            request.client = None

        response = self.get_response(request)

        # Reset the schema after the response is generated
        connection.set_schema_to_public()

        return response


from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.exceptions import AuthenticationFailed


# from channels.middleware import BaseMiddleware
# from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.exceptions import AuthenticationFailed

class WebsocketAuthenticationMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        try:
            token = self.get_token_from_scope(scope)
            user, client, msg_user = await self.authenticate_user_async(token)
            scope['user'] = user  # Set the authenticated user in the scope
            scope['client'] = client  # Set the authenticated user in the scope
            scope['msg_user'] = msg_user  # Set the authenticated user in the scope
        except AuthenticationFailed:
            raise AuthenticationFailed('Authentication failed')  # Terminate the connection if authentication fails

        return await super().__call__(scope, receive, send)


    def get_token_from_scope(self, scope):
        # Extract token from the headers
        print(scope)
        # headers = dict(scope['headers'])
        # token = None
        # if b'token' in headers:
        #     token = headers[b'token'].decode('utf-8')
        #
        # return token

        query_string = scope['query_string'].decode('utf-8')
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]  # Get the token from the query parameters
        return token


    @database_sync_to_async
    def authenticate_user_async(self, token):
        return self.authenticate_user(token)

    def authenticate_user(self, token):
        if not token:
            raise AuthenticationFailed('Token not provided')

        try:
            decoded_token = AccessToken(token)
            user_id = decoded_token['user_id']
            User = get_user_model()
            user = User.objects.get(id=user_id)
            client_id = decoded_token.get('client_id', None)

            if client_id:
                client = Client.objects.get(pk=client_id)
                try:
                    msg_user = HealthOProMessagingUser.objects.get(pro_user=user, client=client)
                except HealthOProMessagingUser.DoesNotExist:
                    msg_user=HealthOProMessagingUser.objects.create(pro_user=user, client=client)

            else:
                client = None
                try:
                    msg_user = HealthOProMessagingUser.objects.get(pro_user=user, client__isnull=True)
                except HealthOProMessagingUser.DoesNotExist:
                    msg_user=HealthOProMessagingUser.objects.create(pro_user=user, client=client)

            return user, client, msg_user
        except Exception as e:
            raise AuthenticationFailed('Invalid or expired token') from e