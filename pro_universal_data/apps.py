from django.apps import AppConfig


class ProUniversalDataConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pro_universal_data'

    def ready(self):
        import pro_universal_data.signals
