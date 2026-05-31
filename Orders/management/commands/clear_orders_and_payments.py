from django.core.management.base import BaseCommand
from django.db import transaction
from Orders.models import (
    Order, OrderItem, OrderStatusHistory, 
    DeliveryAssignment, DeliveryCancellationRequest, 
    DeliveryProof, Payment, Receipt
)


class Command(BaseCommand):
    help = 'Delete all orders, payments, and related data. WARNING: This is irreversible!'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation and force delete',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('⚠️  WARNING: This will delete ALL orders, payments, and related data!'))
        self.stdout.write('')
        
        # Count records
        order_count = Order.objects.count()
        payment_count = Payment.objects.count()
        receipt_count = Receipt.objects.count()
        order_item_count = OrderItem.objects.count()
        status_history_count = OrderStatusHistory.objects.count()
        delivery_assignment_count = DeliveryAssignment.objects.count()
        cancel_request_count = DeliveryCancellationRequest.objects.count()
        delivery_proof_count = DeliveryProof.objects.count()
        
        total_records = (
            order_count + payment_count + receipt_count + 
            order_item_count + status_history_count + 
            delivery_assignment_count + cancel_request_count + 
            delivery_proof_count
        )
        
        self.stdout.write(self.style.ERROR(f'Records to be deleted:'))
        self.stdout.write(f'  • Orders: {order_count}')
        self.stdout.write(f'  • Payments: {payment_count}')
        self.stdout.write(f'  • Receipts: {receipt_count}')
        self.stdout.write(f'  • Order Items: {order_item_count}')
        self.stdout.write(f'  • Status History: {status_history_count}')
        self.stdout.write(f'  • Delivery Assignments: {delivery_assignment_count}')
        self.stdout.write(f'  • Cancellation Requests: {cancel_request_count}')
        self.stdout.write(f'  • Delivery Proofs: {delivery_proof_count}')
        self.stdout.write('')
        self.stdout.write(self.style.ERROR(f'TOTAL: {total_records} records'))
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
                
                # Delete all orders (this cascades to related models)
                deleted_count, deleted_dict = Order.objects.all().delete()
                
                self.stdout.write('')
                self.stdout.write(self.style.SUCCESS('✓ Deletion completed successfully!'))
                self.stdout.write('')
                self.stdout.write('Deleted:')
                for model, count in deleted_dict.items():
                    self.stdout.write(f'  • {model}: {count}')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error during deletion: {str(e)}'))
            raise
