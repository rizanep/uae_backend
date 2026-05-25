import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(TimestampedModel):
    deleted_at = models.DateTimeField(blank=True, null=True, db_index=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        if not self.deleted_at:
            self.deleted_at = timezone.now()
            self.save(update_fields=['deleted_at'])

    def restore(self):
        if self.deleted_at:
            self.deleted_at = None
            self.save(update_fields=['deleted_at'])


class SMSTemplate(SoftDeleteModel):
    """Store SMS message templates"""
    
    SMS_TYPE_CHOICES = [
        ('NORMAL', 'Normal'),
        ('TRANSACTIONAL', 'Transactional'),
        ('OTP', 'OTP'),
        ('PROMOTIONAL', 'Promotional'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template_name = models.CharField(max_length=256, unique=True, db_index=True)
    template_content = models.TextField(help_text="Use {{VAR1}}, {{VAR2}} for variables")
    sender_id = models.CharField(max_length=11, help_text="Sender ID (max 11 chars)")
    sms_type = models.CharField(max_length=20, choices=SMS_TYPE_CHOICES, default='NORMAL')
    
    # DLT (Distributed Ledger Technology) - Required in India
    dlt_template_id = models.CharField(max_length=255, blank=True, null=True, help_text="DLT Template ID for Indian SMS")
    
    # Message properties
    character_count = models.IntegerField(default=0, help_text="Character count of template")
    sms_parts = models.IntegerField(default=1, help_text="Number of SMS parts needed")
    
    # Status tracking
    is_approved = models.BooleanField(default=False)
    approval_status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('APPROVED', 'Approved'),
            ('REJECTED', 'Rejected'),
            ('DISABLED', 'Disabled'),
        ],
        default='PENDING',
        db_index=True
    )
    rejection_reason = models.TextField(blank=True, null=True)
    
    # Metadata
    msg91_template_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='sms_templates_created')
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['template_name', 'deleted_at']),
            models.Index(fields=['approval_status', 'deleted_at']),
            models.Index(fields=['sms_type', 'deleted_at']),
        ]

    def __str__(self):
        return f"{self.template_name} ({self.approval_status})"

    def save(self, *args, **kwargs):
        """Calculate SMS parts based on character count"""
        self.character_count = len(self.template_content)
        self.sms_parts = max(1, (self.character_count - 1) // 160 + 1)
        super().save(*args, **kwargs)


class SMSMessage(SoftDeleteModel):
    """Log all sent SMS messages"""
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SENT', 'Sent'),
        ('DELIVERED', 'Delivered'),
        ('FAILED', 'Failed'),
        ('BOUNCED', 'Bounced'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(SMSTemplate, on_delete=models.PROTECT, related_name='messages')
    recipient_number = models.CharField(max_length=20, db_index=True)
    
    # Message variables for template substitution
    variables = models.JSONField(default=dict, blank=True)
    
    # Rendered message content
    message_content = models.TextField()
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    msg91_message_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    
    # Response tracking
    response_data = models.JSONField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    
    # Timestamps
    sent_at = models.DateTimeField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)
    
    # Metadata
    sent_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='sms_messages_sent')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient_number', 'status', 'deleted_at']),
            models.Index(fields=['template', 'status', 'deleted_at']),
            models.Index(fields=['created_at', 'deleted_at']),
        ]

    def __str__(self):
        return f"SMS to {self.recipient_number} - {self.status}"


class SMSWebhookLog(SoftDeleteModel):
    """Log webhook events from MSG91"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=50)  # e.g., 'delivery_report', 'bounce'
    message = models.ForeignKey(SMSMessage, on_delete=models.SET_NULL, null=True, blank=True, related_name='webhook_logs')
    
    payload = models.JSONField()
    
    is_processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event_type', 'is_processed', 'deleted_at']),
        ]

    def __str__(self):
        return f"{self.event_type} - {self.created_at}"


class SMSConfiguration(models.Model):
    """Store SMS global configuration"""
    
    id = models.AutoField(primary_key=True)
    sender_id = models.CharField(max_length=11, help_text="Default sender ID")
    is_active = models.BooleanField(default=True)
    
    # Rate limiting
    daily_limit = models.IntegerField(default=10000, help_text="Daily message limit")
    monthly_limit = models.IntegerField(default=300000, help_text="Monthly message limit")
    
    # Cost tracking
    cost_per_sms = models.DecimalField(max_digits=10, decimal_places=4, default=0.50)
    
    # Features
    enable_short_url = models.BooleanField(default=False)
    short_url_expiry = models.IntegerField(default=3600, help_text="Seconds")
    enable_realtime_response = models.BooleanField(default=False)
    
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        verbose_name_plural = "SMS Configuration"

    def __str__(self):
        return f"SMS Config: {self.sender_id}"
