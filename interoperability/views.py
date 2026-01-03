from django.shortcuts import render
from rest_framework import generics, permissions
from interoperability.models import LabTpaType, LabTpaSecretKeys
from interoperability.serializers import LabTpaSecretKeysSerializer, LabTpaSecretKeysIntegrationSerializer


# Create your views here.

class LabTpaSecretKeysViewset(generics.ListAPIView):
    queryset = LabTpaSecretKeys.objects.all()
    serializer_class = LabTpaSecretKeysSerializer


# using this for machine integration
class LabTpaSecretKeysIntegrationView(generics.ListAPIView):
    serializer_class = LabTpaSecretKeysIntegrationSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        secret_key = self.request.query_params.get('secret_key', None)
        queryset = LabTpaSecretKeys.objects.none()
        if secret_key is not None:
            try:
                queryset = LabTpaSecretKeys.objects.filter(secret_key=secret_key)

            except LabTpaSecretKeys.DoesNotExist:
                queryset = LabTpaSecretKeys.objects.none()

        return queryset
