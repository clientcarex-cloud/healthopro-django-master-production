from django.core.cache import cache
from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django_tenants.utils import schema_context

from healtho_pro_user.models.business_models import BusinessModules
from healtho_pro_user.models.users_models import Client
from pro_laboratory.models.global_models import LabMenuAccess
from pro_universal_data.models import ULabPatientAttenderTitles, ULabPatientGender, ULabPatientTitles, \
    ULabPaymentModeType, ULabPatientAge, ULabMenus


@receiver(post_save, sender=ULabPatientAttenderTitles)
@receiver(post_delete, sender=ULabPatientAttenderTitles)
def clear_ulab_patient_attender_titles_cache(sender, instance, **kwargs):
    def invalidate_cache():
        try:
            cache_key_prefix = f'ulab_patient_attender_titles_list'
            keys_to_delete = [key for key in cache.keys(f'{cache_key_prefix}*')]
            for key in keys_to_delete:
                cache.delete(key)
                print(f'Deleted cache key: {key}')
        except Exception as e:
            print(f"Error occurred while invalidating cache: {str(e)}")

    transaction.on_commit(invalidate_cache)


@receiver(post_save, sender=ULabPatientGender)
@receiver(post_delete, sender=ULabPatientGender)
def clear_ulab_patient_gender_cache(sender, instance, **kwargs):
    def invalidate_cache():
        try:
            cache_key_prefix = f'ulab_patient_gender_list'
            keys_to_delete = [key for key in cache.keys(f'{cache_key_prefix}*')]
            for key in keys_to_delete:
                cache.delete(key)
                print(f'Deleted cache key: {key}')
        except Exception as e:
            print(f"Error occurred while invalidating cache: {str(e)}")

    transaction.on_commit(invalidate_cache)


@receiver(post_save, sender=ULabPatientTitles)
@receiver(post_delete, sender=ULabPatientTitles)
def clear_ulab_patient_titles_cache(sender, instance, **kwargs):
    def invalidate_cache():
        try:
            cache_key_prefix = f'ulab_patient_titles_list'
            keys_to_delete = [key for key in cache.keys(f'{cache_key_prefix}*')]
            for key in keys_to_delete:
                cache.delete(key)
                print(f'Deleted cache key: {key}')
        except Exception as e:
            print(f"Error occurred while invalidating cache: {str(e)}")

    transaction.on_commit(invalidate_cache)


@receiver(post_save, sender=ULabPaymentModeType)
@receiver(post_delete, sender=ULabPaymentModeType)
def clear_ulab_paymode_type_cache(sender, instance, **kwargs):
    def invalidate_cache():
        try:
            cache_key_prefix = f'ulab_paymode_type_list'
            keys_to_delete = [key for key in cache.keys(f'{cache_key_prefix}*')]
            for key in keys_to_delete:
                cache.delete(key)
                print(f'Deleted cache key: {key}')
        except Exception as e:
            print(f"Error occurred while invalidating cache: {str(e)}")

    transaction.on_commit(invalidate_cache)


@receiver(post_save, sender=ULabPatientAge)
@receiver(post_delete, sender=ULabPatientAge)
def clear_ulab_patient_age_cache(sender, instance, **kwargs):
    def invalidate_cache():
        try:
            cache_key_prefix = f'ulab_patient_age_list'
            keys_to_delete = [key for key in cache.keys(f'{cache_key_prefix}*')]
            for key in keys_to_delete:
                cache.delete(key)
                print(f'Deleted cache key: {key}')
        except Exception as e:
            print(f"Error occurred while invalidating cache: {str(e)}")

    transaction.on_commit(invalidate_cache)


@receiver(post_save, sender=ULabMenus)
@receiver(post_delete, sender=ULabMenus)
def clear_ulab_menu_list_cache(sender, instance, **kwargs):
    def invalidate_cache():
        try:
            cache_key_prefix = 'ulab_menu_list'
            keys_to_delete = [key for key in cache.keys(f'{cache_key_prefix}*')]

            if keys_to_delete:
                for key in keys_to_delete:
                    cache.delete(key)
                    print(f'Deleted cache key: {key}')
            else:
                print("No cache.")
        except Exception as e:
            print(f"Error occurred while invalidating cache: {str(e)}")

    transaction.on_commit(invalidate_cache)


@receiver(post_save, sender=BusinessModules)
@receiver(post_delete, sender=BusinessModules)
def clear_ulab_menu_list_cache(sender, instance, **kwargs):
    def invalidate_cache():
        try:
            cache_key_prefix = 'ulab_menu_list'
            keys_to_delete = [key for key in cache.keys(f'{cache_key_prefix}*')]
            if keys_to_delete:
                for key in keys_to_delete:
                    cache.delete(key)
                    print(f'Deleted cache key: {key}')
            else:
                print("No cache.")
        except Exception as e:
            print(f"Error occurred while invalidating cache: {str(e)}")

    transaction.on_commit(invalidate_cache)


@receiver(post_save, sender=BusinessModules)
@receiver(post_delete, sender=BusinessModules)
def check_lab_menu_access(sender, instance, **kwargs):
    def check():
        business_modules_menus = instance.modules.all()

        client = Client.objects.get(name=instance.business.organization_name)

        with schema_context(client.schema_name):
            lab_menu_access_instances = LabMenuAccess.objects.all()

            for lab_menu_access in lab_menu_access_instances:
                lab_menus = lab_menu_access.lab_menu.all()

                # Find lab_menus in LabMenuAccess that are not in BusinessModules' modules
                extra_menus = lab_menus.difference(business_modules_menus)

                if extra_menus.exists():
                    lab_menu_access.lab_menu.remove(*extra_menus)

    transaction.on_commit(check)
