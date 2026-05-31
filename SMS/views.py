import logging
from datetime import datetime
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import SMSTemplate, SMSMessage, SMSConfiguration, SMSWebhookLog
from .serializers import (
    SMSTemplateSerializer,
    SMSMessageSerializer,
    BulkSMSMessageSerializer,
    SMSConfigurationSerializer
)
from .permissions import IsAdminOrReadOnly
from .services import MSG91SMSService

logger = logging.getLogger(__name__)


class SMSTemplateViewSet(viewsets.ModelViewSet):
    """
    Admin-only endpoints for managing SMS templates
    
    Endpoints:
    - GET /api/sms/templates/ - List all templates
    - POST /api/sms/templates/ - Create new template
    - GET /api/sms/templates/{id}/ - Retrieve template
    - PUT /api/sms/templates/{id}/ - Update template
    - DELETE /api/sms/templates/{id}/ - Delete template (soft delete)
    - POST /api/sms/templates/{id}/approve/ - Approve template
    - POST /api/sms/templates/{id}/reject/ - Reject template
    - POST /api/sms/templates/{id}/create-in-msg91/ - Create in MSG91
    """
    
    queryset = SMSTemplate.objects.filter(deleted_at__isnull=True)
    serializer_class = SMSTemplateSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['approval_status', 'sms_type']
    search_fields = ['template_name', 'template_content', 'sender_id']
    ordering_fields = ['created_at', 'updated_at', 'template_name']
    ordering = ['-created_at']
    
    def perform_create(self, serializer):
        """Set created_by to current user"""
        serializer.save(created_by=self.request.user)
    
    def perform_destroy(self, instance):
        """Soft delete template"""
        instance.soft_delete()
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrReadOnly])
    def approve(self, request, pk=None):
        """Approve template"""
        template = self.get_object()
        template.is_approved = True
        template.approval_status = 'APPROVED'
        template.rejection_reason = None
        template.save()
        
        logger.info(f"SMS Template {template.id} approved by {request.user}")
        
        return Response({
            'success': True,
            'message': 'Template approved successfully',
            'template': SMSTemplateSerializer(template).data
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrReadOnly])
    def reject(self, request, pk=None):
        """Reject template"""
        template = self.get_object()
        reason = request.data.get('reason', 'No reason provided')
        
        template.is_approved = False
        template.approval_status = 'REJECTED'
        template.rejection_reason = reason
        template.save()
        
        logger.info(f"SMS Template {template.id} rejected by {request.user}: {reason}")
        
        return Response({
            'success': True,
            'message': 'Template rejected successfully',
            'template': SMSTemplateSerializer(template).data
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrReadOnly])
    def create_in_msg91(self, request, pk=None):
        """Create template in MSG91"""
        template = self.get_object()
        
        try:
            service = MSG91SMSService()
            
            success, response = service.create_template(
                template_name=template.template_name,
                template_content=template.template_content,
                sender_id=template.sender_id,
                sms_type=template.sms_type,
                dlt_template_id=template.dlt_template_id
            )
            
            if success:
                # Extract template ID from response
                template_id = response.get('data', {}).get('template_id')
                template.msg91_template_id = template_id
                template.save()
                
                logger.info(f"SMS Template {template.id} created in MSG91: {template_id}")
                
                return Response({
                    'success': True,
                    'message': 'Template created in MSG91 successfully',
                    'template_id': template_id,
                    'response': response
                }, status=status.HTTP_200_OK)
            else:
                error_msg = response.get('message', 'Unknown error from MSG91')
                logger.warning(f"Template creation failed: {error_msg}")
                
                return Response({
                    'success': False,
                    'message': f'Failed to create template: {error_msg}',
                    'response': response
                }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(f"Error creating template in MSG91: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SMSMessageViewSet(viewsets.ModelViewSet):
    """
    Admin-only endpoints for sending and managing SMS
    
    Endpoints:
    - GET /api/sms/messages/ - List messages
    - POST /api/sms/messages/send/ - Send single message
    - POST /api/sms/messages/send-bulk/ - Send bulk messages
    - GET /api/sms/messages/{id}/ - Retrieve message
    """
    
    queryset = SMSMessage.objects.filter(deleted_at__isnull=True)
    serializer_class = SMSMessageSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'template']
    search_fields = ['recipient_number', 'msg91_message_id']
    ordering_fields = ['created_at', 'sent_at']
    ordering = ['-created_at']
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrReadOnly])
    @transaction.atomic
    def send(self, request):
        """
        Send single SMS
        
        Request body:
        {
            "template_id": "uuid",
            "recipient_number": "+971501234567",
            "variables": {"VAR1": "value1", "VAR2": "value2"},
            "short_url": false,
            "realtime_response": false
        }
        """
        template_id = request.data.get('template')
        recipient_number = request.data.get('recipient_number')
        variables = request.data.get('variables', {})
        short_url = request.data.get('short_url', False)
        realtime_response = request.data.get('realtime_response', False)
        
        try:
            # Verify template exists and is approved
            template = get_object_or_404(
                SMSTemplate,
                id=template_id,
                is_approved=True,
                deleted_at__isnull=True
            )
            
            # Render message content
            service = MSG91SMSService()
            message_content = service.render_message(template.template_content, variables)
            
            # Create message record
            message = SMSMessage.objects.create(
                template=template,
                recipient_number=recipient_number,
                variables=variables,
                message_content=message_content,
                sent_by=request.user,
                status='PENDING'
            )
            
            # Send via MSG91
            success, response = service.send_message(
                template_id=template.msg91_template_id or template_id,
                recipient_number=recipient_number,
                variables=variables,
                short_url=short_url,
                realtime_response=realtime_response
            )
            
            if success:
                msg_id = response.get('message_id') or response.get('data', {}).get('message_id')
                message.msg91_message_id = msg_id
                message.status = 'SENT'
                message.response_data = response
                message.sent_at = datetime.now()
                message.save()
                
                logger.info(f"SMS {message.id} sent to {recipient_number}")
                
                return Response({
                    'success': True,
                    'message': 'SMS sent successfully',
                    'data': SMSMessageSerializer(message).data
                }, status=status.HTTP_201_CREATED)
            else:
                error_msg = response.get('message', 'Unknown error')
                message.status = 'FAILED'
                message.error_message = error_msg
                message.response_data = response
                message.save()
                
                logger.warning(f"SMS {message.id} failed: {error_msg}")
                
                return Response({
                    'success': False,
                    'message': f'Failed to send SMS: {error_msg}',
                    'data': SMSMessageSerializer(message).data
                }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(f"Error sending SMS: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrReadOnly])
    @transaction.atomic
    def send_bulk(self, request):
        """
        Send bulk SMS
        
        Request body:
        {
            "template_id": "uuid",
            "recipient_numbers": ["+971501234567", "+971502345678"],
            "variables_list": [
                {"VAR1": "value1_1", "VAR2": "value1_2"},
                {"VAR1": "value2_1", "VAR2": "value2_2"}
            ],
            "short_url": false
        }
        """
        serializer = BulkSMSMessageSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        template_id = serializer.validated_data['template_id']
        recipient_numbers = serializer.validated_data['recipient_numbers']
        variables_list = serializer.validated_data.get('variables_list', [])
        short_url = request.data.get('short_url', False)
        
        try:
            # Verify template exists and is approved
            template = get_object_or_404(
                SMSTemplate,
                id=template_id,
                is_approved=True,
                deleted_at__isnull=True
            )
            
            # Create message records
            service = MSG91SMSService()
            messages = []
            
            for idx, recipient in enumerate(recipient_numbers):
                variables = variables_list[idx] if idx < len(variables_list) else {}
                message_content = service.render_message(template.template_content, variables)
                
                message = SMSMessage(
                    template=template,
                    recipient_number=recipient,
                    variables=variables,
                    message_content=message_content,
                    sent_by=request.user,
                    status='PENDING'
                )
                messages.append(message)
            
            SMSMessage.objects.bulk_create(messages)
            
            # Send via MSG91
            success, response = service.send_bulk_messages(
                template_id=template.msg91_template_id or template_id,
                recipient_numbers=recipient_numbers,
                variables_list=variables_list if variables_list else None,
                short_url=short_url
            )
            
            if success:
                # Update message statuses
                msg_ids = response.get('message_ids', [])
                for idx, message in enumerate(messages):
                    if idx < len(msg_ids):
                        message.msg91_message_id = msg_ids[idx]
                    message.status = 'SENT'
                    message.response_data = response
                    message.sent_at = datetime.now()
                
                SMSMessage.objects.bulk_update(
                    messages,
                    ['msg91_message_id', 'status', 'response_data', 'sent_at']
                )
                
                logger.info(f"Bulk SMS sent: {len(messages)} messages")
                
                return Response({
                    'success': True,
                    'message': f'Bulk SMS sent successfully ({len(messages)} messages)',
                    'sent_count': len(messages),
                    'response': response
                }, status=status.HTTP_201_CREATED)
            else:
                error_msg = response.get('message', 'Unknown error')
                logger.warning(f"Bulk send failed: {error_msg}")
                
                return Response({
                    'success': False,
                    'message': f'Failed to send bulk SMS: {error_msg}',
                    'sent_count': 0,
                    'response': response
                }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(f"Error sending bulk SMS: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SMSConfigurationViewSet(viewsets.ViewSet):
    """
    Admin-only endpoints for SMS configuration
    
    Endpoints:
    - GET /api/sms/config/ - Get configuration
    - PUT /api/sms/config/ - Update configuration
    """
    
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    
    def retrieve(self, request):
        """Get SMS configuration"""
        try:
            config, created = SMSConfiguration.objects.get_or_create(id=1)
            serializer = SMSConfigurationSerializer(config)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error retrieving SMS configuration: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def update(self, request):
        """Update SMS configuration"""
        try:
            config, created = SMSConfiguration.objects.get_or_create(id=1)
            
            serializer = SMSConfigurationSerializer(config, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save(updated_by=request.user)
                logger.info(f"SMS Configuration updated by {request.user}")
                return Response(serializer.data, status=status.HTTP_200_OK)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(f"Error updating SMS configuration: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SMSReportViewSet(viewsets.ViewSet):
    """
    Admin-only endpoints for SMS reports and logs
    
    Endpoints:
    - GET /api/sms/reports/logs/ - Get SMS delivery logs
    """
    
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdminOrReadOnly])
    def logs(self, request):
        """
        Get SMS delivery logs from MSG91
        
        Query Parameters:
        - start_date: YYYY-MM-DD
        - end_date: YYYY-MM-DD
        """
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not start_date or not end_date:
            return Response({
                'error': 'start_date and end_date required (YYYY-MM-DD format)'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            service = MSG91SMSService()
            success, response = service.get_sms_logs(start_date, end_date)
            
            if success:
                return Response({
                    'success': True,
                    'data': response.get('data', []),
                    'count': len(response.get('data', []))
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': 'Failed to fetch logs',
                    'response': response
                }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(f"Error fetching SMS logs: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
