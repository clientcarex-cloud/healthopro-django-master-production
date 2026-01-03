from rest_framework import viewsets

from pro_laboratory.models.user_permissions_models import UserPermissionsAccess
from pro_laboratory.serializers.user_permissions_serializers import UserPermissionsAccessSerializer


class UserPermissionsAccessViewset(viewsets.ModelViewSet):
    serializer_class = UserPermissionsAccessSerializer

    def get_queryset(self):
        queryset = UserPermissionsAccess.objects.all()
        query = self.request.query_params.get('lab_staff')

        if query is not None:
            return queryset.filter(lab_staff__id=query)
        else:
            return queryset.all()

