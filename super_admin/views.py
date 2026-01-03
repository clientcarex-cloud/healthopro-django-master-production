import string
from datetime import datetime, timedelta
import random
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from django_tenants.utils import schema_context
from rest_framework import status, permissions, viewsets, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from deleting_schema import delete_msg_users_of_client, delete_user_tenants_of_client, \
    delete_business_details_and_add_in_deleted, delete_schema_of_client
from healtho_pro_user.models.business_models import BusinessProfiles, GlobalMessagingSettings, GlobalBusinessSettings, \
    BusinessModules, BusinessAddresses, DeletedBusinessProfiles
from healtho_pro_user.models.subscription_models import BusinessBillCalculationType, BusinessSubscriptionPlans, \
    BusinessSubscriptionType, OverallBusinessSubscriptionStatus
from healtho_pro_user.models.users_models import HealthOProUser, Client, OTP, UserTenant
from healtho_pro_user.serializers.business_serializers import BusinessProfilesSerializer, \
    GlobalMessagingSettingsSerializer, GlobalBusinessSettingsSerializer
from healtho_pro_user.serializers.subscription_serializers import BusinessBillCalculationTypeSerializer, \
    BusinessSubscriptionTypeSerializer, OverallBusinessSubscriptionStatusSerializer
from healtho_pro_user.views.users_views import blacklist_user_tokens
from pro_laboratory.models.bulk_messaging_models import BusinessMessagesCredits
from pro_laboratory.models.client_based_settings_models import BusinessMessageSettings, BusinessControls
from pro_laboratory.models.global_models import LabStaff, LabStaffDefaultBranch
from pro_laboratory.models.messaging_models import WhatsappConfigurations
from pro_laboratory.models.patient_models import LabPatientTests, Patient
from pro_laboratory.models.subscription_data_models import BusinessSubscriptionPlansPurchased
from pro_laboratory.serializers.bulk_messaging_serializers import BusinessMessagesCreditsSerializer
from pro_laboratory.serializers.client_based_settings_serializers import BusinessControlsSerializer
from pro_laboratory.serializers.messaging_serializers import WhatsappConfigurationsSerializer
from pro_laboratory.serializers.subscription_data_serializers import \
    BusinessSubscriptionPlansPurchaseFromAdminSerializer, BusinessSubscriptionPlansPurchasedSerializer
from pro_universal_data.models import MessagingServiceTypes, ULabMenus
from pro_universal_data.serializers import ULabMenusSerializer
from pro_universal_data.views import send_webbased_whatsapp_message, send_sms
from super_admin.models import HealthOProSuperAdmin
from super_admin.serializers import HealthOProSuperAdminSerializer, BusinessLoginAccessControlSerializer, \
    BusinessProfilesForAdminSerializer, BusinessModulesSerializer, BusinessSubscriptionPlansSerializer, \
    DeletedBusinessProfilesSerializer, BusinessProfilesDeletionForAdminSerializer


