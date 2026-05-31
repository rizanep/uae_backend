import os
import django
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from Marketing.models import MarketingMedia

# Restore ID 1
try:
    media = MarketingMedia.objects.get(id=1)
    if media.deleted_at:
        print(f"Restoring media: {media.title} (ID: {media.id})")
        media.restore()
        print("Restored successfully.")
    else:
        print("Media is not deleted.")
except MarketingMedia.DoesNotExist:
    print("Media ID 1 not found.")
