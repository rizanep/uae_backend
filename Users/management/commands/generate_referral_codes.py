"""
Management command to generate referral codes for users who don't have one.
Usage:
    python manage.py generate_referral_codes
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from Users.models import User
from Marketing.services import generate_referral_code


class Command(BaseCommand):
    help = 'Generate referral codes for users who don\'t have one'

    def handle(self, *args, **options):
        # Find users without referral codes
        users_without_code = User.objects.filter(
            referral_code__isnull=True,
            deleted_at__isnull=True
        )
        
        count = users_without_code.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS('All users already have referral codes!'))
            return
        
        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write(f"Generating referral codes for {count} users...")
        self.stdout.write(f"{'=' * 60}\n")
        
        generated = 0
        failed = 0
        
        with transaction.atomic():
            for user in users_without_code:
                try:
                    user.referral_code = generate_referral_code()
                    user.save(update_fields=['referral_code'])
                    generated += 1
                    self.stdout.write(
                        f"✓ {user.email or user.phone_number}: {user.referral_code}"
                    )
                except Exception as e:
                    failed += 1
                    self.stdout.write(
                        self.style.ERROR(f"✗ {user.email or user.phone_number}: {str(e)}")
                    )
        
        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write(self.style.SUCCESS(f"Generated: {generated}"))
        if failed:
            self.stdout.write(self.style.ERROR(f"Failed: {failed}"))
        self.stdout.write(f"{'=' * 60}\n")
