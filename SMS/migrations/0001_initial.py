# Generated migration for SMS models

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
            name='SMSTemplate',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('template_name', models.CharField(db_index=True, max_length=256, unique=True)),
                ('template_content', models.TextField(help_text='Use {{VAR1}}, {{VAR2}} for variables')),
                ('sender_id', models.CharField(help_text='Sender ID (max 11 chars)', max_length=11)),
                ('sms_type', models.CharField(choices=[('NORMAL', 'Normal'), ('TRANSACTIONAL', 'Transactional'), ('OTP', 'OTP'), ('PROMOTIONAL', 'Promotional')], default='NORMAL', max_length=20)),
                ('dlt_template_id', models.CharField(blank=True, help_text='DLT Template ID for Indian SMS', max_length=255, null=True)),
                ('character_count', models.IntegerField(default=0, help_text='Character count of template')),
                ('sms_parts', models.IntegerField(default=1, help_text='Number of SMS parts needed')),
                ('is_approved', models.BooleanField(default=False)),
                ('approval_status', models.CharField(choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected'), ('DISABLED', 'Disabled')], db_index=True, default='PENDING', max_length=20)),
                ('rejection_reason', models.TextField(blank=True, null=True)),
                ('msg91_template_id', models.CharField(blank=True, max_length=255, null=True, unique=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sms_templates_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SMSMessage',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('recipient_number', models.CharField(db_index=True, max_length=20)),
                ('variables', models.JSONField(blank=True, default=dict)),
                ('message_content', models.TextField()),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('SENT', 'Sent'), ('DELIVERED', 'Delivered'), ('FAILED', 'Failed'), ('BOUNCED', 'Bounced')], db_index=True, default='PENDING', max_length=20)),
                ('msg91_message_id', models.CharField(blank=True, max_length=255, null=True, unique=True)),
                ('response_data', models.JSONField(blank=True, null=True)),
                ('error_message', models.TextField(blank=True, null=True)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('delivered_at', models.DateTimeField(blank=True, null=True)),
                ('sent_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sms_messages_sent', to=settings.AUTH_USER_MODEL)),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='messages', to='SMS.smstemplate')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SMSWebhookLog',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('event_type', models.CharField(max_length=50)),
                ('payload', models.JSONField()),
                ('is_processed', models.BooleanField(default=False)),
                ('processing_error', models.TextField(blank=True, null=True)),
                ('message', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='webhook_logs', to='SMS.smsmessage')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SMSConfiguration',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('sender_id', models.CharField(help_text='Default sender ID', max_length=11)),
                ('is_active', models.BooleanField(default=True)),
                ('daily_limit', models.IntegerField(default=10000, help_text='Daily message limit')),
                ('monthly_limit', models.IntegerField(default=300000, help_text='Monthly message limit')),
                ('cost_per_sms', models.DecimalField(decimal_places=4, default=0.5, max_digits=10)),
                ('enable_short_url', models.BooleanField(default=False)),
                ('short_url_expiry', models.IntegerField(default=3600, help_text='Seconds')),
                ('enable_realtime_response', models.BooleanField(default=False)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'SMS Configuration',
            },
        ),
        # Add database indexes
        migrations.AddIndex(
            model_name='smstemplate',
            index=models.Index(fields=['template_name', 'deleted_at'], name='SMS_smstem_templa_idx'),
        ),
        migrations.AddIndex(
            model_name='smstemplate',
            index=models.Index(fields=['approval_status', 'deleted_at'], name='SMS_smstem_approv_idx'),
        ),
        migrations.AddIndex(
            model_name='smstemplate',
            index=models.Index(fields=['sms_type', 'deleted_at'], name='SMS_smstem_sms_ty_idx'),
        ),
        migrations.AddIndex(
            model_name='smsmessage',
            index=models.Index(fields=['recipient_number', 'status', 'deleted_at'], name='SMS_smsmess_recipi_idx'),
        ),
        migrations.AddIndex(
            model_name='smsmessage',
            index=models.Index(fields=['template', 'status', 'deleted_at'], name='SMS_smsmess_templ_status_idx'),
        ),
        migrations.AddIndex(
            model_name='smsmessage',
            index=models.Index(fields=['created_at', 'deleted_at'], name='SMS_smsmess_create_idx'),
        ),
        migrations.AddIndex(
            model_name='smswebhooklog',
            index=models.Index(fields=['event_type', 'is_processed', 'deleted_at'], name='SMS_smswebb_event_idx'),
        ),
    ]
