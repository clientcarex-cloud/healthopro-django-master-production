from django.apps import AppConfig


class Healtho_pro_userConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'healtho_pro_user'

    def ready(self):
        import healtho_pro_user.signals
