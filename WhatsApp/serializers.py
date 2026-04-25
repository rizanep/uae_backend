from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import WhatsAppTemplate, WhatsAppMessage, WhatsAppConfiguration


class WhatsAppTemplateSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = WhatsAppTemplate
        fields = [
            'id', 'template_name', 'integrated_number', 'language', 'category',
            'header_format', 'header_text', 'header_example',
            'body_text', 'body_example', 'footer_text', 'buttons',
            'is_approved', 'approval_status', 'rejection_reason',
            'msg91_template_id', 'created_by_name', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'msg91_template_id', 'created_at', 'updated_at', 'created_by_name']

    def validate_header_format(self, value):
        """Validate header format is appropriate"""
        if value and value not in ['TEXT', 'IMAGE', 'VIDEO', 'DOCUMENT', 'LOCATION']:
            raise serializers.ValidationError(_("Invalid header format."))
        return value

    def validate_buttons(self, value):
        """Validate buttons structure"""
        if not isinstance(value, list):
            raise serializers.ValidationError(_("Buttons must be a list."))
        
        for button in value:
            if 'type' not in button:
                raise serializers.ValidationError(_("Each button must have a type."))
            if button['type'] not in ['QUICK_REPLY', 'URL', 'CALL', 'COPY_CODE', 'CATALOG', 'MPM']:
                raise serializers.ValidationError(_("Invalid button type."))
        
        return value

    def validate_template_name(self, value):
        """Validate template name"""
        if len(value) < 3:
            raise serializers.ValidationError(_("Template name must be at least 3 characters."))
        if len(value) > 512:
            raise serializers.ValidationError(_("Template name must be at most 512 characters."))
        return value

    def validate_integrated_number(self, value):
        """Validate phone number format"""
        if not value.startswith('+') and not value.isdigit():
            raise serializers.ValidationError(_("Invalid phone number format."))
        if len(value) < 10:
            raise serializers.ValidationError(_("Phone number too short."))
        return value


class WhatsAppMessageSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.template_name', read_only=True)
    sent_by_name = serializers.CharField(source='sent_by.get_full_name', read_only=True)
    
    class Meta:
        model = WhatsAppMessage
        fields = [
            'id', 'template', 'template_name', 'recipient_number',
            'variables', 'status', 'msg91_message_id',
            'sent_at', 'delivered_at', 'read_at',
            'sent_by_name', 'error_message', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'msg91_message_id', 'sent_at', 'delivered_at', 'read_at', 'sent_by_name', 'created_at', 'updated_at']

    def validate_recipient_number(self, value):
        """Validate recipient phone number"""
        if not value.startswith('+') and not value.isdigit():
            raise serializers.ValidationError(_("Invalid phone number format."))
        if len(value) < 10:
            raise serializers.ValidationError(_("Phone number too short."))
        return value


class BulkWhatsAppMessageSerializer(serializers.Serializer):
    """Serializer for bulk message sending"""
    template_id = serializers.UUIDField()
    recipient_numbers = serializers.ListField(
        child=serializers.CharField(max_length=20),
        min_length=1,
        max_length=1000
    )
    variables_list = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text="Optional list of variable dicts for each recipient"
    )

    def validate(self, data):
        """Validate bulk message data"""
        recipient_numbers = data.get('recipient_numbers', [])
        variables_list = data.get('variables_list', [])
        
        # Validate phone numbers
        for number in recipient_numbers:
            if not number.startswith('+') and not number.isdigit():
                raise serializers.ValidationError(
                    _("Invalid phone number format: {}").format(number)
                )
        
        # If variables provided, must match count
        if variables_list and len(variables_list) != len(recipient_numbers):
            raise serializers.ValidationError(
                _("Variables list must match recipient numbers count.")
            )
        
        return data


class WhatsAppConfigurationSerializer(serializers.ModelSerializer):
    updated_by_name = serializers.CharField(source='updated_by.get_full_name', read_only=True)
    
    class Meta:
        model = WhatsAppConfiguration
        fields = ['integrated_number', 'is_active', 'daily_limit', 'monthly_limit', 'updated_at', 'updated_by_name']
        read_only_fields = ['updated_at', 'updated_by_name']

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
