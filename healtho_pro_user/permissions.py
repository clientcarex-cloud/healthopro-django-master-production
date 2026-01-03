from rest_framework import permissions


class IsTenantUser(permissions.BasePermission):
    def has_permission(self, request, view):
        user_tenant_id = getattr(request.user, 'tenant_id', None)
        token_tenant_id = request.auth.get('tenant_id') if request.auth else None

        return user_tenant_id == token_tenant_id
