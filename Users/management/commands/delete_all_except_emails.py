from django.core.management.base import BaseCommand
from django.db import transaction, connection
from Users.models import User


class Command(BaseCommand):
    help = 'Delete all users except specified emails. WARNING: This is irreversible!'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation and force delete',
        )

    def handle(self, *args, **options):
        # Emails to preserve
        preserve_emails = [
            'khaderrizan@gmail.com',
            'admin@simakfresh.ae',
            'delivery-admin@demo.com',
        ]
        
        self.stdout.write(self.style.WARNING('⚠️  WARNING: This will delete ALL users except the following!'))
        self.stdout.write('')
        
        for email in preserve_emails:
            self.stdout.write(f'  • {email}')
        
        self.stdout.write('')
        
        # Count users
        preserve_count = User.objects.filter(email__in=preserve_emails).count()
        total_users = User.objects.count()
        delete_count = total_users - preserve_count
        
        self.stdout.write(self.style.SUCCESS(f'✓ Users to KEEP: {preserve_count}'))
        self.stdout.write(self.style.ERROR(f'Records to be DELETED: {delete_count}'))
        self.stdout.write('')
        
        if delete_count == 0:
            self.stdout.write(self.style.SUCCESS('✓ No users to delete. Database is already clean!'))
            return
        
        if not options['force']:
            confirm = input(self.style.WARNING(f'Are you sure you want to delete {delete_count} users? (yes/no): '))
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('✗ Deletion cancelled.'))
                return
        
        try:
            self.stdout.write('Preparing for deletion...')
            
            # Get users to delete
            users_to_delete = User.objects.exclude(email__in=preserve_emails)
            users_to_delete_ids = list(users_to_delete.values_list('id', flat=True))
            
            if users_to_delete_ids:
                # Clear foreign key references with explicit commit
                try:
                    with connection.cursor() as cursor:
                        # List of (table, column) pairs that reference users
                        fk_references = [
                            ('"SMS_smstemplate"', 'created_by_id'),
                            ('"SMS_smsmessage"', 'sent_by_id'),
                            ('"WhatsApp_whatsapptemplate"', 'created_by_id'),
                            ('"Notifications_contactmessage"', 'created_by_id'),
                        ]
                        
                        for table, column in fk_references:
                            try:
                                query = f"UPDATE {table} SET {column} = NULL WHERE {column} = ANY(%s)"
                                cursor.execute(query, [users_to_delete_ids])
                                count = cursor.rowcount
                                if count > 0:
                                    self.stdout.write(f'  • Cleared {count} references in {table}')
                            except Exception:
                                pass  # Table may not exist or FK may not have data
                    
                    # Commit the changes explicitly
                    connection.commit()
                    self.stdout.write(self.style.SUCCESS('  ✓ FK references cleared'))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  ⚠ FK cleanup warning: {type(e).__name__}'))
            
            # Now delete users in a transaction
            with transaction.atomic():
                self.stdout.write('Deleting users...')
                
                # Delete users not in preserve list
                deleted_count, deleted_dict = users_to_delete.delete()
                
                self.stdout.write('')
                self.stdout.write(self.style.SUCCESS('✓ Deletion completed successfully!'))
                self.stdout.write('')
                self.stdout.write(f'Total records deleted: {deleted_count}')
                self.stdout.write('')
                self.stdout.write('Breakdown by model:')
                for model, count in deleted_dict.items():
                    self.stdout.write(f'  • {model}: {count}')
                
                # Show final count
                self.stdout.write('')
                self.stdout.write(self.style.SUCCESS('✓ Final User Count:'))
                remaining_users = User.objects.all()
                for user in remaining_users:
                    role = user.role if hasattr(user, 'role') else 'unknown'
                    self.stdout.write(f'  • {user.email} (role: {role})')
                self.stdout.write(f'\nTotal Users Remaining: {remaining_users.count()}')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error during deletion: {str(e)}'))
            raise
