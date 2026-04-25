"""
Account Deletion Service
Handles complete user account deletion with all related data
"""

import logging
from django.db import transaction
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta

from .models import User, GoogleOAuthToken, OTPToken, UserProfile, UserAddress
from Orders.models import Order
from Cart.models import Cart

logger = logging.getLogger(__name__)


class AccountDeletionService:
    """
    Service to handle complete account deletion with all related data
    Supports both hard delete and anonymization
    """
    
    # Related models to delete in order of dependency
    RELATED_MODELS_DELETE_ORDER = [
        'Cart',
        'Order',
        'UserAddress',
        'UserProfile',
        'GoogleOAuthToken',
        'OTPToken',
    ]
    
    @staticmethod
    def anonymize_user(user):
        """
        Anonymize user data instead of hard delete
        Useful for compliance (GDPR, etc.)
        """
        user.first_name = "Deleted"
        user.last_name = "User"
        user.email = f"deleted_{user.id}@deleted.local"
        user.phone_number = None
        user.google_id = None
        user.google_email = None
        user.referral_code = f"deleted_{user.id}"
        user.is_active = False
        user.deleted_at = timezone.now()
        user.save()
        
        logger.info(f"User {user.id} anonymized successfully")
        return user
    
    @staticmethod
    @transaction.atomic
    def delete_user_data(user, delete_method='hard', send_confirmation=True):
        """
        Delete all user data
        
        Args:
            user: User instance to delete
            delete_method: 'hard' (permanent delete) or 'soft' (anonymize)
            send_confirmation: Whether to send deletion confirmation email
        
        Returns:
            dict: Status and details of deletion
        """
        
        if delete_method not in ['hard', 'soft']:
            raise ValueError("delete_method must be 'hard' or 'soft'")
        
        try:
            user_email = user.email
            user_id = user.id
            user_phone = user.phone_number
            
            deletion_time = timezone.now()
            
            # Log deletion request
            logger.warning(
                f"Account deletion initiated for user {user_id} ({user_email}) - Method: {delete_method}",
                extra={'user_id': user_id, 'delete_method': delete_method}
            )
            
            # Delete or anonymize related data
            if delete_method == 'hard':
                AccountDeletionService._hard_delete_related_data(user)
                
                # Hard delete user
                user.delete()
                deletion_status = 'permanently_deleted'
                
            else:  # soft delete
                # Anonymize user
                AccountDeletionService.anonymize_user(user)
                deletion_status = 'anonymized'
            
            # Send confirmation email
            if send_confirmation and user_email:
                try:
                    AccountDeletionService._send_deletion_confirmation(
                        user_email,
                        deletion_status,
                        deletion_time
                    )
                except Exception as e:
                    logger.error(f"Failed to send deletion confirmation: {str(e)}")
            
            return {
                'status': 'success',
                'user_id': user_id,
                'user_email': user_email,
                'user_phone': user_phone,
                'deletion_method': delete_method,
                'deletion_status': deletion_status,
                'deleted_at': deletion_time,
                'message': f'Account successfully {deletion_status.replace("_", " ")}'
            }
        
        except Exception as e:
            logger.error(f"Error during account deletion: {str(e)}", exc_info=True)
            raise
    
    @staticmethod
    def _hard_delete_related_data(user):
        """Hard delete all user-related data"""
        
        # Delete cart items
        Cart.objects.filter(user=user).delete()
        logger.info(f"Deleted cart for user {user.id}")
        
        # Delete orders (with CASCADE, this should be automatic)
        # But we'll be explicit
        Order.objects.filter(user=user).delete()
        logger.info(f"Deleted orders for user {user.id}")
        
        # Delete addresses
        UserAddress.objects.filter(user=user).delete()
        logger.info(f"Deleted addresses for user {user.id}")
        
        # Delete profile
        if hasattr(user, 'profile') and user.profile:
            profile = user.profile
            # Delete profile image if it exists
            if profile.profile_picture and profile.profile_picture.name:
                storage = profile.profile_picture.storage
                try:
                    storage.delete(profile.profile_picture.name)
                except Exception as e:
                    logger.warning(f"Could not delete profile picture: {str(e)}")
            profile.delete()
            logger.info(f"Deleted profile for user {user.id}")
        
        # Delete Google OAuth token
        if hasattr(user, 'google_token') and user.google_token:
            user.google_token.delete()
            logger.info(f"Deleted Google OAuth token for user {user.id}")
        
        # Delete OTP tokens
        OTPToken.objects.filter(user=user).delete()
        logger.info(f"Deleted OTP tokens for user {user.id}")
    
    @staticmethod
    def _send_deletion_confirmation(email, deletion_status, deletion_time):
        """Send deletion confirmation email"""
        
        if deletion_status == 'permanently_deleted':
            subject = "Your Account Has Been Permanently Deleted"
            message = f"""
Hello,

Your account has been permanently deleted as requested.

All your personal information, orders, addresses, and related data have been removed from our system.
This action is irreversible.

Deletion Time: {deletion_time.strftime('%Y-%m-%d %H:%M:%S')}

If you did not request this deletion or have any questions, please contact our support team.

Best regards,
{settings.APP_NAME} Team
"""
        else:  # anonymized
            subject = "Your Account Has Been Anonymized"
            message = f"""
Hello,

Your account has been anonymized as requested.

Your personal information has been removed and replaced with generic data.
You can no longer access your account with the original credentials.

Anonymization Time: {deletion_time.strftime('%Y-%m-%d %H:%M:%S')}

If you did not request this action or have any questions, please contact our support team.

Best regards,
{settings.APP_NAME} Team
"""
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            logger.info(f"Deletion confirmation email sent to {email}")
        except Exception as e:
            logger.error(f"Failed to send deletion confirmation email: {str(e)}")
            raise
    
    @staticmethod
    def can_delete_account(user, password=None):
        """
        Check if user account can be deleted
        
        Args:
            user: User instance
            password: User's password for verification
        
        Returns:
            tuple: (can_delete, reason)
        """
        
        # Check if user is already deleted
        if user.deleted_at:
            return False, "Account is already deleted"
        
        # Check for pending orders
        pending_orders = Order.objects.filter(
            user=user,
            status__in=['pending', 'confirmed', 'preparing', 'out_for_delivery']
        ).count()
        
        if pending_orders > 0:
            return False, f"You have {pending_orders} pending order(s). Please cancel them before deleting your account."
        
        return True, "Account can be deleted"
    
    @staticmethod
    def get_deletion_info(user):
        """Get information about what will be deleted"""
        
        return {
            'user': {
                'id': user.id,
                'email': user.email,
                'phone_number': user.phone_number,
                'name': f"{user.first_name} {user.last_name}",
            },
            'related_data': {
                'addresses': UserAddress.objects.filter(user=user).count(),
                'orders': Order.objects.filter(user=user).count(),
                'cart_items': Cart.objects.filter(user=user).count(),
                'profile': UserProfile.objects.filter(user=user).exists(),
                'google_oauth': GoogleOAuthToken.objects.filter(user=user).exists(),
            },
            'note': 'This action is irreversible. All data will be permanently deleted.'
        }
