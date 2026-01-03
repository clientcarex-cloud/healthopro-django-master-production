from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from interoperability.views import LabTpaSecretKeysViewset, LabTpaSecretKeysIntegrationView

urlpatterns = [
    path('lab_tpa_secret_keys/', LabTpaSecretKeysViewset.as_view(), name='lab_tpa_secret_keys'),
    path('lab_tpa_integrated_secret_keys/', LabTpaSecretKeysIntegrationView.as_view(), name='lab_tpa_integrated_secret_keys'),


]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
