from datetime import datetime, timedelta

import jwt
from django.core.cache import cache
from django.utils import timezone
from rest_framework import generics, permissions, viewsets
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

from healtho_pro import settings
from healtho_pro_user.models.business_models import BusinessProfiles
from healtho_pro_user.models.universal_models import ProDoctor, ProDoctorProfessionalDetails
from healtho_pro_user.models.users_models import HealthOProUser, OTP, ULoginSliders, UserTenant, Client
from healtho_pro_user.serializers.users_serializers import UserSerializer, CustomUserSerializer, \
    ULoginSlidersSerializer, DoctorSerializer
from pro_laboratory.models.global_models import LabStaff, LabStaffRole
from pro_universal_data.views import send_webbased_whatsapp_message, send_sms
from rest_framework_simplejwt.views import TokenObtainPairView
import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
import random
import string

User = get_user_model()
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CreateUserView(generics.CreateAPIView):
    model = HealthOProUser
    permission_classes = [permissions.AllowAny]
    serializer_class = UserSerializer

    def perform_create(self, serializer):
        user = serializer.save()
        otp_code = ''.join(random.choices(string.digits, k=4))
        OTP.objects.create(pro_user_id=user, otp_code=otp_code)

        send_webbased_whatsapp_message(user.phone_number, otp_code)
        send_sms(user.phone_number, f"{otp_code} | HealthO Pro")  # Send SMS

        logger.info(f'OTP sent to {user.phone_number}: {otp_code}')


class LoginView(TokenObtainPairView):
    pass



class ResendOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        phone_number = request.data.get('phone_number')
        try:
            user = HealthOProUser.objects.get(phone_number=phone_number)
            otp_obj = OTP.objects.get(pro_user_id=user)

            if otp_obj.can_resend():
                new_otp = ''.join(random.choices(string.digits, k=4))
                otp_obj.reset_otp(new_otp)
                send_webbased_whatsapp_message(user.phone_number, new_otp)  # Send the new OTP
                send_sms(user.phone_number, f"{new_otp} | HealthO Pro")  # Send SMS
                return Response({'message': 'New OTP sent'}, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'OTP resend request too soon'}, status=status.HTTP_400_BAD_REQUEST)

        except HealthOProUser.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        except OTP.DoesNotExist:
            # Handle case where OTP record does not exist
            return Response({'error': 'OTP not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # Log the exception or handle it as needed
            logger.error(f"Unexpected error: {str(e)}")
            return Response({'error': 'An unexpected error occurred'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SendOTPToResetPassword(APIView):
    def post(self, request, *args, **kwargs):
        try:
            phone_number = request.data.get('phone_number')
            user = HealthOProUser.objects.get(phone_number=phone_number)
            otp_obj = OTP.objects.get(pro_user_id=user)

            new_otp = ''.join(random.choices(string.digits, k=4))
            otp_obj.reset_otp(new_otp)

            try:
                # send_webbased_whatsapp_message(user.phone_number, new_otp)  # Send the new OTP
                send_sms(user.phone_number, f"{new_otp} | HealthO Pro")  # Send SMS
                return Response({'message': 'OTP sent successfully to set/reset the password!'},
                                status=status.HTTP_200_OK)
            except Exception as error:
                print(error)
                return Response({'message': f"{error}"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as error:
            print(error)
            return Response({'message': f"{error}"}, status=status.HTTP_400_BAD_REQUEST)


class SetPasswordForUser(APIView):
    def post(self, request, *args, **kwargs):
        phone_number = request.data.get('phone_number')
        password = request.data.get('password')
        otp_code = request.data.get('otp')

        try:
            user = HealthOProUser.objects.get(phone_number=phone_number)
            otp_obj = OTP.objects.get(pro_user_id=user)
            if otp_obj.is_expired():
                return Response({'error': 'OTP expired'}, status=status.HTTP_400_BAD_REQUEST)

            if otp_obj.attempts >= 3:
                return Response({'error': 'Too many attempts with Wrong OTP!'}, status=status.HTTP_400_BAD_REQUEST)

            otp_obj.increment_attempts()
            if otp_obj.otp_code == otp_code:
                user.username = user.phone_number
                user.set_password(password)
                user.save()

                print('started deleting cache')
                try:
                    cache_key = f"user_login_data_{user.phone_number}_"
                    for key in cache.keys(f"{cache_key}*"):
                        cache.delete(key)
                        print(f"Deleted cache:{key}")
                except Exception as e:
                    print(f"Error occurred while invalidating cache: {str(e)}")

                return Response({"message": "Password is set successfully"})

            else:
                return Response({"message": 'Invalid OTP!'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            return Response({"message": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)


class UserLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        try:
            phone_number = request.data.get('phone_number')
            password = request.data.get('password')
            otp_code = request.data.get('otp')

            if not (password or otp_code):
                if not password:
                    return Response({"Error":"Password is not Entered!"}, status=status.HTTP_400_BAD_REQUEST)
                elif not otp_code:
                    return Response({"Error":"OTP is not Entered!"}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({"Error": "OTP/Password is not Entered!"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                user = HealthOProUser.objects.get(phone_number=phone_number)
                otp_obj = OTP.objects.get(pro_user_id=user)

                if password:
                    if not user.password:
                        return Response({"Error": "Password is not set for the User, Login with OTP!"},
                                        status=status.HTTP_400_BAD_REQUEST)

                    if otp_obj.password_attempts >= 5:
                        return Response({'error': 'Too many attempts with wrong password, try to login with OTP!'},
                                        status=status.HTTP_400_BAD_REQUEST)

                    if not user.check_password(password):
                        otp_obj.increment_password_attempts()
                        return Response({'error': 'Invalid password'}, status=status.HTTP_400_BAD_REQUEST)


                elif otp_code:
                    if otp_obj.is_expired():
                        return Response({'error': 'OTP expired'}, status=status.HTTP_400_BAD_REQUEST)

                    if otp_obj.attempts >= 3:
                        return Response({'error': 'Too many attempts'}, status=status.HTTP_400_BAD_REQUEST)

                    otp_obj.increment_attempts()
                    if otp_obj.otp_code == otp_code:
                        otp_obj.reset_otp(otp_code)
                    else:
                        return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)

                blacklist_user_tokens(user)
                user.last_login = timezone.now()
                user.save()

                public_tenant = Client.objects.get(name='Public')
                user_tenants_without_public = UserTenant.objects.filter(user=user).prefetch_related('client').exclude(
                    client=public_tenant)
                if (user.user_type.id == 3 or user.user_type.id == 2) and user_tenants_without_public:
                    user_tenants = UserTenant.objects.filter(user=user).prefetch_related('client')
                    tenants_list = []
                    for ut in user_tenants:
                        try:
                            business = BusinessProfiles.objects.get(organization_name=ut.client.name)

                            try:
                                with schema_context(ut.client.schema_name):
                                    lab_staff = LabStaff.objects.get(mobile_number=user.phone_number)
                                    lab_staff_role = LabStaffRole.objects.get(id=lab_staff.role_id)
                            except LabStaff.DoesNotExist:
                                continue

                            business_logo_url = business.b_logo if business.b_logo else None

                            if business.is_account_disabled:
                                refresh_token = ""
                                access_token = ""
                            else:
                                refresh = RefreshToken.for_user(user)
                                refresh['client_id'] = str(ut.client.id)
                                access = refresh.access_token

                                refresh_token = str(refresh)
                                access_token = str(access)

                            tenants_list.append({
                                "pro_user_id": user.id,
                                'client_id': ut.client.id,
                                'client_name': ut.client.name,
                                "business_logo": business_logo_url,
                                "b_id": business.id,
                                "business_name": business.organization_name,
                                "is_account_disabled": business.is_account_disabled,
                                "provider_type": business.provider_type.id,
                                "lab_staff_id": lab_staff.id,
                                "lab_staff_name": lab_staff.name,
                                "lab_staff_role": lab_staff_role.name,
                                "is_superadmin": lab_staff.is_superadmin,
                                "is_active": lab_staff.is_active,
                                "is_login_access": lab_staff.is_login_access,
                                'refresh': refresh_token,
                                'access': access_token,
                            })
                        except Exception as error:
                            print(error)

                    response_data = {
                        'message': 'User verified. Tokens generated for each tenant.',
                        'tenants': tenants_list,
                    }
                    return Response(response_data, status=status.HTTP_200_OK)

                if user.user_type.id == 1:
                    refresh = RefreshToken.for_user(user)
                    pro_doctor = ProDoctor.objects.get(pro_user_id=user)
                    pro_doctor_professional_details = ProDoctorProfessionalDetails.objects.get(
                        pro_doctor=pro_doctor)
                    doctor_details = []
                    doctor_details.append({
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                        'pro_user_id': pro_doctor.pro_user_id.id,
                        'pro_doctor_id': pro_doctor.id,
                        'user_type': user.user_type.id
                    })
                    return Response({"doctors_data": doctor_details}, status=status.HTTP_200_OK)

                if user.user_type.id == 2 and not user_tenants_without_public:
                    refresh = RefreshToken.for_user(user)
                    healthcare_professional_details = []
                    healthcare_professional_details.append({
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                        'user_type': user.user_type.id
                    })
                    return Response({"healthcare_professional_data": healthcare_professional_details},
                                    status=status.HTTP_200_OK)
            except HealthOProUser.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
            except LabStaff.DoesNotExist:
                return Response({'error': 'LabStaff not found'}, status=status.HTTP_404_NOT_FOUND)
            except LabStaffRole.DoesNotExist:
                return Response({'error': 'LabStaffRole not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as error:
            print('in exception code of login',error)
            return Response({'error': f'{error}'}, status=status.HTTP_400_BAD_REQUEST)


class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = HealthOProUser.objects.all()
    serializer_class = CustomUserSerializer


def blacklist_user_tokens(user):
    one_day_ago = datetime.now() - timedelta(days=1)
    user_tokens = OutstandingToken.objects.filter(user=user, created_at__gte=one_day_ago)

    for token in user_tokens:
        BlacklistedToken.objects.get_or_create(token=token)


class BlacklistExistingLoginsView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            user= request.user
            client = request.client
            print(user, client)
            if user:
                one_day_ago = datetime.now() - timedelta(days=1)
                last_token = OutstandingToken.objects.filter(user=user).last()
                user_tokens = OutstandingToken.objects.filter(user=user, created_at__gte=one_day_ago).exclude(
                                                                id=last_token.id)
                if client:
                    for token in user_tokens:
                        print(token.token)
                        decoded_token =  jwt.decode(token.token, settings.SECRET_KEY, algorithms=['HS256'])
                        print(decoded_token)
                        token_client_id = decoded_token.get("client_id")
                        print(token_client_id, client.id)

                        if token_client_id == str(client.id):
                            print('toekn deleted')
                            BlacklistedToken.objects.get_or_create(token=token)

                else:
                    for token in user_tokens:
                        BlacklistedToken.objects.get_or_create(token=token)

            return Response({"Status":"Existing Logins Blacklisted!"})

        except Exception as error:
            print(error)
            return Response({"Error":f"{error}"}, status=status.HTTP_400_BAD_REQUEST)




class DirectOTPLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        phone_number = request.data.get('phone_number')

        if not phone_number:
            return Response({'error': 'Mobile number is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Retrieve the user and their tenant
            user = HealthOProUser.objects.get(phone_number=phone_number)

            otp_obj = OTP.objects.get(pro_user_id=user)

            if otp_obj.can_resend():
                new_otp = ''.join(random.choices(string.digits, k=4))
                otp_obj.reset_otp(new_otp)
                try:
                    # send_webbased_whatsapp_message(user.phone_number, new_otp)  # Send the new OTP
                    send_sms(user.phone_number, f"{new_otp} | HealthO Pro")  # Send SMS
                    return Response({'message': 'New OTP sent'}, status=status.HTTP_200_OK)
                except Exception as error:
                    print(error)
                    return Response({'message': f"{error}"})
            else:
                return Response({'error': 'OTP resend request too soon (after few seconds)'},
                                status=status.HTTP_400_BAD_REQUEST)

        except HealthOProUser.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        except OTP.DoesNotExist:
            # Handle case where OTP record does not exist
            return Response({'message': 'OTP record does not exist'}, status=status.HTTP_404_NOT_FOUND)


class ULoginSlidersViewSet(viewsets.ModelViewSet):
    queryset = ULoginSliders.objects.all()
    serializer_class = ULoginSlidersSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.db import connection, models, transaction
from django.http import JsonResponse


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_tenant_info(request):
    tenant_id = getattr(request.user, 'client_id', 'No tenant ID found')
    schema_name = connection.schema_name
    return JsonResponse({
        'tenant_id': tenant_id,
        'schema_name': schema_name
    })


class GetDoctorsListApiView(generics.ListAPIView):
    queryset = HealthOProUser.objects.filter(user_type=1)
    serializer_class = DoctorSerializer
