import logging
from datetime import datetime
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError, PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import WhatsAppTemplate, WhatsAppMessage, WhatsAppConfiguration, WhatsAppWebhookLog
from .serializers import (
    WhatsAppTemplateSerializer,
    WhatsAppMessageSerializer,
    BulkWhatsAppMessageSerializer,
    WhatsAppConfigurationSerializer
)
from .permissions import IsAdminOrReadOnly, IsWhatsAppAdmin
from .services import MSG91WhatsAppService

logger = logging.getLogger(__name__)


class WhatsAppTemplateViewSet(viewsets.ModelViewSet):
    """
    Admin-only endpoints for managing WhatsApp templates
    
    Endpoints:
    - GET /api/whatsapp/templates/ - List all templates
    - POST /api/whatsapp/templates/ - Create new template
    - GET /api/whatsapp/templates/{id}/ - Retrieve template
    - PUT /api/whatsapp/templates/{id}/ - Update template
    - DELETE /api/whatsapp/templates/{id}/ - Delete template (soft delete)
    - POST /api/whatsapp/templates/{id}/sync-with-msg91/ - Sync with MSG91
    - POST /api/whatsapp/templates/{id}/approve/ - Approve template
    - POST /api/whatsapp/templates/{id}/reject/ - Reject template
    """
    
    queryset = WhatsAppTemplate.objects.filter(deleted_at__isnull=True)
    serializer_class = WhatsAppTemplateSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['approval_status', 'language', 'category']
    search_fields = ['template_name', 'body_text']
    ordering_fields = ['created_at', 'updated_at', 'template_name']
    ordering = ['-created_at']
    
    def perform_create(self, serializer):
        """Set created_by to current user"""
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        """Update template"""
        serializer.save()
    
    def perform_destroy(self, instance):
        """Soft delete template"""
        instance.soft_delete()
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrReadOnly])
    def sync_with_msg91(self, request, pk=None):
        """
        Create or sync template with MSG91
        """
        template = self.get_object()
        
        try:
            service = MSG91WhatsAppService()
            
            success, response = service.create_template(
                template_name=template.template_name,
                category=template.category,
                language_code=template.language,
                header_format=template.header_format,
                header_text=template.header_text,
                body_text=template.body_text,
                footer_text=template.footer_text,
                buttons=template.buttons or []
            )
            
            if success:
                # Extract template ID from response
                template_id = response.get('data', {}).get('template_id')
                template.msg91_template_id = template_id
                template.approval_status = 'PENDING'
                template.save()
                
                logger.info(f"Template {template.id} synced with MSG91: {template_id}")
                
                return Response({
                    'success': True,
                    'message': 'Template synced with MSG91 successfully',
                    'template_id': template_id,
                    'response': response
                }, status=status.HTTP_200_OK)
            else:
                error_msg = response.get('message', 'Unknown error from MSG91')
                logger.warning(f"Template sync failed: {error_msg}")
                
                return Response({
                    'success': False,
                    'message': f'Failed to sync template: {error_msg}',
                    'response': response
                }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(f"Error syncing template: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error syncing template: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrReadOnly])
    def approve(self, request, pk=None):
        """
        Manually approve template
        """
        template = self.get_object()
        template.is_approved = True
        template.approval_status = 'APPROVED'
        template.rejection_reason = None
        template.save()
        
        logger.info(f"Template {template.id} approved by {request.user}")
        
        return Response({
            'success': True,
            'message': 'Template approved successfully',
            'template': WhatsAppTemplateSerializer(template).data
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrReadOnly])
    def reject(self, request, pk=None):
        """
        Reject template with reason
        """
        template = self.get_object()
        reason = request.data.get('reason', 'No reason provided')
        
        template.is_approved = False
        template.approval_status = 'REJECTED'
        template.rejection_reason = reason
        template.save()
        
        logger.info(f"Template {template.id} rejected by {request.user}: {reason}")
        
        return Response({
            'success': True,
            'message': 'Template rejected successfully',
            'template': WhatsAppTemplateSerializer(template).data
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdminOrReadOnly])
    def sync_all_from_msg91(self, request):
        """
        Fetch all templates from MSG91 and sync locally
        """
        try:
            service = MSG91WhatsAppService()
            success, response = service.get_templates()
            
            if success:
                templates = response.get('data', [])
                logger.info(f"Fetched {len(templates)} templates from MSG91")
                
                return Response({
                    'success': True,
                    'message': f'Found {len(templates)} templates in MSG91',
                    'templates': templates
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': 'Failed to fetch templates from MSG91',
                    'response': response
                }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(f"Error fetching templates from MSG91: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WhatsAppMessageViewSet(viewsets.ModelViewSet):
    """
    Admin-only endpoints for sending and managing WhatsApp messages
    
    Endpoints:
    - GET /api/whatsapp/messages/ - List messages
    - POST /api/whatsapp/messages/send/ - Send single message
    - POST /api/whatsapp/messages/send-bulk/ - Send bulk messages
    - GET /api/whatsapp/messages/{id}/ - Retrieve message
    """
    
    queryset = WhatsAppMessage.objects.filter(deleted_at__isnull=True)
    serializer_class = WhatsAppMessageSerializer
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
        Send single WhatsApp message
        
        Request body:
        {
            "template_id": "uuid",
            "recipient_number": "+971501234567",
            "variables": {"body_1": "value1", "body_2": "value2"}
        }
        """
        serializer = WhatsAppMessageSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        template_id = request.data.get('template')
        recipient_number = request.data.get('recipient_number')
        variables = request.data.get('variables', {})
        
        try:
            # Verify template exists and is approved
            template = get_object_or_404(
                WhatsAppTemplate,
                id=template_id,
                is_approved=True,
                deleted_at__isnull=True
            )
            
            # Create message record
            message = WhatsAppMessage.objects.create(
                template=template,
                recipient_number=recipient_number,
                variables=variables,
                sent_by=request.user,
                status='PENDING'
            )
            
            # Send via MSG91
            service = MSG91WhatsAppService()
            success, response = service.send_message(
                template_name=template.template_name,
                recipient_number=recipient_number,
                variables=variables
            )
            
            if success:
                msg_id = response.get('message_id') or response.get('data', {}).get('message_id')
                message.msg91_message_id = msg_id
                message.status = 'SENT'
                message.response_data = response
                message.sent_at = datetime.now()
                message.save()
                
                logger.info(f"Message {message.id} sent to {recipient_number}")
                
                return Response({
                    'success': True,
                    'message': 'Message sent successfully',
                    'data': WhatsAppMessageSerializer(message).data
                }, status=status.HTTP_201_CREATED)
            else:
                error_msg = response.get('message', 'Unknown error')
                message.status = 'FAILED'
                message.error_message = error_msg
                message.response_data = response
                message.save()
                
                logger.warning(f"Message {message.id} failed: {error_msg}")
                
                return Response({
                    'success': False,
                    'message': f'Failed to send message: {error_msg}',
                    'data': WhatsAppMessageSerializer(message).data
                }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrReadOnly])
    @transaction.atomic
    def send_bulk(self, request):
        """
        Send bulk WhatsApp messages
        
        Request body:
        {
            "template_id": "uuid",
            "recipient_numbers": ["+971501234567", "+971502345678"],
            "variables_list": [
                {"body_1": "value1_1", "body_2": "value1_2"},
                {"body_1": "value2_1", "body_2": "value2_2"}
            ]
        }
        """
        serializer = BulkWhatsAppMessageSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        template_id = serializer.validated_data['template_id']
        recipient_numbers = serializer.validated_data['recipient_numbers']
        variables_list = serializer.validated_data.get('variables_list', [])
        
        try:
            # Verify template exists and is approved
            template = get_object_or_404(
                WhatsAppTemplate,
                id=template_id,
                is_approved=True,
                deleted_at__isnull=True
            )
            
            # Create message records
            messages = []
            for idx, recipient in enumerate(recipient_numbers):
                variables = variables_list[idx] if idx < len(variables_list) else {}
                message = WhatsAppMessage(
                    template=template,
                    recipient_number=recipient,
                    variables=variables,
                    sent_by=request.user,
                    status='PENDING'
                )
                messages.append(message)
            
            WhatsAppMessage.objects.bulk_create(messages)
            
            # Send via MSG91
            service = MSG91WhatsAppService()
            success, response = service.send_bulk_messages(
                template_name=template.template_name,
                recipient_numbers=recipient_numbers,
                variables_list=variables_list if variables_list else None
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
                
                WhatsAppMessage.objects.bulk_update(
                    messages,
                    ['msg91_message_id', 'status', 'response_data', 'sent_at']
                )
                
                logger.info(f"Bulk messages sent: {len(messages)} messages")
                
                return Response({
                    'success': True,
                    'message': f'Bulk messages sent successfully ({len(messages)} messages)',
                    'sent_count': len(messages),
                    'response': response
                }, status=status.HTTP_201_CREATED)
            else:
                error_msg = response.get('message', 'Unknown error')
                logger.warning(f"Bulk send failed: {error_msg}")
                
                return Response({
                    'success': False,
                    'message': f'Failed to send bulk messages: {error_msg}',
                    'sent_count': 0,
                    'response': response
                }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(f"Error sending bulk messages: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WhatsAppConfigurationViewSet(viewsets.ViewSet):
    """
    Admin-only endpoints for WhatsApp configuration
    
    Endpoints:
    - GET /api/whatsapp/config/ - Get configuration
    - PUT /api/whatsapp/config/{number}/ - Update configuration
    """
    
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    
    def retrieve(self, request):
        """Get WhatsApp configuration"""
        try:
            from django.conf import settings
            config = WhatsAppConfiguration.objects.get(
                integrated_number=settings.MSG91_INTEGRATED_NUMBER
            )
            serializer = WhatsAppConfigurationSerializer(config)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except WhatsAppConfiguration.DoesNotExist:
            return Response({
                'error': 'Configuration not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error retrieving configuration: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def update(self, request):
        """Update WhatsApp configuration"""
        try:
            from django.conf import settings
            config, created = WhatsAppConfiguration.objects.get_or_create(
                integrated_number=settings.MSG91_INTEGRATED_NUMBER
            )
            
            serializer = WhatsAppConfigurationSerializer(config, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save(updated_by=request.user)
                logger.info(f"Configuration updated by {request.user}")
                return Response(serializer.data, status=status.HTTP_200_OK)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(f"Error updating configuration: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
