from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from WhatsApp.models import WhatsAppConfiguration, WhatsAppTemplate
from WhatsApp.services import MSG91WhatsAppService
from django.conf import settings


class Command(BaseCommand):
    help = 'Manage MSG91 WhatsApp integration'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            type=str,
            choices=['test-connection', 'list-templates', 'create-config', 'verify-setup'],
            help='Action to perform'
        )

    def handle(self, *args, **options):
        action = options['action']

        if action == 'test-connection':
            self.test_connection()
        elif action == 'list-templates':
            self.list_templates()
        elif action == 'create-config':
            self.create_config()
        elif action == 'verify-setup':
            self.verify_setup()

    def test_connection(self):
        """Test MSG91 API connection"""
        self.stdout.write(self.style.WARNING('Testing MSG91 connection...'))

        try:
            service = MSG91WhatsAppService()
            success, response = service.get_templates()

            if success:
                self.stdout.write(
                    self.style.SUCCESS('✓ Connection successful!')
                )
                self.stdout.write(f"Response: {response}")
            else:
                self.stdout.write(
                    self.style.ERROR('✗ Connection failed!')
                )
                self.stdout.write(f"Error: {response}")

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Connection error: {str(e)}')
            )

    def list_templates(self):
        """List all WhatsApp templates"""
        self.stdout.write(self.style.WARNING('Fetching templates from MSG91...'))

        try:
            service = MSG91WhatsAppService()
            success, response = service.get_templates()

            if success:
                templates = response.get('data', [])
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Found {len(templates)} templates')
                )

                for template in templates:
                    self.stdout.write(f"\n  Name: {template.get('template_name')}")
                    self.stdout.write(f"  Status: {template.get('status')}")
                    self.stdout.write(f"  Category: {template.get('category')}")
            else:
                self.stdout.write(
                    self.style.ERROR('✗ Failed to fetch templates')
                )
                self.stdout.write(f"Error: {response}")

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error: {str(e)}')
            )

    def create_config(self):
        """Create default WhatsApp configuration"""
        self.stdout.write(self.style.WARNING('Creating configuration...'))

        try:
            config, created = WhatsAppConfiguration.objects.get_or_create(
                integrated_number=settings.MSG91_INTEGRATED_NUMBER,
                defaults={
                    'is_active': True,
                    'daily_limit': 10000,
                    'monthly_limit': 300000,
                }
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS('✓ Configuration created successfully')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('✓ Configuration already exists')
                )

            self.stdout.write(f"\nNumber: {config.integrated_number}")
            self.stdout.write(f"Active: {config.is_active}")
            self.stdout.write(f"Daily Limit: {config.daily_limit}")
            self.stdout.write(f"Monthly Limit: {config.monthly_limit}")

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error: {str(e)}')
            )

    def verify_setup(self):
        """Verify complete WhatsApp setup"""
        self.stdout.write(self.style.WARNING('Verifying WhatsApp setup...\n'))

        checks = {
            'MSG91_AUTH_KEY': settings.MSG91_AUTH_KEY,
            'MSG91_INTEGRATED_NUMBER': settings.MSG91_INTEGRATED_NUMBER,
            'Configuration': WhatsAppConfiguration.objects.filter(
                integrated_number=settings.MSG91_INTEGRATED_NUMBER
            ).exists(),
            'Superuser': User.objects.filter(is_superuser=True).exists(),
        }

        all_passed = True

        for check, value in checks.items():
            if value:
                self.stdout.write(f"  ✓ {check}")
            else:
                self.stdout.write(
                    self.style.ERROR(f"  ✗ {check}")
                )
                all_passed = False

        self.stdout.write('\n')

        # Test connection
        try:
            service = MSG91WhatsAppService()
            success, _ = service.get_templates()
            if success:
                self.stdout.write("  ✓ MSG91 API Connection")
            else:
                self.stdout.write(self.style.ERROR("  ✗ MSG91 API Connection"))
                all_passed = False
        except:
            self.stdout.write(self.style.ERROR("  ✗ MSG91 API Connection"))
            all_passed = False

        self.stdout.write('\n')

        if all_passed:
            self.stdout.write(
                self.style.SUCCESS('✓ All checks passed! WhatsApp is ready to use.')
            )
        else:
            self.stdout.write(
                self.style.ERROR('✗ Some checks failed. Please review the setup.')
            )
