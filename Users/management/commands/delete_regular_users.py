from django.core.management.base import BaseCommand
from django.db import transaction, connection
from Users.models import User


class Command(BaseCommand):
    help = 'Delete all users except delivery boys and admins. WARNING: This is irreversible!'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation and force delete',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('⚠️  WARNING: This will delete ALL regular users!'))
        self.stdout.write('')
        
        # Count users by role
        admin_count = User.objects.filter(role='admin').count()
        delivery_boy_count = User.objects.filter(role='delivery_boy').count()
        user_count = User.objects.filter(role='user').count()
        superuser_count = User.objects.filter(is_superuser=True).count()
        
        self.stdout.write(self.style.SUCCESS('✓ Users to KEEP:'))
        self.stdout.write(f'  • Admins: {admin_count}')
        self.stdout.write(f'  • Delivery Boys: {delivery_boy_count}')
        self.stdout.write(f'  • Superusers: {superuser_count}')
        self.stdout.write('')
        
        self.stdout.write(self.style.ERROR('Records to be DELETED:'))
        self.stdout.write(f'  • Regular Users: {user_count}')
        self.stdout.write('')
        
        if user_count == 0:
            self.stdout.write(self.style.SUCCESS('✓ No regular users to delete. Database is clean!'))
            return
        
        if not options['force']:
            confirm = input(self.style.WARNING(f'Are you sure you want to delete {user_count} regular users? (yes/no): '))
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('✗ Deletion cancelled.'))
                return
        
        try:
            self.stdout.write('Preparing for deletion...')
            
            # Get user IDs to delete
            users_to_delete_ids = list(User.objects.filter(role='user').values_list('id', flat=True))
            
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
                self.stdout.write('Deleting regular users...')
                
                # Delete all users with role='user' (not delivery_boy or admin)
                users_to_delete = User.objects.filter(role='user')
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
                self.stdout.write(f'  • Admins: {User.objects.filter(role="admin").count()}')
                self.stdout.write(f'  • Delivery Boys: {User.objects.filter(role="delivery_boy").count()}')
                self.stdout.write(f'  • Total Users Remaining: {User.objects.count()}')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error during deletion: {str(e)}'))
            raise
