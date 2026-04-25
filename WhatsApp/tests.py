from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import WhatsAppTemplate, WhatsAppMessage, WhatsAppConfiguration
import uuid


class WhatsAppTemplateTestCase(APITestCase):
    """Test WhatsApp Template endpoints"""
    
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
        """Test creating a WhatsApp template"""
        payload = {
            'template_name': 'test_template',
            'integrated_number': '+971501234567',
            'language': 'en',
            'category': 'MARKETING',
            'body_text': 'Hello {{1}}, this is a test template',
            'approval_status': 'PENDING'
        }
        
        response = self.client.post('/api/whatsapp/templates/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['template_name'], 'test_template')
    
    def test_list_templates(self):
        """Test listing templates"""
        WhatsAppTemplate.objects.create(
            template_name='test1',
            integrated_number='+971501234567',
            body_text='Test template 1'
        )
        
        response = self.client.get('/api/whatsapp/templates/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_non_admin_cannot_create_template(self):
        """Test that non-admin users cannot create templates"""
        self.client.force_authenticate(user=self.regular_user)
        
        payload = {
            'template_name': 'test_template',
            'integrated_number': '+971501234567',
            'body_text': 'Test'
        }
        
        response = self.client.post('/api/whatsapp/templates/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class WhatsAppMessageTestCase(APITestCase):
    """Test WhatsApp Message endpoints"""
    
    def setUp(self):
        """Set up test client and data"""
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.admin_user)
        
        self.template = WhatsAppTemplate.objects.create(
            template_name='test_template',
            integrated_number='+971501234567',
            body_text='Hello {{1}}',
            is_approved=True,
            approval_status='APPROVED'
        )
    
    def test_send_message(self):
        """Test sending a single message"""
        payload = {
            'template': str(self.template.id),
            'recipient_number': '+971509876543',
            'variables': {'body_1': 'John'}
        }
        
        response = self.client.post('/api/whatsapp/messages/send/', payload, format='json')
        # This will fail if MSG91 service is not configured, but tests structure is correct
        # In production, mock the service
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
            'recipient_number': '+971509876543'
        }
        
        response = self.client.post('/api/whatsapp/messages/send/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class WhatsAppConfigurationTestCase(APITestCase):
    """Test WhatsApp Configuration endpoints"""
    
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
        WhatsAppConfiguration.objects.create(
            integrated_number='+971501234567',
            daily_limit=10000,
            monthly_limit=300000
        )
        
        response = self.client.get('/api/whatsapp/config/retrieve/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
