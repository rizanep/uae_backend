from rest_framework.permissions import BasePermission, IsAdminUser
from rest_framework.exceptions import PermissionDenied


class IsAdminOrReadOnly(IsAdminUser):
    """
    Allow admin users full access. Deny all non-admins.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_staff and request.user.is_superuser


class IsWhatsAppAdmin(BasePermission):
    """
    Custom permission to check if user is admin and has WhatsApp management permission
    """
    message = "You do not have permission to manage WhatsApp templates."
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user is superuser
        if request.user.is_superuser:
            return True
        
        # Check if user has specific permission
        return request.user.has_perm('WhatsApp.change_whatsapptemplate')
    
    def has_object_permission(self, request, view, obj):
        # Restrict to superuser
        return request.user.is_superuser


class IsOwnerOrAdmin(BasePermission):
    """
    Allow owners of object and admins to access
    """
    message = "You do not have permission to perform this action."
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        
        # Check if user created the object
        if hasattr(obj, 'created_by') and obj.created_by == request.user:
            return True
        
        return False
