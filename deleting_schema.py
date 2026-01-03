import os
from csv import excel

from django.db.models import Q
import psycopg2
from django_tenants.utils import schema_context

from cloud_messaging.models import Group, Conversation, Message, MessageReadStatus
from healtho_pro_user.models.business_models import DeletedBusinessProfiles, BusinessAddresses, BContacts, \
    BusinessProfilesImages, BusinessTimings, BExecutive, GlobalBusinessSettings, BusinessModules
from healtho_pro_user.models.pro_doctor_models import ProdoctorAppointmentSlot, ProDoctorConsultation
from healtho_pro_user.models.subscription_models import OverallBusinessSubscriptionStatus, \
    OverallBusinessSubscriptionPlansPurchased
from healtho_pro_user.models.users_models import UserTenant, OTP, UserSession, HealthOProMessagingUser, Client
from pro_laboratory.models.global_models import LabStaff
from pro_laboratory.models.sourcing_lab_models import SourcingLabRegistration
from super_admin.models import HealthOProSuperAdmin


def delete_msg_users_of_client(client=None, business=None):
    try:
        print('msg users deletion started')
        if client:
            msg_users = HealthOProMessagingUser.objects.filter(client=client)

            groups = Group.objects.filter(creator__in=msg_users)

            conversations = Conversation.objects.filter(Q(initiator__in=msg_users) | Q(receiver__in=msg_users))

            messages = Message.objects.filter(Q(group__in=groups) | Q(conversation__in=conversations))

            try:
                MessageReadStatus.objects.filter(message__in=messages).delete()
                messages.delete()
            except Exception as error:
                print(error)

            try:
                conversations.delete()
            except Exception as error:
                print(error)
                for conversation in conversations:
                    conversation.client = None
                    conversation.save()

            try:
                groups.delete()
            except Exception as error:
                print(error)

            try:
                msg_users.delete()
            except Exception as error:
                print(error)
                for msg_user in msg_users:
                    msg_user.client = None
                    msg_user.save()

        print('msg users deletion ended')

    except Exception as error:
        print(error)




def delete_user_tenants_of_client(client=None, business=None):
    try:
        print('user tenants deletion started')
        business.pro_user_id=None
        business.save()
        if client:
            tenants = UserTenant.objects.filter(client=client)
            users = tenants.values_list('user', flat=True)

            with schema_context(client.schema_name):
                lab_staffs = LabStaff.objects.filter(pro_user_id__in=users)
                if lab_staffs:
                    lab_staffs.update(pro_user_id=None)

                for tenant in tenants:
                    try:
                        user=tenant.user
                        other_client_exists_for_user = UserTenant.objects.filter(user=user).exclude(client=client)
                        print('user:',user, other_client_exists_for_user, 'other_client_exists_for_user')

                        if other_client_exists_for_user:
                            print('other client exists for user, so not deleting user!')
                            pass
                        else:
                            otp = OTP.objects.filter(pro_user_id=user)
                            if otp:
                                otp.delete()
                            print('otp delete')

                            user.delete()
                            print('user deleted')

                    except Exception as error:
                        print(error)

                tenants.delete()
                print('tenant deleted')

        print('user tenants deletion ended')
    except Exception as error:
        print(error)

