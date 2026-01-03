import datetime

from django.http import HttpResponse
from django.utils import timezone


def home(request):
    try:
        return HttpResponse(
        "Hi HealthO Team, We all together working on this project for bringing Revolutionize into Healthcare [For Developers]")
    except Exception as error:
        print(error)
        return HttpResponse(str(error))


import jwt
from django.conf import settings
import uuid  # For generating unique IDs


def generate_access_token():
    # Generate a unique JWT ID (jti)
    jwt_id = str(uuid.uuid4())

    # Define the payload for the token
    payload = {
        'token_type': 'access',
        'jti': jwt_id,  # Include the JWT ID (jti)
        'exp':1749097969,
        'user_id':1
    }

    # Generate token using specified secret key and algorithm
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

    return token

#
# # Usage example:
# token = generate_access_token()
# print("Generated Access Token:", token)
#
# decoded_data = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
# print(decoded_data)
