from rest_framework.permissions import BasePermission, IsAdminUser


class IsAdminOrReadOnly(IsAdminUser):
    """
    Allow admin users full access. Deny all non-admins.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_staff and request.user.is_superuser


class IsSMSAdmin(BasePermission):
    """
    Custom permission to check if user is admin with SMS management permission
    """
    message = "You do not have permission to manage SMS templates."
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user is superuser
        if request.user.is_superuser:
            return True
        
        # Check if user has specific permission
        return request.user.has_perm('SMS.change_smstemplate')
    
    def has_object_permission(self, request, view, obj):
        # Restrict to superuser
        return request.user.is_superuser