def delete_business_details_and_add_in_deleted(business=None, client=None,deleted_by=None):
    print('business deletion started')
    try:
        super_admin = HealthOProSuperAdmin.objects.get(user=deleted_by)
        address_obj = BusinessAddresses.objects.filter(b_id=business).first()
        address = address_obj.address if address_obj else ""

        addresses = BusinessAddresses.objects.filter(b_id=business)
        sub_status = OverallBusinessSubscriptionStatus.objects.filter(b_id=business)
        sub_plans = OverallBusinessSubscriptionPlansPurchased.objects.filter(b_id=business)
        contacts = BContacts.objects.filter(b_id=business)
        images = BusinessProfilesImages.objects.filter(b_id=business)
        timings = BusinessTimings.objects.filter(b_id=business)
        executives = BExecutive.objects.filter(b_id=business)

        business_settings = GlobalBusinessSettings.objects.filter(business=business)
        modules = BusinessModules.objects.filter(business=business)

        slots = ProdoctorAppointmentSlot.objects.filter(hospital=business)
        consultations = ProDoctorConsultation.objects.filter(hospital=business)

        querysets_with_b_id_field = [addresses, sub_status, sub_plans, contacts, images, timings, executives]

        querysets_with_business_field = [business_settings, modules]

        querysets_with_hospital_field = [slots, consultations]

        for queryset in querysets_with_b_id_field:
            try:
                if queryset:
                    try:
                        print('Deleting:',queryset)
                        queryset.delete()
                        print('Deleted:',queryset)

                    except Exception as error:
                        print(error)
                        try:
                            print('Updating:',queryset)
                            queryset.update(b_id=None)
                            print('Updated:',queryset)
                        except Exception as error:
                            print(error)

            except Exception as error:
                print(error)


        for queryset in querysets_with_business_field:
            try:
                if queryset:
                    try:
                        print('Deleting:',queryset)
                        queryset.delete()
                        print('Deleted:',queryset)
                    except Exception as error:
                        print(error)
                        try:
                            print('Updating:',queryset)
                            queryset.update(business=None)
                            print('Updated:',queryset)
                        except Exception as error:
                            print(error)

            except Exception as error:
                print(error)


        for queryset in querysets_with_hospital_field:
            try:
                if queryset:
                    try:
                        print('Deleting:',queryset)
                        queryset.delete()
                        print('Deleted:',queryset)
                    except Exception as error:
                        print(error)
                        try:
                            print('Updating:',queryset)
                            queryset.update(hospital=None)
                            print('Updated:',queryset)
                        except Exception as error:
                            print(error)

            except Exception as error:
                print(error)


        try:
            if client:
                with schema_context(client.schema_name):
                    sourcing_labs = SourcingLabRegistration.objects.all()
                    print('Sourcing labs: ',sourcing_labs)

                    if sourcing_labs:
                        initiators = SourcingLabRegistration.objects.filter(initiator__isnull=False).values_list('initiator', flat=True)
                        acceptors = SourcingLabRegistration.objects.filter(acceptor__isnull=False).values_list('acceptor', flat=True)

                        sourcing_businesses = set(initiators) | set(acceptors)
                        sourcing_businesses.discard(business)
                        print('Sourcing Businesses: ',sourcing_businesses)

                        if sourcing_businesses:
                            for sourcing_business in sourcing_businesses:
                                sourcing_client = Client.objects.filter(name=sourcing_business.organization_name).first()

                                if sourcing_client:
                                    try:
                                        with schema_context(sourcing_client.schema_name):
                                            initiator_labs = SourcingLabRegistration.objects.filter(initiator=business)
                                            for lab in initiator_labs:
                                                print('initiator removed for lab',lab)
                                                lab.initiator = None
                                                lab.save()

                                            acceptor_labs = SourcingLabRegistration.objects.filter(acceptor=business)
                                            for lab in acceptor_labs:
                                                print('acceptor removed for lab',lab)
                                                lab.acceptor = None
                                                lab.save()

                                    except Exception as error:
                                        print(error)

        except Exception as error:
            print(error)

        try:
            print('deletion obj creation started')
            obj = DeletedBusinessProfiles.objects.create(
                deleted_id=business.id,
                deleted_client_id=client.id if client else None,
                organization_name=business.organization_name,
                phone_number=business.phone_number,
                provider_type=business.provider_type,
                country=business.country,
                city=business.city,
                pin_code=business.pin_code,
                state=business.state,
                address=address,
                latitude=business.latitude,
                longitude=business.longitude,
                website=business.website,
                b_logo=business.b_logo,
                business_added_on=business.added_on,
                deleted_by=super_admin)

            print('deletion obj creation ended')

        except Exception as error:
            print(error)
        print('business deletion ended')

    except Exception as error:
        print(error)



def delete_schema_of_client(client=None, business=None):
    # Database connection parameters
    db_config = {
        "dbname": os.environ.get('DB_NAME'),
        "user": os.environ.get('DB_USER'),
        "password": os.environ.get('DB_PASSWORD'),
        "host": os.environ.get('DB_HOST'),
        "port": os.environ.get('DB_PORT')
    }

    try:
        print('schemas deletion started')
        conn = psycopg2.connect(**db_config)
        conn.autocommit = True
        cursor = conn.cursor()

        business_name = business.organization_name

        if client:
            schema_name = client.schema_name
            client_name = client.name

            query = f'DROP SCHEMA "{schema_name}" CASCADE;'
            cursor.execute(query)
            print(f"Schema '{schema_name}' has been dropped successfully.")

            query_for_client = f"DELETE FROM public.healtho_pro_user_client WHERE name = '{client_name}';"
            cursor.execute(query_for_client)
            print(f"client '{client_name}' has been dropped successfully.")

        query_for_business = f"DELETE FROM public.healtho_pro_user_businessprofiles WHERE organization_name = '{business_name}';"
        cursor.execute(query_for_business)
        print(f"business '{business_name}' has been dropped successfully.")

        print('schemas deletion ended')


    except psycopg2.Error as e:
        print(f"Error: {e}")

    finally:
        # Clean up
        if cursor:
            cursor.close()
        if conn:
            conn.close()

