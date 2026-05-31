from django.core.management.base import BaseCommand
from django.db import transaction
from Marketing.models import Coupon
from Notifications.models import (
    Notification, NotificationTemplate, Broadcast,
    ContactMessage
)


class Command(BaseCommand):
    help = 'Delete all coupons and notifications data (excluding marketing media, FCM devices, and reward configs). WARNING: This is irreversible!'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation and force delete',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('⚠️  WARNING: This will delete ALL coupons and notifications data!'))
        self.stdout.write('')
        
        # Count records
        coupon_count = Coupon.objects.count()
        notification_count = Notification.objects.count()
        template_count = NotificationTemplate.objects.count()
        broadcast_count = Broadcast.objects.count()
        contact_message_count = ContactMessage.objects.count()
        
        total_records = (
            coupon_count + notification_count +
            template_count + broadcast_count + contact_message_count
        )
        
        self.stdout.write(self.style.ERROR(f'Records to be deleted:'))
        self.stdout.write(f'  • Coupons: {coupon_count}')
        self.stdout.write(f'  • Notifications: {notification_count}')
        self.stdout.write(f'  • Notification Templates: {template_count}')
        self.stdout.write(f'  • Broadcasts: {broadcast_count}')
        self.stdout.write(f'  • Contact Messages: {contact_message_count}')
        self.stdout.write('')
        self.stdout.write(self.style.ERROR(f'TOTAL: {total_records} records'))
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✓ Kept (NOT deleted):'))
        self.stdout.write(f'  • Marketing Media')
        self.stdout.write(f'  • FCM Devices')
        self.stdout.write(f'  • Reward Configurations')
        self.stdout.write('')
        
        if total_records == 0:
            self.stdout.write(self.style.SUCCESS('✓ No data to delete. Database is already clean!'))
            return
        
        if not options['force']:
            confirm = input(self.style.WARNING('Are you sure you want to delete all this data? (yes/no): '))
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('✗ Deletion cancelled.'))
                return
        
        try:
            with transaction.atomic():
                self.stdout.write('Deleting data...')
                
                deleted_dict = {}
                
                # Delete Notifications (will cascade to related records)
                count, details = Notification.objects.all().delete()
                if count > 0:
                    deleted_dict.update(details)
                
                # Delete Broadcasts
                count, details = Broadcast.objects.all().delete()
                if count > 0:
                    deleted_dict.update(details)
                
                # Delete NotificationTemplates
                count, details = NotificationTemplate.objects.all().delete()
                if count > 0:
                    deleted_dict.update(details)
                
                # Delete ContactMessages
                count, details = ContactMessage.objects.all().delete()
                if count > 0:
                    deleted_dict.update(details)
                
                # Delete Coupons
                count, details = Coupon.objects.all().delete()
                if count > 0:
                    deleted_dict.update(details)
                
                self.stdout.write('')
                self.stdout.write(self.style.SUCCESS('✓ Deletion completed successfully!'))
                self.stdout.write('')
                self.stdout.write('Deleted:')
                for model, count in deleted_dict.items():
                    self.stdout.write(f'  • {model}: {count}')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error during deletion: {str(e)}'))
            raise
