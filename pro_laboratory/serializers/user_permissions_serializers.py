from rest_framework import serializers
from pro_laboratory.models.user_permissions_models import UserPermissionsAccess


class UserPermissionsAccessSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPermissionsAccess
        fields = "__all__"


