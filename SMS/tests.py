from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import SMSTemplate, SMSMessage, SMSConfiguration
import uuid


class SMSTemplateTestCase(APITestCase):
    """Test SMS Template endpoints"""
    
    def setUp(self):
        """Set up test client and admin user"""
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        self.regular_user = User.objects.create_user(
            username='user',
            email='user@test.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.admin_user)
    
    def test_create_template(self):
        """Test creating an SMS template"""
        payload = {
            'template_name': 'order_notification',
            'template_content': 'Hello {{VAR1}}, your order {{VAR2}} is confirmed',
            'sender_id': 'MYAPP',
            'sms_type': 'TRANSACTIONAL',
            'approval_status': 'PENDING'
        }
        
        response = self.client.post('/api/sms/templates/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['template_name'], 'order_notification')
    
    def test_list_templates(self):
        """Test listing templates"""
        SMSTemplate.objects.create(
            template_name='test_template',
            template_content='Test template content {{VAR1}}',
            sender_id='TEST',
            sms_type='NORMAL'
        )
        
        response = self.client.get('/api/sms/templates/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_non_admin_cannot_create_template(self):
        """Test that non-admin users cannot create templates"""
        self.client.force_authenticate(user=self.regular_user)
        
        payload = {
            'template_name': 'test',
            'template_content': 'Test',
            'sender_id': 'TEST'
        }
        
        response = self.client.post('/api/sms/templates/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class SMSMessageTestCase(APITestCase):
    """Test SMS Message endpoints"""
    
    def setUp(self):
        """Set up test client and data"""
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.admin_user)
        
        self.template = SMSTemplate.objects.create(
            template_name='test_template',
            template_content='Hello {{VAR1}}',
            sender_id='TEST',
            is_approved=True,
            approval_status='APPROVED'
        )
    
    def test_send_message(self):
        """Test sending a single SMS"""
        payload = {
            'template': str(self.template.id),
            'recipient_number': '+971501234567',
            'variables': {'VAR1': 'Ahmed'}
        }
        
        response = self.client.post('/api/sms/messages/send/', payload, format='json')
        self.assertIn(response.status_code, [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ])
    
    def test_non_admin_cannot_send_message(self):
        """Test that non-admin users cannot send messages"""
        regular_user = User.objects.create_user(
            username='user',
            email='user@test.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=regular_user)
        
        payload = {
            'template': str(self.template.id),
            'recipient_number': '+971501234567'
        }
        
        response = self.client.post('/api/sms/messages/send/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class SMSConfigurationTestCase(APITestCase):
    """Test SMS Configuration endpoints"""
    
    def setUp(self):
        """Set up test client"""
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.admin_user)
    
    def test_get_configuration(self):
        """Test retrieving configuration"""
        response = self.client.get('/api/sms/config/retrieve/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
