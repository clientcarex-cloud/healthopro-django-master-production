from django.apps import AppConfig


class ProLaboratoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pro_laboratory'

    def ready(self):
        import pro_laboratory.signals