#Login view
class SuperAdminLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        try:
            phone_number = request.data.get('phone_number')
            otp_code = request.data.get('otp')
            password = request.data.get('password')

            user = HealthOProUser.objects.get(phone_number=phone_number)

            super_admin = HealthOProSuperAdmin.objects.get(user=user, is_active=True)

            otp_obj = OTP.objects.get(pro_user_id=user)
            if otp_code:
                if otp_obj.is_expired():
                    return Response({'Error': 'OTP expired'}, status=status.HTTP_400_BAD_REQUEST)

                if otp_obj.attempts >= 3:
                    return Response({'Error': 'Too many attempts'}, status=status.HTTP_400_BAD_REQUEST)

                otp_obj.increment_attempts()
                if otp_obj.otp_code == otp_code:
                    otp_obj.reset_otp(otp_code)
                else:
                    return Response({'Error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)

            elif password:
                if not user.password:
                    return Response({"Error": "Password is not set for the User, Login with OTP!"},
                                    status=status.HTTP_400_BAD_REQUEST)

                if otp_obj.password_attempts >= 5:
                    return Response({'Error': 'Too many attempts with wrong password, try to login with OTP!'},
                                    status=status.HTTP_400_BAD_REQUEST)

                if user.check_password(password):
                    pass
                else:
                    otp_obj.increment_password_attempts()
                    return Response({'Error': 'Invalid password'}, status=status.HTTP_400_BAD_REQUEST)


            else:
                return Response({'Error': 'OTP or Password is mandatory!'}, status=status.HTTP_400_BAD_REQUEST)

            blacklist_user_tokens(user)
            user.last_login = timezone.now()
            user.save()

            public = Client.objects.get(name='Public')

            refresh = RefreshToken.for_user(user)
            refresh['client_id'] = str(public.id)
            access = refresh.access_token

            refresh_token = str(refresh)
            access_token = str(access)

            if super_admin:
                admin_details = {
                    "id": super_admin.id,
                    "name": super_admin.user.full_name,
                    "mobile_number": super_admin.user.phone_number,
                    "refresh": refresh_token,
                    "access": access_token
                }

                return Response(admin_details)
            else:
                return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)

        except HealthOProUser.DoesNotExist:
            return Response({"Error": "Access Denied!"}, status=status.HTTP_404_NOT_FOUND)

        except HealthOProSuperAdmin.DoesNotExist:
            return Response({"Error": "Access Denied!"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as error:
            return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)


class DirectOTPLoginViewForAdmin(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        phone_number = request.data.get('phone_number')

        if not phone_number:
            return Response({'Error': 'Mobile number is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = HealthOProUser.objects.get(phone_number=phone_number)

            super_admin = HealthOProSuperAdmin.objects.get(user=user, is_active=True)

            if super_admin:
                otp_obj = OTP.objects.get(pro_user_id=user)

                if otp_obj.can_resend():
                    new_otp = ''.join(random.choices(string.digits, k=4))
                    otp_obj.reset_otp(new_otp)
                    try:
                        send_webbased_whatsapp_message(user.phone_number, new_otp)  # Send the new OTP
                        send_sms(user.phone_number, f"{new_otp} | HealthO Pro")  # Send SMS
                        return Response({'message': 'New OTP sent'}, status=status.HTTP_200_OK)
                    except Exception as error:
                        print(error)
                        return Response({'message': f"{error}"})
                else:
                    return Response({'Error': 'OTP resend request too soon (after few seconds)'},
                                    status=status.HTTP_400_BAD_REQUEST)

        except HealthOProSuperAdmin.DoesNotExist:
            return Response({"Error": "Access Denied!"}, status=status.HTTP_404_NOT_FOUND)

        except HealthOProUser.DoesNotExist:
            return Response({"Error": "Access Denied!"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as error:
            return Response({"Error": "Access Denied!"}, status=status.HTTP_404_NOT_FOUND)


class ResendOTPViewForAdmin(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        phone_number = request.data.get('phone_number')
        try:
            user = HealthOProUser.objects.get(phone_number=phone_number)

            super_admin = HealthOProSuperAdmin.objects.get(user=user, is_active=True)

            if super_admin:
                otp_obj = OTP.objects.get(pro_user_id=user)

                if otp_obj.can_resend():
                    new_otp = ''.join(random.choices(string.digits, k=4))
                    otp_obj.reset_otp(new_otp)
                    send_sms(user.phone_number, f"{new_otp} | HealthO Pro")  # Send SMS
                    return Response({'message': 'New OTP sent'}, status=status.HTTP_200_OK)
                else:
                    return Response({'Error': 'OTP resend request too soon'}, status=status.HTTP_400_BAD_REQUEST)


        except HealthOProSuperAdmin.DoesNotExist:
            return Response({"Error": "Access Denied!"}, status=status.HTTP_404_NOT_FOUND)

        except HealthOProUser.DoesNotExist:
            return Response({"Error": "Access Denied!"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as error:
            return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)


#Superadmin Related
class HealthOProSuperAdminViewset(viewsets.ModelViewSet):
    queryset = HealthOProSuperAdmin.objects.all()
    serializer_class = HealthOProSuperAdminSerializer

    def get_queryset(self):
        try:
            user = self.request.user
            super_admin = HealthOProSuperAdmin.objects.get(is_active=True, user=user)
            queryset = HealthOProSuperAdmin.objects.all()

            if super_admin:
                return queryset

        except HealthOProSuperAdmin.DoesNotExist:
            return HealthOProSuperAdmin.objects.none()

        except Exception as error:
            return HealthOProSuperAdmin.objects.none()

    def create(self, request, *args, **kwargs):
        try:
            user = request.user
            super_admin = HealthOProSuperAdmin.objects.get(is_active=True, user=user)

            if super_admin:
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer.save()

                return Response(serializer.data)

        except HealthOProSuperAdmin.DoesNotExist:
            return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as error:
            return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            super_admin = HealthOProSuperAdmin.objects.get(is_active=True, user=self.request.user)

            if super_admin:
                instance = self.get_object()
                partial = kwargs.pop('partial', False)
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                validated_data = serializer.validated_data

                instance.is_active = validated_data['is_active']
                instance.save()

                return Response({"Status": "Changes updated!"})
            else:
                return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)

        except HealthOProSuperAdmin.DoesNotExist:
            return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as error:
            return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)


class BusinessProfilesViewSet(viewsets.ModelViewSet):
    queryset = BusinessProfiles.objects.all()
    serializer_class = BusinessProfilesForAdminSerializer
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self):
        try:
            super_admin = HealthOProSuperAdmin.objects.get(user=self.request.user, is_active=True)
            client_id = self.request.query_params.get('client_id', None)
            queryset = BusinessProfiles.objects.all().order_by('id')
            query = self.request.query_params.get('q', None)
            sort = self.request.query_params.get('sort', None)

            if client_id is not None:
                client = Client.objects.get(pk=client_id)

                queryset = BusinessProfiles.objects.filter(organization_name=client.name)

            if query is not None:
                search_query = (Q(organization_name__icontains=query) | Q(phone_number__icontains=query))
                queryset = queryset.filter(search_query)

            if sort == '-added_on':
                queryset = queryset.order_by('-added_on')
            if sort == 'added_on':
                queryset = queryset.order_by('added_on')

            return queryset
        except HealthOProSuperAdmin.DoesNotExist:
            raise ValidationError({"Error": f"Access Denied!"})

        except Exception as error:
            raise ValidationError({"Error": f"{error}"})

    def create(self, request, *args, **kwargs):
        try:
            super_admin = HealthOProSuperAdmin.objects.get(user=self.request.user, is_active=True)

            return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)

        except HealthOProSuperAdmin.DoesNotExist:
            return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as error:
            return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            super_admin = HealthOProSuperAdmin.objects.get(user=self.request.user, is_active=True)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            return Response(serializer.data, status=status.HTTP_200_OK)

        except HealthOProSuperAdmin.DoesNotExist:
            return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as error:
            return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)


class BusinessLoginAccessControl(generics.ListCreateAPIView):
    queryset = BusinessProfiles.objects.all()
    serializer_class = BusinessLoginAccessControlSerializer

    def get(self, request, *args, **kwargs):
        try:
            super_admin = HealthOProSuperAdmin.objects.get(is_active=True, user=self.request.user)
            queryset = self.get_queryset()
            b_id = self.request.query_params.get('b_id', None)
            client_id = self.request.query_params.get('client_id', None)
            query = self.request.query_params.get('q', None)
            sort = self.request.query_params.get('sort', None)

            if sort is None:
                sort = '-added_on'

            if query:
                search_query = (Q(organization_name__icontains=query) | Q(phone_number__icontains=query))
                queryset = queryset.filter(search_query)

            if sort == '-added_on':
                queryset = queryset.order_by('-added_on')
            if sort == 'added_on':
                queryset = queryset.order_by('added_on')

            if b_id:
                queryset = BusinessProfiles.objects.filter(pk=b_id)

            if client_id:
                client = Client.objects.get(pk=client_id)
                queryset = BusinessProfiles.objects.filter(organization_name=client.name)

            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)


        except HealthOProSuperAdmin.DoesNotExist:
            return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as error:
            return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, *args, **kwargs):
        try:
            super_admin = HealthOProSuperAdmin.objects.get(is_active=True, user=self.request.user)
            client_id = self.request.query_params.get('client_id')
            b_id = self.request.query_params.get('b_id')

            if not (client_id or b_id):
                return Response({"Error": "No business is selected!"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                if client_id:
                    client = Client.objects.get(pk=client_id)
                    b_id = BusinessProfiles.objects.get(organization_name=client.name)
                elif b_id:
                    b_id = BusinessProfiles.objects.get(pk=b_id)
                    client = Client.objects.get(name=b_id.organization_name)

                if b_id.is_account_disabled:
                    b_id.is_account_disabled = False
                    b_id.save()

                    return Response({"Status": f"Account is Enabled : {b_id.organization_name}"})
                else:
                    b_id.is_account_disabled = True
                    b_id.save()
                    user_tenants = UserTenant.objects.filter(client=client).select_related('client')
                    for ut in user_tenants:
                        user = ut.user
                        blacklist_user_tokens(user)
                        user.last_login = timezone.now()
                        user.save()

                    return Response({"Status": f"Account is Disabled : {b_id.organization_name}"})


        except HealthOProSuperAdmin.DoesNotExist:
            return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as error:
            return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)


class GlobalMessagingSettingsViewset(viewsets.ModelViewSet):
    queryset = GlobalMessagingSettings.objects.all()
    serializer_class = GlobalMessagingSettingsSerializer

    def get_queryset(self):
        try:
            super_admin = HealthOProSuperAdmin.objects.get(is_active=True, user=self.request.user)
            sms, created = GlobalMessagingSettings.objects.get_or_create(type=MessagingServiceTypes.objects.get(pk=1))

            whatsapp, created = GlobalMessagingSettings.objects.get_or_create(
                type=MessagingServiceTypes.objects.get(pk=2))

            return self.queryset
        except HealthOProSuperAdmin.DoesNotExist:
            raise ValidationError({"Error": f"Access Denied!"})

        except Exception as error:
            raise ValidationError({"Error": f"{error}"})

    def create(self, request, *args, **kwargs):
        return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            super_admin = HealthOProSuperAdmin.objects.get(is_active=True, user=self.request.user)

            if super_admin:
                instance = self.get_object()
                partial = kwargs.pop('partial', False)
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                validated_data = serializer.validated_data

                instance.is_active = validated_data['is_active']
                instance.remarks = validated_data['remarks']

                instance.last_updated_by = request.user

                instance.save()

                serializer = GlobalMessagingSettingsSerializer(instance)
                return Response(serializer.data)

        except HealthOProSuperAdmin.DoesNotExist:
            return Response({"Error": "Access Denied!"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as error:
            return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)


class GlobalBusinessSettingsViewset(viewsets.ModelViewSet):
    queryset = GlobalBusinessSettings.objects.all()
    serializer_class = GlobalBusinessSettingsSerializer

    def get_queryset(self):
        try:
            super_admin = HealthOProSuperAdmin.objects.get(user=self.request.user, is_active=True)

            queryset = self.queryset
            return queryset

        except HealthOProSuperAdmin.DoesNotExist:
            raise ValidationError({"Error": f"Access Denied!"})

        except Exception as error:
            raise ValidationError({"Error": f"{error}"})

    def create(self, request, *args, **kwargs):
        try:
            super_admin = HealthOProSuperAdmin.objects.get(user=self.request.user, is_active=True)
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)  # Validate the incoming data
            self.perform_create(serializer)  # Create the object

            # Return a success response with the created object
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except HealthOProSuperAdmin.DoesNotExist:
            return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as error:
            return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            super_admin = HealthOProSuperAdmin.objects.get(is_active=True, user=self.request.user)

            if super_admin:
                instance = self.get_object()
                partial = kwargs.pop('partial', False)
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                validated_data = serializer.validated_data
                is_sms_active = validated_data['is_sms_active']
                is_whatsapp_active = validated_data['is_whatsapp_active']

                instance.is_sms_active = is_sms_active
                instance.is_whatsapp_active = is_whatsapp_active
                instance.last_updated_by = request.user

                client = Client.objects.get(name=instance.business.organization_name)
                with schema_context(client.schema_name):
                    if is_sms_active is not None:
                        obj = BusinessMessageSettings.objects.get(client=client)
                        obj.is_sms_active = is_sms_active
                        obj.save()

                    if is_whatsapp_active is not None:
                        obj = BusinessMessageSettings.objects.get(client=client)
                        obj.is_whatsapp_active = is_whatsapp_active
                        obj.save()

                instance.save()

                serializer = GlobalBusinessSettingsSerializer(instance)

                return Response(serializer.data)

        except HealthOProSuperAdmin.DoesNotExist:
            return Response({"Error": "Access Denied!"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as error:
            print(error)
            return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)


class BusinessMessagesCreditsAdditionView(generics.ListCreateAPIView):
    def get(self, request, *args, **kwargs):
        try:
            super_admin = HealthOProSuperAdmin.objects.get(is_active=True, user=self.request.user)

            # Use request.query_params for GET requests
            b_id = self.request.query_params.get('b_id')
            if not b_id:
                return Response({"Error": "b_id is required"}, status=status.HTTP_400_BAD_REQUEST)

            # Get the business and client
            business = BusinessProfiles.objects.get(pk=b_id)
            client = Client.objects.get(name=business.organization_name)

            # Switch to the client's schema
            with schema_context(client.schema_name):
                # Get the last SMS and WhatsApp credits
                sms = BusinessMessagesCredits.objects.filter(
                    messaging_service_types=MessagingServiceTypes.objects.get(id=1))
                sms_credits = sms.last()
                whatsapp = BusinessMessagesCredits.objects.filter(
                    messaging_service_types=MessagingServiceTypes.objects.get(id=2))
                whatsapp_credits = whatsapp.last()

                history = BusinessMessagesCredits.objects.all().order_by('-id')

                # Combine the two credit records (ensure both are not None)
                credits = []
                if sms_credits:
                    credits.append(sms_credits)
                if whatsapp_credits:
                    credits.append(whatsapp_credits)

                sms_history = BusinessMessagesCreditsSerializer(sms, many=True)
                whatsapp_history = BusinessMessagesCreditsSerializer(whatsapp, many=True)

                history = BusinessMessagesCreditsSerializer(history, many=True)

                # Serialize the combined results
                serializer = BusinessMessagesCreditsSerializer(credits, many=True)
                return Response({"latest": serializer.data,
                                 "history": history.data,
                                 "sms_history": sms_history.data,
                                 "whatsapp_history": whatsapp_history.data}, status=status.HTTP_200_OK)

        except HealthOProSuperAdmin.DoesNotExist:
            return Response({"Error": "Access Denied!"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as error:
            return Response({"Error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, *args, **kwargs):
        try:
            super_admin = HealthOProSuperAdmin.objects.get(is_active=True, user=self.request.user)
            b_id = request.data.get('b_id')
            new_credits = request.data.get('new_credits')
            service_type = request.data.get('service_type')
            remarks = request.data.get('remarks', "")

            if not b_id:
                return Response({"Error": "Business ID is mandatory!"}, status=status.HTTP_400_BAD_REQUEST)

            if not service_type:
                return Response({"Error": "Service Type is mandatory!"}, status=status.HTTP_400_BAD_REQUEST)

            b_id = BusinessProfiles.objects.get(pk=b_id)

            client = Client.objects.get(name=b_id.organization_name)

            with schema_context(client.schema_name):
                # Create a new BusinessWhatsAppCounter entry
                credits = BusinessMessagesCredits.objects.create(
                    new_credits=new_credits,
                    total_messages=0,
                    remarks=remarks,
                    messaging_service_types=MessagingServiceTypes.objects.get(id=service_type),
                    last_updated_by=request.user
                )
                serializer = BusinessMessagesCreditsSerializer(credits)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

        except HealthOProSuperAdmin.DoesNotExist:
            return Response({"Error": "Access Denied!"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as error:
            return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)


class ULabMenusListViewset(viewsets.ModelViewSet):
    queryset = ULabMenus.objects.all()
    serializer_class = ULabMenusSerializer

    def get_queryset(self):
        try:
            super_admin = HealthOProSuperAdmin.objects.get(user=self.request.user, is_active=True)
            queryset = self.queryset
            is_active = self.request.query_params.get('is_active', None)

            if is_active:
                queryset = queryset.filter(is_active=True)

            return queryset
        except HealthOProSuperAdmin.DoesNotExist:
            raise ValidationError({"Error": "Access Denied!"})

        except Exception as error:
            raise ValidationError({"Error": f"{error}"})

    def create(self, request, *args, **kwargs):
        try:
            super_admin = HealthOProSuperAdmin.objects.get(user=self.request.user, is_active=True)
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)  # Validate the incoming data
            self.perform_create(serializer)  # Create the object

            # Return a success response with the created object
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except HealthOProSuperAdmin.DoesNotExist:
            return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as error:
            return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            super_admin = HealthOProSuperAdmin.objects.get(user=self.request.user, is_active=True)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            return Response(serializer.data, status=status.HTTP_200_OK)

        except HealthOProSuperAdmin.DoesNotExist:
            return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as error:
            return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)


class BusinessModulesMappingView(viewsets.ModelViewSet):
    queryset = BusinessModules.objects.all()
    serializer_class = BusinessModulesSerializer

    def get_queryset(self):
        try:
            super_admin = HealthOProSuperAdmin.objects.get(user=self.request.user, is_active=True)
            queryset = self.queryset
            b_id = self.request.query_params.get('b_id', None)

            if b_id:
                queryset = queryset.filter(business__id=b_id)

            return queryset

        except HealthOProSuperAdmin.DoesNotExist:
            raise ValidationError({"Error": "Access Denied!"})

        except Exception as error:
            raise ValidationError({"Error": f"{error}"})

    def create(self, request, *args, **kwargs):
        return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            super_admin = HealthOProSuperAdmin.objects.get(user=self.request.user, is_active=True)
            instance = self.get_object()
            partial = kwargs.pop('partial', False)
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            validated_data = serializer.validated_data

            modules = validated_data.get('modules')
            if modules is not None:
                instance.modules.set(modules)

            instance.last_updated_by = request.user

            instance.save()

            return Response(serializer.data)

        except HealthOProSuperAdmin.DoesNotExist:
            return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as error:
            return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)


class BusinessSubscriptionTypeViewSet(viewsets.ModelViewSet):
    queryset = BusinessSubscriptionType.objects.all()
    serializer_class = BusinessSubscriptionTypeSerializer


class BusinessBillCalculationTypeViewSet(viewsets.ModelViewSet):
    queryset = BusinessBillCalculationType.objects.all()
    serializer_class = BusinessBillCalculationTypeSerializer

    def get_queryset(self):
        try:
            super_admin = HealthOProSuperAdmin.objects.get(user=self.request.user, is_active=True)

            queryset = BusinessBillCalculationType.objects.all()
            subscription_type = self.request.query_params.get('subscription_type', None)

            if subscription_type:
                queryset = queryset.filter(subscription_type__id=subscription_type)

            return queryset

        except HealthOProSuperAdmin.DoesNotExist:
            raise ValidationError({"Error": "Access Denied!"})

        except Exception as error:
            raise ValidationError({"Error": "Access Denied!"})


class BusinessSubscriptionPlansViewSet(viewsets.ModelViewSet):
    queryset = BusinessSubscriptionPlans.objects.all()
    serializer_class = BusinessSubscriptionPlansSerializer

    def get_queryset(self):
        try:
            super_admin = HealthOProSuperAdmin.objects.get(user=self.request.user, is_active=True)
            queryset = BusinessSubscriptionPlans.objects.all()

            query = self.request.query_params.get('q', None)

            if query:
                queryset = queryset.filter(name__icontains=query)

            return queryset

        except HealthOProSuperAdmin.DoesNotExist:
            raise ValidationError({"Error": "Access Denied!"})

        except Exception as error:
            raise ValidationError({"Error": f"{error}"})

    def create(self, request, *args, **kwargs):
        try:
            super_admin = HealthOProSuperAdmin.objects.get(user=self.request.user, is_active=True)
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)  # Validate the incoming data
            serializer_data = serializer.validated_data
            serializer_data['created_by'] = self.request.user
            serializer_data['last_updated_by'] = self.request.user
            self.perform_create(serializer)  # Create the object

            # Return a success response with the created object
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except HealthOProSuperAdmin.DoesNotExist:
            return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as error:
            return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            super_admin = HealthOProSuperAdmin.objects.get(user=self.request.user, is_active=True)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer_data = serializer.validated_data
            serializer_data['last_updated_by'] = self.request.user
            self.perform_update(serializer)

            return Response(serializer.data, status=status.HTTP_200_OK)

        except HealthOProSuperAdmin.DoesNotExist:
            return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as error:
            return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)


class BusinessSubscriptionPlansPurchasedViewset(viewsets.ModelViewSet):
    queryset = BusinessSubscriptionPlansPurchased.objects.all()
    serializer_class = BusinessSubscriptionPlansPurchaseFromAdminSerializer

    def list(self, request, *args, **kwargs):
        try:
            super_admin = HealthOProSuperAdmin.objects.get(user=self.request.user, is_active=True)

            b_id = self.request.query_params.get('b_id', None)

            if not b_id:
                return ValidationError({"Error": "b_id is mandatory!"})

            b_id = BusinessProfiles.objects.get(pk=b_id)

            client = Client.objects.get(name=b_id.organization_name)

            with schema_context(client.schema_name):
                queryset = BusinessSubscriptionPlansPurchased.objects.all().order_by('-id')

                serializer = BusinessSubscriptionPlansPurchasedSerializer(queryset, many=True)

                return Response(serializer.data)

        except HealthOProSuperAdmin.DoesNotExist:
            return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as error:
            return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request, *args, **kwargs):
        try:
            super_admin = HealthOProSuperAdmin.objects.get(user=self.request.user, is_active=True)

            created_by = self.request.user
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer_data = serializer.validated_data
            b_id = serializer_data.get('b_id')
            calc_type = serializer_data.get('calc_type')
            plan = serializer_data.get('plan')
            plan_start_date_input = serializer_data.get('plan_start_date')

            if not b_id:
                return Response({"Error": "b_id is mandatory!"}, status=status.HTTP_400_BAD_REQUEST)

            client = Client.objects.get(name=b_id.organization_name)
            with schema_context(client.schema_name):
                if not calc_type:
                    calc_type = BusinessBillCalculationType.objects.filter(subscription_type__name='Paid',
                                                                           is_default=True).first()

                if not plan:
                    plan = BusinessSubscriptionPlans.objects.filter(subscription_type__name='Paid',
                                                                    is_default_plan=True).first()

                existing_plan = BusinessSubscriptionPlansPurchased.objects.last()

                plan_start_date = existing_plan.plan_end_date

                if plan_start_date_input:
                    plan_start_date = plan_start_date_input

                sub_plan = BusinessSubscriptionPlansPurchased.objects.create(
                    b_id=b_id,
                    plan_name=plan.name,
                    no_of_days=plan.plan_validity_in_days,
                    plan_start_date=plan_start_date,
                    plan_end_date=plan_start_date + timedelta(days=plan.plan_validity_in_days),
                    amount_per_patient=calc_type.amount_per_patient,
                    is_amount_percentage=calc_type.is_amount_percentage,
                    is_prepaid=calc_type.is_prepaid,
                    invoice_bill_amount=plan.plan_price if calc_type.is_prepaid else 0.00,
                    is_bill_paid=True if calc_type.is_prepaid else False,
                    payment_status='Paid' if calc_type.is_prepaid else 'Bill Not Generated',
                    invoice_id="",
                    created_by=created_by,
                    last_updated_by=created_by
                )

                overall_subscription_status = OverallBusinessSubscriptionStatus.objects.get(b_id=b_id)
                overall_subscription_status.validity = sub_plan.plan_end_date
                overall_subscription_status.account_locks_on = sub_plan.plan_end_date + timedelta(
                    days=plan.grace_period)
                overall_subscription_status.is_subscription_active = True
                overall_subscription_status.save()

                try:
                    if not b_id.is_onboarded:
                        b_id.is_onboarded = True
                        b_id.save()
                except Exception as error:
                    print(error)

                serializer = BusinessSubscriptionPlansPurchasedSerializer(sub_plan)

                return Response(serializer.data, status=status.HTTP_201_CREATED)

        except HealthOProSuperAdmin.DoesNotExist:
            return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as error:
            return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)


class OverallBusinessSubscriptionStatusViewSet(viewsets.ModelViewSet):
    queryset = OverallBusinessSubscriptionStatus.objects.all()
    serializer_class = OverallBusinessSubscriptionStatusSerializer

    def get_queryset(self):
        try:
            super_admin = HealthOProSuperAdmin.objects.get(user=self.request.user, is_active=True)
            queryset = self.queryset
            b_id = self.request.query_params.get('b_id', None)

            if b_id:
                queryset = queryset.filter(b_id__id=b_id)

            return queryset

        except HealthOProSuperAdmin.DoesNotExist:
            raise ValidationError({"Error": "Access Denied!"})

        except Exception as error:
            raise ValidationError({"Error": f"{error}"})


class WhatsappConfigurationsViewSet(viewsets.ModelViewSet):
    queryset = WhatsappConfigurations.objects.all()
    serializer_class = WhatsappConfigurationsSerializer

    def list(self, request, *args, **kwargs):
        try:
            super_admin = HealthOProSuperAdmin.objects.get(user=self.request.user, is_active=True)
            b_id = self.request.query_params.get('b_id', None)
            business = BusinessProfiles.objects.get(pk=b_id)
            client = Client.objects.get(name=business.organization_name)
            with schema_context(client.schema_name):
                queryset = WhatsappConfigurations.objects.all()
                serializer = WhatsappConfigurationsSerializer(queryset, many=True)
                return Response(serializer.data)

        except HealthOProSuperAdmin.DoesNotExist:
            return Response({"Error": "Access Denied!"})

        except Exception as error:
            return Response({"Error": f"{error}"})

    def create(self, request, *args, **kwargs):
        try:
            super_admin = HealthOProSuperAdmin.objects.get(user=self.request.user, is_active=True)
            b_id = self.request.query_params.get('b_id', None)
            if not b_id:
                return Response({"Error": "b_id is mandatory!"}, status=status.HTTP_400_BAD_REQUEST)

            business = BusinessProfiles.objects.get(pk=b_id)
            client = Client.objects.get(name=business.organization_name)

            with schema_context(client.schema_name):
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer_data = serializer.validated_data
                serializer_data['last_updated_by'] = self.request.user

                if serializer_data['secret_key'] and serializer_data['phone_id']:
                    pass
                else:
                    serializer_data['is_active'] = False

                self.perform_create(serializer)

                return Response(serializer.data, status=status.HTTP_201_CREATED)

        except HealthOProSuperAdmin.DoesNotExist:
            return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as error:
            return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            super_admin = HealthOProSuperAdmin.objects.get(user=self.request.user, is_active=True)
            b_id = self.request.query_params.get('b_id', None)
            if not b_id:
                return Response({"Error": "b_id is mandatory!"}, status=status.HTTP_400_BAD_REQUEST)

            business = BusinessProfiles.objects.get(pk=b_id)
            client = Client.objects.get(name=business.organization_name)

            with schema_context(client.schema_name):
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer_data = serializer.validated_data
                serializer_data['last_updated_by'] = self.request.user
                if serializer_data['secret_key'] and serializer_data['phone_id']:
                    pass
                else:
                    serializer_data['is_active'] = False

                self.perform_update(serializer)


                return Response(serializer.data, status=status.HTTP_200_OK)

        except HealthOProSuperAdmin.DoesNotExist:
            return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as error:
            return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)




class BusinessControlsViewSet(viewsets.ModelViewSet):
    queryset = BusinessControls.objects.all()
    serializer_class = BusinessControlsSerializer

    def list(self, request, *args, **kwargs):
        try:
            super_admin = HealthOProSuperAdmin.objects.get(user=self.request.user, is_active=True)
            b_id = self.request.query_params.get('b_id', None)
            if not b_id:
                return Response({"Error": "b_id is mandatory!"}, status=status.HTTP_400_BAD_REQUEST)
            business = BusinessProfiles.objects.get(pk=b_id)
            client = Client.objects.get(name=business.organization_name)
            with schema_context(client.schema_name):
                obj = BusinessControls.objects.first()

                if obj:
                    pass
                else:
                    obj = BusinessControls.objects.create(multiple_branches=False)

                serializer = BusinessControlsSerializer(obj)
                return Response(serializer.data)

        except HealthOProSuperAdmin.DoesNotExist:
            return Response({"Error": "Access Denied!"},status=status.HTTP_400_BAD_REQUEST)

        except Exception as error:
            return Response({"Error": f"{error}"},status=status.HTTP_400_BAD_REQUEST)


    def update(self, request, *args, **kwargs):
        try:
            super_admin = HealthOProSuperAdmin.objects.get(user=self.request.user, is_active=True)
            b_id = self.request.query_params.get('b_id', None)
            if not b_id:
                return Response({"Error": "b_id is mandatory!"}, status=status.HTTP_400_BAD_REQUEST)

            business = BusinessProfiles.objects.get(pk=b_id)
            client = Client.objects.get(name=business.organization_name)

            with schema_context(client.schema_name):
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer_data = serializer.validated_data

                serializer_data['last_updated_by'] = self.request.user

                self.perform_update(serializer)

                if instance.multiple_branches:
                    lab_staffs = LabStaff.objects.filter(is_login_access=True)
                    branches=BusinessAddresses.objects.filter(b_id=business)

                    for lab_staff in lab_staffs:
                        lab_staff.branches.set(branches)
                        default_branch, created = LabStaffDefaultBranch.objects.get_or_create(lab_staff=lab_staff)
                        default_branch.default_branch.set(branches)

                tests = LabPatientTests.objects.filter(branch__isnull=False).exists()
                patients = Patient.objects.filter(branch__isnull=False).exists()

                if tests and patients:
                    pass
                else:
                    first_branch = branches.first()
                    for patient in patients:
                        patient.branch = first_branch
                        patient.save()

                    for test in tests:
                        test.branch = first_branch
                        test.save()

                return Response(serializer.data, status=status.HTTP_200_OK)

        except HealthOProSuperAdmin.DoesNotExist:
            return Response({"Error": "Access Denied!"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as error:
            return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)



class DeleteBusinessAccountsView(generics.ListCreateAPIView):
    queryset = BusinessProfiles.objects.filter(is_onboarded=False)
    serializer_class = BusinessProfilesDeletionForAdminSerializer

    def get_queryset(self):
        try:
            super_admin = HealthOProSuperAdmin.objects.get(user=self.request.user, is_active=True)
            action = self.request.query_params.get('action', None)
            query = self.request.query_params.get('q', None)
            sort = self.request.query_params.get('sort', None)

            if action == 'view':
                queryset = BusinessProfiles.objects.filter(is_onboarded=False, is_active=True)

            elif action == 'ready_to_delete':
                inactive_businesses = BusinessProfiles.objects.filter(is_onboarded=False, is_active=False)
                ready_to_delete_businesses= []

                for business in inactive_businesses:
                    client = Client.objects.filter(name=business.organization_name, is_active=True)
                    if not client:
                        ready_to_delete_businesses.append(business.id)

                queryset = BusinessProfiles.objects.filter(is_onboarded=False, is_active=False,id__in=ready_to_delete_businesses)

            elif action == 'deleted':
                queryset = DeletedBusinessProfiles.objects.all()
                self.serializer_class=DeletedBusinessProfilesSerializer

            else:
                queryset = BusinessProfiles.objects.none()

            if query is not None:
                search_query = (Q(organization_name__icontains=query) | Q(phone_number__icontains=query))
                queryset = queryset.filter(search_query)

            if sort == '-added_on':
                queryset = queryset.order_by('-added_on')
            if sort == 'added_on':
                queryset = queryset.order_by('added_on')

            return queryset

        except HealthOProSuperAdmin.DoesNotExist:
            return Response({"Error": "Access Denied!"},status=status.HTTP_400_BAD_REQUEST)

        except Exception as error:
            print(error)
            return BusinessProfiles.objects.none()

    def create(self, request, *args, **kwargs):
        try:
            super_admin = HealthOProSuperAdmin.objects.get(user=self.request.user, is_active=True,is_owner=True)
            action = request.data.get('action', None)
            b_id = request.data.get('b_id', None)

            if action and b_id:
                pass
            else:
                return Response({"Error":"Action and Business ID are mandatory!"}, status=status.HTTP_400_BAD_REQUEST)

            business = BusinessProfiles.objects.get(pk=b_id)
            client = Client.objects.filter(name=business.organization_name).first()

            if business.is_onboarded:
                return Response({"Error":"Onboarded Businesses cannot be deleted!"}, status=status.HTTP_400_BAD_REQUEST)

            if action == 'inactive':
                business.is_active=False
                business.save()
                if client:
                    client.is_active=False
                    client.save()
                return Response({"Status":"Business marked as Inactive!"})

            elif action == 'active':
                business.is_active = True
                business.save()

                if client:
                    client.is_active = True
                    client.save()
                return Response({"Status": "Business marked as Active!"})

            elif action == 'delete':
                client_status = client.is_active if client else False
                if business.is_active or client_status or business.is_onboarded:
                    return Response({"Error":"Cannot Delete Active Business!"}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    try:
                        delete_msg_users_of_client(client=client, business=business)
                        delete_user_tenants_of_client(client=client, business=business)
                        delete_business_details_and_add_in_deleted(business=business,client=client,
                                                                   deleted_by=request.user)
                        delete_schema_of_client(client=client, business=business)
                        return Response({"Status":"Business deleted!"})
                    except Exception as error:
                        print(error)
                        return Response({"Error":f"{error}"}, status=status.HTTP_400_BAD_REQUEST)

            else:
                return Response({"Error": "Selected Action is not Available!"}, status=status.HTTP_400_BAD_REQUEST)

        except HealthOProSuperAdmin.DoesNotExist:
            return Response({"Error": "Access Denied!"},status=status.HTTP_400_BAD_REQUEST)

        except Exception as error:
            print(error)
            return Response({"Error":f"{error}"}, status=status.HTTP_400_BAD_REQUEST)