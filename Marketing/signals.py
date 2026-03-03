
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import MarketingMedia

@receiver(post_save, sender=MarketingMedia)
@receiver(post_delete, sender=MarketingMedia)
def clear_marketing_media_cache(sender, instance, **kwargs):
    """
    Clear marketing media cache when an item is created, updated, or deleted.
    """
    cache.delete("marketing_media_list_public")
    cache.delete("marketing_media_list_staff")
