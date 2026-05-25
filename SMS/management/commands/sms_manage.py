from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from SMS.services import MSG91SMSService
from SMS.models import SMSTemplate, SMSMessage


class Command(BaseCommand):
    help = 'SMS Management Commands - test, verify, sync'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            type=str,
            choices=['test-connection', 'verify-setup', 'sync-templates'],
            help='Action to perform'
        )
        parser.add_argument(
            '--phone',
            type=str,
            help='Phone number for test SMS (with country code)'
        )
        parser.add_argument(
            '--template-id',
            type=str,
            help='Template ID to sync'
        )

    def handle(self, *args, **options):
        action = options['action']

        if action == 'test-connection':
            self.test_connection()
        elif action == 'verify-setup':
            self.verify_setup()
        elif action == 'sync-templates':
            self.sync_templates(options.get('template_id'))

    def test_connection(self):
        """Test MSG91 connection"""
        self.stdout.write(self.style.WARNING('Testing MSG91 connection...'))

        try:
            service = MSG91SMSService()
            
            # Try to get templates (lightweight test)
            success, response = service.get_template_versions()
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS('✓ MSG91 connection successful!')
                )
                self.stdout.write(f"  Response: {response}")
            else:
                self.stdout.write(
                    self.style.ERROR('✗ MSG91 connection failed!')
                )
                self.stdout.write(f"  Error: {response}")
        except Exception as e:
            raise CommandError(f'Connection test failed: {str(e)}')

    def verify_setup(self):
        """Verify SMS setup"""
        self.stdout.write(self.style.WARNING('Verifying SMS setup...'))

        issues = []

        # Check if SMS app is installed
        from django.apps import apps
        try:
            apps.get_app_config('SMS')
            self.stdout.write(self.style.SUCCESS('✓ SMS app installed'))
        except LookupError:
            issues.append('SMS app not installed in INSTALLED_APPS')

        # Check for templates
        template_count = SMSTemplate.objects.filter(deleted_at__isnull=True).count()
        if template_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'✓ {template_count} SMS templates found')
            )
        else:
            issues.append('No SMS templates found')

        # Check for environment variables
        import os
        required_env_vars = ['MSG91_AUTH_KEY', 'MSG91_ROUTE']
        missing_vars = []
        for var in required_env_vars:
            if not os.environ.get(var):
                missing_vars.append(var)

        if missing_vars:
            issues.append(f'Missing environment variables: {", ".join(missing_vars)}')
        else:
            self.stdout.write(
                self.style.SUCCESS('✓ Required environment variables set')
            )

        if issues:
            self.stdout.write(self.style.ERROR('\nIssues found:'))
            for idx, issue in enumerate(issues, 1):
                self.stdout.write(f"  {idx}. {issue}")
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ SMS setup verified successfully!'))

    def sync_templates(self, template_id=None):
        """Sync templates with MSG91"""
        self.stdout.write(self.style.WARNING('Syncing templates with MSG91...'))

        try:
            service = MSG91SMSService()
            
            # Get templates to sync
            if template_id:
                templates = SMSTemplate.objects.filter(
                    id=template_id,
                    deleted_at__isnull=True
                )
            else:
                templates = SMSTemplate.objects.filter(
                    is_approved=True,
                    deleted_at__isnull=True
                )

            if not templates.exists():
                self.stdout.write(
                    self.style.WARNING('No templates to sync')
                )
                return

            synced_count = 0
            failed_count = 0

            for template in templates:
                self.stdout.write(f'\nSyncing: {template.template_name}')

                try:
                    success, response = service.create_template(
                        template_name=template.template_name,
                        template_content=template.template_content,
                        sender_id=template.sender_id,
                        sms_type=template.sms_type,
                        dlt_template_id=template.dlt_template_id
                    )

                    if success:
                        msg91_id = response.get('data', {}).get('template_id')
                        template.msg91_template_id = msg91_id
                        template.save()
                        
                        self.stdout.write(
                            self.style.SUCCESS(f'  ✓ Synced (ID: {msg91_id})')
                        )
                        synced_count += 1
                    else:
                        error = response.get('message', 'Unknown error')
                        self.stdout.write(
                            self.style.ERROR(f'  ✗ Failed: {error}')
                        )
                        failed_count += 1

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ Error: {str(e)}')
                    )
                    failed_count += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✓ Sync complete: {synced_count} synced, {failed_count} failed'
                )
            )

        except Exception as e:
            raise CommandError(f'Sync failed: {str(e)}')
