from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, UserProfile

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create a UserProfile whenever a new User is created.
    """
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Ensure the UserProfile is saved whenever the User is updated.
    """
    if hasattr(instance, 'profile'):
        instance.profile.save()
