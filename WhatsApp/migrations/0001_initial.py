# Generated migration for WhatsApp models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='WhatsAppTemplate',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('template_name', models.CharField(db_index=True, max_length=512, unique=True)),
                ('integrated_number', models.CharField(max_length=20)),
                ('language', models.CharField(choices=[('en', 'English'), ('ar', 'Arabic'), ('hi', 'Hindi'), ('ur', 'Urdu')], default='en', max_length=10)),
                ('category', models.CharField(choices=[('MARKETING', 'Marketing'), ('AUTHENTICATION', 'Authentication'), ('TRANSACTIONAL', 'Transactional'), ('UTILITY', 'Utility')], default='MARKETING', max_length=50)),
                ('header_format', models.CharField(blank=True, choices=[('TEXT', 'Text'), ('IMAGE', 'Image'), ('VIDEO', 'Video'), ('DOCUMENT', 'Document'), ('LOCATION', 'Location')], max_length=20, null=True)),
                ('header_text', models.TextField(blank=True, null=True)),
                ('header_example', models.JSONField(blank=True, null=True)),
                ('body_text', models.TextField()),
                ('body_example', models.JSONField(blank=True, null=True)),
                ('footer_text', models.TextField(blank=True, null=True)),
                ('buttons', models.JSONField(blank=True, default=list)),
                ('is_approved', models.BooleanField(default=False)),
                ('approval_status', models.CharField(choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected'), ('DISABLED', 'Disabled')], db_index=True, default='PENDING', max_length=20)),
                ('rejection_reason', models.TextField(blank=True, null=True)),
                ('msg91_template_id', models.CharField(blank=True, max_length=255, null=True, unique=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='whatsapp_templates_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='WhatsAppMessage',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('recipient_number', models.CharField(db_index=True, max_length=20)),
                ('variables', models.JSONField(blank=True, default=dict)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('SENT', 'Sent'), ('DELIVERED', 'Delivered'), ('READ', 'Read'), ('FAILED', 'Failed')], db_index=True, default='PENDING', max_length=20)),
                ('msg91_message_id', models.CharField(blank=True, max_length=255, null=True, unique=True)),
                ('response_data', models.JSONField(blank=True, null=True)),
                ('error_message', models.TextField(blank=True, null=True)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('delivered_at', models.DateTimeField(blank=True, null=True)),
                ('read_at', models.DateTimeField(blank=True, null=True)),
                ('sent_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='whatsapp_messages_sent', to=settings.AUTH_USER_MODEL)),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='messages', to='WhatsApp.whatsapptemplate')),
            ],
            options={
                'ordering': ['-created_at'],
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='WhatsAppWebhookLog',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('event_type', models.CharField(max_length=50)),
                ('payload', models.JSONField()),
                ('is_processed', models.BooleanField(default=False)),
                ('processing_error', models.TextField(blank=True, null=True)),
                ('message', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='webhook_logs', to='WhatsApp.whatsappmessage')),
            ],
            options={
                'ordering': ['-created_at'],
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='WhatsAppConfiguration',
            fields=[
                ('integrated_number', models.CharField(max_length=20, primary_key=True, serialize=False)),
                ('is_active', models.BooleanField(default=True)),
                ('daily_limit', models.IntegerField(default=10000, help_text='Daily message limit')),
                ('monthly_limit', models.IntegerField(default=300000, help_text='Monthly message limit')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'WhatsApp Configurations',
            },
        ),
        # Add database indexes
        migrations.AddIndex(
            model_name='whatsapptemplate',
            index=models.Index(fields=['template_name', 'deleted_at'], name='WhatsApp_wh_templa_idx'),
        ),
        migrations.AddIndex(
            model_name='whatsapptemplate',
            index=models.Index(fields=['approval_status', 'deleted_at'], name='WhatsApp_wh_approv_idx'),
        ),
        migrations.AddIndex(
            model_name='whatsapptemplate',
            index=models.Index(fields=['integrated_number', 'deleted_at'], name='WhatsApp_wh_integr_idx'),
        ),
        migrations.AddIndex(
            model_name='whatsappmessage',
            index=models.Index(fields=['recipient_number', 'status', 'deleted_at'], name='WhatsApp_wh_recipi_idx'),
        ),
        migrations.AddIndex(
            model_name='whatsappmessage',
            index=models.Index(fields=['template', 'status', 'deleted_at'], name='WhatsApp_wh_templ_status_idx'),
        ),
        migrations.AddIndex(
            model_name='whatsappmessage',
            index=models.Index(fields=['created_at', 'deleted_at'], name='WhatsApp_wh_create_idx'),
        ),
        migrations.AddIndex(
            model_name='whatsappwebhooklog',
            index=models.Index(fields=['event_type', 'is_processed', 'deleted_at'], name='WhatsApp_wh_event_idx'),
        ),
    ]
