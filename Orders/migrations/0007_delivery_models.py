from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('Orders', '0006_remove_payment_telr_reference_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DeliveryAssignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('ASSIGNED', 'Assigned'), ('IN_TRANSIT', 'In Transit'), ('COMPLETED', 'Completed')], default='ASSIGNED', max_length=20, verbose_name='assignment status')),
                ('assigned_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('accepted_at', models.DateTimeField(blank=True, null=True)),
                ('delivered_at', models.DateTimeField(blank=True, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('assigned_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_deliveries', to=settings.AUTH_USER_MODEL, verbose_name='assigned by')),
                ('delivery_boy', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='delivery_assignments', to=settings.AUTH_USER_MODEL, verbose_name='delivery boy')),
                ('order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='delivery_assignment', to='Orders.order', verbose_name='order')),
            ],
            options={
                'verbose_name': 'Delivery Assignment',
                'verbose_name_plural': 'Delivery Assignments',
                'ordering': ['-assigned_at'],
                'indexes': [models.Index(fields=['delivery_boy', 'status'], name='delivery_boy_status_idx')],
            },
        ),
        migrations.CreateModel(
            name='DeliveryCancellationRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason', models.TextField(verbose_name='reason')),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')], db_index=True, default='PENDING', max_length=20, verbose_name='request status')),
                ('review_notes', models.TextField(blank=True, null=True, verbose_name='review notes')),
                ('requested_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='delivery_cancel_request', to='Orders.order', verbose_name='order')),
                ('requested_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='delivery_cancel_requests', to=settings.AUTH_USER_MODEL, verbose_name='requested by')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_delivery_cancel_requests', to=settings.AUTH_USER_MODEL, verbose_name='reviewed by')),
            ],
            options={
                'verbose_name': 'Delivery Cancellation Request',
                'verbose_name_plural': 'Delivery Cancellation Requests',
                'ordering': ['-requested_at'],
            },
        ),
        migrations.CreateModel(
            name='DeliveryProof',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('proof_image', models.ImageField(upload_to='delivery/proofs/')),
                ('signature_name', models.CharField(blank=True, max_length=255, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('assignment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='proofs', to='Orders.deliveryassignment', verbose_name='delivery assignment')),
                ('order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='delivery_proof', to='Orders.order', verbose_name='order')),
                ('uploaded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='uploaded_delivery_proofs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Delivery Proof',
                'verbose_name_plural': 'Delivery Proofs',
                'ordering': ['-created_at'],
            },
        ),
    ]
