from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Allow users to edit their own profile or allow admin to edit any profile
    """
    
    def has_object_permission(self, request, view, obj):
        # Admin can modify any user
        if request.user and request.user.role == 'admin':
            return True
        
        # Users can only modify themselves
        return obj == request.user


class IsAdmin(permissions.BasePermission):
    """
    Allow only admin users
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'admin'


class IsOwner(permissions.BasePermission):
    """
    Allow only the owner to access
    """
    
    def has_object_permission(self, request, view, obj):
        return obj == request.user


class IsAdminOrOwner(permissions.BasePermission):
    """
    Allow admin users or the owner to access
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        return request.user == obj or request.user.role == 'admin'