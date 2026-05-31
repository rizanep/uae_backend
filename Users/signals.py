from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, UserProfile, DeliveryBoyProfile
from Marketing.services import create_first_order_coupon, grant_referral_rewards, generate_referral_code

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create a UserProfile whenever a new User is created.
    Also handle marketing logic (referral codes, coupons).
    """
    if created:
        # Create Profile
        UserProfile.objects.get_or_create(user=instance)
        if instance.role == 'delivery_boy':
            DeliveryBoyProfile.objects.get_or_create(user=instance)
        
        # Generate Referral Code for the new user
        if not instance.referral_code:
            instance.referral_code = generate_referral_code()
            instance.save(update_fields=['referral_code'])
        
        # Create First Order Coupon
        create_first_order_coupon(instance)
        
        # Check if user was referred by someone (referred_by set during creation)
        if instance.referred_by and not instance.referral_reward_claimed:
            grant_referral_rewards(referrer=instance.referred_by, referee=instance)
            instance.referral_reward_claimed = True
            instance.save(update_fields=['referral_reward_claimed'])

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Ensure the UserProfile is saved whenever the User is updated.
    """
    if hasattr(instance, 'profile'):
        instance.profile.save()

    if instance.role == 'delivery_boy':
        DeliveryBoyProfile.objects.get_or_create(user=instance)
