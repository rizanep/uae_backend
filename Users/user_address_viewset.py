class UserAddressViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user addresses.
    Users can only see and manage their own addresses.
    """
    serializer_class = UserAddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserAddress.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # If this is the first address, make it default
        is_default = serializer.validated_data.get('is_default', False)
        if not self.get_queryset().exists():
            is_default = True
        
        if is_default:
            self.get_queryset().update(is_default=False)
            
        serializer.save(user=self.request.user, is_default=is_default)

    def perform_update(self, serializer):
        is_default = serializer.validated_data.get('is_default', False)
        if is_default:
            self.get_queryset().exclude(pk=serializer.instance.pk).update(is_default=False)
        serializer.save()
