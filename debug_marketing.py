import os
import django
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from Marketing.models import MarketingMedia

print(f"Current Time (UTC): {timezone.now()}")

medias = MarketingMedia.objects.all() # Get everything, including soft deleted ones if the manager allows, or raw query
# SoftDeleteModel usually overrides 'objects' to exclude deleted.
# Let's use MarketingMedia.all_objects.all() if it exists, or just objects.all() and check the DB directly.

print(f"Total Media Found: {medias.count()}")

for media in medias:
    print(f"--- Media ID: {media.id} ---")
    print(f"Title: {media.title}")
    print(f"Is Active: {media.is_active}")
    print(f"Start At: {media.start_at}")
    print(f"End At: {media.end_at}")
    print(f"Deleted At: {media.deleted_at}")
    
    now = timezone.now()
    
    is_active = media.is_active
    not_deleted = media.deleted_at is None
    started = media.start_at is None or media.start_at <= now
    not_ended = media.end_at is None or media.end_at >= now
    
    print(f"Logic Check:")
    print(f"  - Not Deleted: {not_deleted}")
    print(f"  - Is Active: {is_active}")
    print(f"  - Started (<= {now}): {started}")
    print(f"  - Not Ended (>= {now}): {not_ended}")
    
    if is_active and not_deleted and started and not_ended:
        print("  => RESULT: SHOULD BE VISIBLE")
    else:
        print("  => RESULT: HIDDEN")
