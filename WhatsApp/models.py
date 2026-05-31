import uuid
import json
from django.db import models
from django.conf import settings
from django.core.validators import URLValidator
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


class WhatsAppTemplate(SoftDeleteModel):
    """Store WhatsApp message templates"""
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('ar', 'Arabic'),
        ('hi', 'Hindi'),
        ('ur', 'Urdu'),
    ]
    
    CATEGORY_CHOICES = [
        ('MARKETING', 'Marketing'),
        ('AUTHENTICATION', 'Authentication'),
        ('TRANSACTIONAL', 'Transactional'),
        ('UTILITY', 'Utility'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template_name = models.CharField(max_length=512, unique=True, db_index=True)
    integrated_number = models.CharField(max_length=20)  # WhatsApp number
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='MARKETING')
    
    # Template components
    header_format = models.CharField(
        max_length=20, 
        choices=[('TEXT', 'Text'), ('IMAGE', 'Image'), ('VIDEO', 'Video'), ('DOCUMENT', 'Document'), ('LOCATION', 'Location')],
        blank=True,
        null=True
    )
    header_text = models.TextField(blank=True, null=True)
    header_example = models.JSONField(blank=True, null=True)
    
    body_text = models.TextField()
    body_example = models.JSONField(blank=True, null=True)
    
    footer_text = models.TextField(blank=True, null=True)
    
    buttons = models.JSONField(default=list, blank=True, null=True)
    
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
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='whatsapp_templates_created')
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['template_name', 'deleted_at']),
            models.Index(fields=['approval_status', 'deleted_at']),
            models.Index(fields=['integrated_number', 'deleted_at']),
        ]

    def __str__(self):
        return f"{self.template_name} ({self.approval_status})"


class WhatsAppMessage(SoftDeleteModel):
    """Log all WhatsApp messages sent"""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SENT', 'Sent'),
        ('DELIVERED', 'Delivered'),
        ('READ', 'Read'),
        ('FAILED', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(WhatsAppTemplate, on_delete=models.PROTECT, related_name='messages')
    recipient_number = models.CharField(max_length=20, db_index=True)
    
    # Message variables for template substitution
    variables = models.JSONField(default=dict, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    msg91_message_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    
    # Response tracking
    response_data = models.JSONField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    
    # Timestamps
    sent_at = models.DateTimeField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)
    read_at = models.DateTimeField(blank=True, null=True)
    
    # Metadata
    sent_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='whatsapp_messages_sent')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient_number', 'status', 'deleted_at']),
            models.Index(fields=['template', 'status', 'deleted_at']),
            models.Index(fields=['created_at', 'deleted_at']),
        ]

    def __str__(self):
        return f"Message to {self.recipient_number} - {self.status}"


class WhatsAppWebhookLog(SoftDeleteModel):
    """Log webhook events from MSG91"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=50)  # e.g., 'message_sent', 'delivery_report'
    message = models.ForeignKey(WhatsAppMessage, on_delete=models.SET_NULL, null=True, blank=True, related_name='webhook_logs')
    
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


class WhatsAppConfiguration(models.Model):
    """Store MSG91 configuration"""
    
    integrated_number = models.CharField(max_length=20, primary_key=True)
    is_active = models.BooleanField(default=True)
    daily_limit = models.IntegerField(default=10000, help_text="Daily message limit")
    monthly_limit = models.IntegerField(default=300000, help_text="Monthly message limit")
    
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        verbose_name_plural = "WhatsApp Configurations"

    def __str__(self):
        return f"WhatsApp Config: {self.integrated_number}"
