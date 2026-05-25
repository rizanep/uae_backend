from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import SMSTemplate, SMSMessage, SMSConfiguration, SMSWebhookLog


@admin.register(SMSTemplate)
class SMSTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'template_name', 'sender_id', 'sms_type',
        'approval_status_badge', 'character_count', 'sms_parts',
        'created_by_name', 'created_at'
    ]
    list_filter = ['approval_status', 'sms_type', 'created_at']
    search_fields = ['template_name', 'template_content', 'sender_id']
    readonly_fields = ['id', 'created_at', 'updated_at', 'character_count', 'sms_parts', 'msg91_template_id']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'template_name', 'sender_id', 'sms_type')
        }),
        ('Template Content', {
            'fields': ('template_content', 'character_count', 'sms_parts'),
            'description': 'Use {{VAR1}}, {{VAR2}}, etc. for variables'
        }),
        ('DLT Configuration', {
            'fields': ('dlt_template_id',),
            'classes': ('collapse',)
        }),
        ('Approval Status', {
            'fields': ('is_approved', 'approval_status', 'rejection_reason'),
        }),
        ('Metadata', {
            'fields': ('msg91_template_id', 'created_by', 'notes', 'created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_templates', 'reject_templates']
    
    def approval_status_badge(self, obj):
        """Display approval status as colored badge"""
        colors = {
            'PENDING': '#FFC107',
            'APPROVED': '#28A745',
            'REJECTED': '#DC3545',
            'DISABLED': '#6C757D',
        }
        color = colors.get(obj.approval_status, '#000000')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.approval_status
        )
    approval_status_badge.short_description = 'Status'
    
    def created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else 'N/A'
    created_by_name.short_description = 'Created By'
    
    def approve_templates(self, request, queryset):
        """Bulk approve templates"""
        updated = queryset.update(is_approved=True, approval_status='APPROVED', rejection_reason=None)
        self.message_user(request, f'{updated} templates approved.')
    approve_templates.short_description = 'Approve selected templates'
    
    def reject_templates(self, request, queryset):
        """Bulk reject templates"""
        updated = queryset.update(is_approved=False, approval_status='REJECTED')
        self.message_user(request, f'{updated} templates rejected.')
    reject_templates.short_description = 'Reject selected templates'
    
    def get_queryset(self, request):
        """Only show non-deleted templates"""
        return super().get_queryset(request).filter(deleted_at__isnull=True)


@admin.register(SMSMessage)
class SMSMessageAdmin(admin.ModelAdmin):
    list_display = [
        'recipient_number', 'template_link', 'sms_type',
        'status_badge', 'sent_at', 'sent_by_name', 'created_at'
    ]
    list_filter = ['status', 'created_at', 'sent_at', 'template__sms_type']
    search_fields = ['recipient_number', 'msg91_message_id', 'template__template_name']
    readonly_fields = ['id', 'msg91_message_id', 'message_content', 'created_at', 'updated_at', 'response_data']
    
    fieldsets = (
        ('Message Information', {
            'fields': ('id', 'template', 'recipient_number', 'msg91_message_id')
        }),
        ('Message Content', {
            'fields': ('message_content', 'variables'),
        }),
        ('Status', {
            'fields': ('status', 'error_message'),
        }),
        ('Timestamps', {
            'fields': ('sent_at', 'delivered_at'),
        }),
        ('Response Data', {
            'fields': ('response_data',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('sent_by', 'created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_delivered']
    
    def status_badge(self, obj):
        """Display status as colored badge"""
        colors = {
            'PENDING': '#FFC107',
            'SENT': '#17A2B8',
            'DELIVERED': '#28A745',
            'FAILED': '#DC3545',
            'BOUNCED': '#FD7E14',
        }
        color = colors.get(obj.status, '#000000')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.status
        )
    status_badge.short_description = 'Status'
    
    def template_link(self, obj):
        """Display template as link"""
        url = reverse('admin:SMS_smstemplate_change', args=[obj.template.id])
        return format_html('<a href="{}">{}</a>', url, obj.template.template_name)
    template_link.short_description = 'Template'
    
    def sms_type(self, obj):
        """Display SMS type"""
        return obj.template.sms_type
    sms_type.short_description = 'Type'
    
    def sent_by_name(self, obj):
        return obj.sent_by.get_full_name() if obj.sent_by else 'N/A'
    sent_by_name.short_description = 'Sent By'
    
    def mark_as_delivered(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status='SENT').update(status='DELIVERED', delivered_at=timezone.now())
        self.message_user(request, f'{updated} messages marked as delivered.')
    mark_as_delivered.short_description = 'Mark selected as delivered'
    
    def get_queryset(self, request):
        """Only show non-deleted messages"""
        return super().get_queryset(request).filter(deleted_at__isnull=True)


@admin.register(SMSConfiguration)
class SMSConfigurationAdmin(admin.ModelAdmin):
    list_display = ['sender_id', 'is_active', 'daily_limit', 'monthly_limit', 'cost_per_sms', 'updated_at']
    list_filter = ['is_active', 'updated_at']
    readonly_fields = ['updated_at']
    
    fieldsets = (
        ('Configuration', {
            'fields': ('sender_id', 'is_active')
        }),
        ('Rate Limiting', {
            'fields': ('daily_limit', 'monthly_limit'),
        }),
        ('Cost Tracking', {
            'fields': ('cost_per_sms',),
        }),
        ('Features', {
            'fields': ('enable_short_url', 'short_url_expiry', 'enable_realtime_response'),
        }),
        ('Metadata', {
            'fields': ('updated_at', 'updated_by'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SMSWebhookLog)
class SMSWebhookLogAdmin(admin.ModelAdmin):
    list_display = ['event_type', 'message_link', 'is_processed', 'created_at']
    list_filter = ['event_type', 'is_processed', 'created_at']
    search_fields = ['message__msg91_message_id']
    readonly_fields = ['id', 'payload', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Event Information', {
            'fields': ('id', 'event_type', 'message')
        }),
        ('Payload', {
            'fields': ('payload',),
        }),
        ('Processing', {
            'fields': ('is_processed', 'processing_error'),
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )
    
    def message_link(self, obj):
        """Display message as link"""
        if obj.message:
            url = reverse('admin:SMS_smsmessage_change', args=[obj.message.id])
            return format_html('<a href="{}">{}</a>', url, obj.message.recipient_number)
        return 'N/A'
    message_link.short_description = 'Message'
    
    def get_queryset(self, request):
        """Only show non-deleted logs"""
        return super().get_queryset(request).filter(deleted_at__isnull=True)
