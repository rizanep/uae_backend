from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import SMSTemplate, SMSMessage, SMSConfiguration
import re


class SMSTemplateSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = SMSTemplate
        fields = [
            'id', 'template_name', 'template_content', 'sender_id', 'sms_type',
            'dlt_template_id', 'character_count', 'sms_parts',
            'is_approved', 'approval_status', 'rejection_reason',
            'msg91_template_id', 'created_by_name', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'character_count', 'sms_parts', 'msg91_template_id', 'created_at', 'updated_at', 'created_by_name']

    def validate_template_name(self, value):
        """Validate template name"""
        if len(value) < 3:
            raise serializers.ValidationError(_("Template name must be at least 3 characters."))
        if len(value) > 256:
            raise serializers.ValidationError(_("Template name must be at most 256 characters."))
        if not re.match(r'^[a-zA-Z0-9_\-]+$', value):
            raise serializers.ValidationError(_("Template name can only contain letters, numbers, hyphens, and underscores."))
        return value

    def validate_template_content(self, value):
        """Validate template content"""
        if len(value) < 10:
            raise serializers.ValidationError(_("Template content must be at least 10 characters."))
        if len(value) > 9999:
            raise serializers.ValidationError(_("Template content exceeds SMS limits (9999 chars)."))
        return value

    def validate_sender_id(self, value):
        """Validate sender ID format"""
        if len(value) > 11:
            raise serializers.ValidationError(_("Sender ID must be max 11 characters."))
        if not re.match(r'^[a-zA-Z0-9]+$', value):
            raise serializers.ValidationError(_("Sender ID can only contain alphanumeric characters."))
        return value

    def validate_dlt_template_id(self, value):
        """Validate DLT template ID (optional)"""
        if value and len(value) > 255:
            raise serializers.ValidationError(_("DLT Template ID too long."))
        return value


class SMSMessageSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.template_name', read_only=True)
    sent_by_name = serializers.CharField(source='sent_by.get_full_name', read_only=True)
    sms_parts = serializers.IntegerField(source='template.sms_parts', read_only=True)
    
    class Meta:
        model = SMSMessage
        fields = [
            'id', 'template', 'template_name', 'recipient_number',
            'variables', 'message_content', 'sms_parts',
            'status', 'msg91_message_id',
            'sent_at', 'delivered_at',
            'sent_by_name', 'error_message', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'msg91_message_id', 'message_content', 'sms_parts', 'sent_at', 'delivered_at', 'sent_by_name', 'created_at', 'updated_at']

    def validate_recipient_number(self, value):
        """Validate recipient phone number"""
        # Remove any non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', value)
        
        if not cleaned or len(cleaned) < 10:
            raise serializers.ValidationError(_("Phone number too short."))
        if len(cleaned) > 20:
            raise serializers.ValidationError(_("Phone number too long."))
        
        return cleaned

    def validate_variables(self, value):
        """Validate variables dictionary"""
        if not isinstance(value, dict):
            raise serializers.ValidationError(_("Variables must be a dictionary."))
        
        for key, val in value.items():
            if not re.match(r'^VAR\d+$', key, re.IGNORECASE):
                raise serializers.ValidationError(_("Variable keys must be VAR1, VAR2, etc."))
        
        return value


class BulkSMSMessageSerializer(serializers.Serializer):
    """Serializer for bulk SMS sending"""
    template_id = serializers.UUIDField()
    recipient_numbers = serializers.ListField(
        child=serializers.CharField(max_length=20),
        min_length=1,
        max_length=10000
    )
    variables_list = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text="Optional list of variable dicts for each recipient"
    )
    short_url = serializers.BooleanField(required=False, default=False)
    realtime_response = serializers.BooleanField(required=False, default=False)

    def validate_recipient_numbers(self, value):
        """Validate all phone numbers"""
        for number in value:
            cleaned = re.sub(r'[^\d+]', '', number)
            if len(cleaned) < 10:
                raise serializers.ValidationError(
                    _("Invalid phone number: {}").format(number)
                )
        return value

    def validate(self, data):
        """Validate bulk message data"""
        recipient_numbers = data.get('recipient_numbers', [])
        variables_list = data.get('variables_list', [])
        
        # If variables provided, must match count
        if variables_list and len(variables_list) != len(recipient_numbers):
            raise serializers.ValidationError(
                _("Variables list must match recipient numbers count.")
            )
        
        return data


class SMSConfigurationSerializer(serializers.ModelSerializer):
    updated_by_name = serializers.CharField(source='updated_by.get_full_name', read_only=True)
    
    class Meta:
        model = SMSConfiguration
        fields = [
            'id', 'sender_id', 'is_active', 'daily_limit', 'monthly_limit',
            'cost_per_sms', 'enable_short_url', 'short_url_expiry',
            'enable_realtime_response', 'updated_at', 'updated_by_name'
        ]
        read_only_fields = ['updated_at', 'updated_by_name']

    def validate_sender_id(self, value):
        if len(value) > 11:
            raise serializers.ValidationError(_("Sender ID must be max 11 characters."))
        if not re.match(r'^[a-zA-Z0-9]+$', value):
            raise serializers.ValidationError(_("Sender ID can only contain alphanumeric characters."))
        return value

    def validate_daily_limit(self, value):
        if value < 0:
            raise serializers.ValidationError(_("Daily limit cannot be negative."))
        if value > 1000000:
            raise serializers.ValidationError(_("Daily limit too high."))
        return value

    def validate_monthly_limit(self, value):
        if value < 0:
            raise serializers.ValidationError(_("Monthly limit cannot be negative."))
        if value > 10000000:
            raise serializers.ValidationError(_("Monthly limit too high."))
        return value

    def validate_cost_per_sms(self, value):
        if value < 0:
            raise serializers.ValidationError(_("Cost cannot be negative."))
        if value > 100:
            raise serializers.ValidationError(_("Cost too high."))
        return value
