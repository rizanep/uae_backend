"""
Management command to view and analyze webhook logs.
Usage:
    python manage.py webhook_logs              # Show recent events
    python manage.py webhook_logs --tail 50   # Show last 50 events
    python manage.py webhook_logs --search "Payment #42"  # Search for specific payment
    python manage.py webhook_logs --stats     # Show statistics
    python manage.py webhook_logs --errors    # Show only errors
"""

import os
from django.core.management.base import BaseCommand
from django.conf import settings
from datetime import datetime
from collections import Counter


class Command(BaseCommand):
    help = 'View and analyze webhook logs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tail',
            type=int,
            default=20,
            help='Number of recent lines to show (default: 20)'
        )
        parser.add_argument(
            '--search',
            type=str,
            help='Search for specific text in logs'
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Show log statistics'
        )
        parser.add_argument(
            '--errors',
            action='store_true',
            help='Show only errors and warnings'
        )
        parser.add_argument(
            '--payments',
            action='store_true',
            help='Show only payment-related logs'
        )

    def read_webhook_log(self):
        """Read webhook log file"""
        log_path = os.path.join(settings.BASE_DIR, 'logs', 'webhooks.log')
        if not os.path.exists(log_path):
            return []
        
        with open(log_path, 'r') as f:
            return f.readlines()

    def handle(self, *args, **options):
        lines = self.read_webhook_log()
        
        if not lines:
            self.stdout.write(self.style.WARNING('No webhook logs found'))
            return

        if options['stats']:
            self.show_stats(lines)
        elif options['search']:
            self.search_logs(lines, options['search'])
        elif options['errors']:
            self.show_errors(lines)
        elif options['payments']:
            self.show_payments(lines)
        else:
            self.show_recent(lines, options['tail'])

    def show_recent(self, lines, tail_count):
        """Show recent webhook events"""
        self.stdout.write(self.style.SUCCESS(f'\n=== Latest {tail_count} Webhook Events ===\n'))
        
        for line in lines[-tail_count:]:
            self.color_line(line)

    def show_errors(self, lines):
        """Show only errors and warnings"""
        self.stdout.write(self.style.WARNING('\n=== Errors & Warnings ===\n'))
        
        error_lines = [l for l in lines if 'ERROR' in l or 'WARNING' in l]
        
        if not error_lines:
            self.stdout.write(self.style.SUCCESS('✓ No errors or warnings found'))
            return
        
        for line in error_lines:
            self.color_line(line)

    def search_logs(self, lines, search_term):
        """Search for text in logs"""
        self.stdout.write(self.style.SUCCESS(f'\n=== Search Results for "{search_term}" ===\n'))
        
        results = [l for l in lines if search_term in l]
        
        if not results:
            self.stdout.write(self.style.WARNING(f'No results found for "{search_term}"'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Found {len(results)} matching entries:\n'))
        
        for line in results:
            self.color_line(line)

    def show_payments(self, lines):
        """Show payment-related events"""
        self.stdout.write(self.style.SUCCESS('\n=== Payment Processing Events ===\n'))
        
        payment_lines = [l for l in lines if 'Webhook processed' in l or 'Payment' in l]
        
        if not payment_lines:
            self.stdout.write(self.style.WARNING('No payment events found'))
            return
        
        for line in payment_lines[-20:]:  # Show last 20
            self.color_line(line)

    def show_stats(self, lines):
        """Show log statistics"""
        self.stdout.write(self.style.SUCCESS('\n=== Webhook Log Statistics ===\n'))
        
        # Count events by level
        levels = Counter()
        for line in lines:
            if 'INFO' in line:
                levels['INFO'] += 1
            elif 'WARNING' in line:
                levels['WARNING'] += 1
            elif 'ERROR' in line:
                levels['ERROR'] += 1
        
        # Count successful vs failed payments
        success = len([l for l in lines if 'PENDING to SUCCESS' in l])
        failed = len([l for l in lines if 'PENDING to FAILED' in l])
        
        # Count signature issues
        signature_issues = len([l for l in lines if 'signature' in l.lower()])
        
        # Extract unique payments and orders
        payment_ids = set()
        order_ids = set()
        for line in lines:
            if 'Payment #' in line:
                try:
                    payment_id = line.split('Payment #')[1].split(' ')[0] if 'Payment #' in line else None
                    if payment_id:
                        payment_ids.add(payment_id)
                except:
                    pass
            if 'Order #' in line:
                try:
                    order_id = line.split('Order #')[1].split(')')[0] if 'Order #' in line else None
                    if order_id:
                        order_ids.add(order_id)
                except:
                    pass
        
        self.stdout.write(f'Total log entries: {len(lines)}')
        self.stdout.write(f'\nBy Level:')
        self.stdout.write(f'  INFO:    {levels["INFO"]}')
        self.stdout.write(f'  WARNING: {levels["WARNING"]}')
        self.stdout.write(f'  ERROR:   {levels["ERROR"]}')
        
        self.stdout.write(f'\nPayment Processing:')
        self.stdout.write(f'  Successful: {success}')
        self.stdout.write(f'  Failed:     {failed}')
        self.stdout.write(f'  Unique Payments: {len(payment_ids)}')
        self.stdout.write(f'  Unique Orders: {len(order_ids)}')
        
        self.stdout.write(f'\nSignature Issues: {signature_issues}')
        
        # Calculate success rate
        total_payments = success + failed
        if total_payments > 0:
            success_rate = (success / total_payments) * 100
            self.stdout.write(f'  Success Rate: {success_rate:.1f}%\n')

    def color_line(self, line):
        """Color a log line based on level"""
        line = line.rstrip()
        
        if 'ERROR' in line:
            self.stdout.write(self.style.ERROR(line))
        elif 'WARNING' in line:
            self.stdout.write(self.style.WARNING(line))
        elif 'SUCCESS' in line or 'success' in line:
            self.stdout.write(self.style.SUCCESS(line))
        else:
            self.stdout.write(line)
