from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import ContactMessage

User = get_user_model()


class ContactMessageTestCase(APITestCase):
    """Test cases for ContactMessageViewSet."""

    def setUp(self):
        """Set up test data."""
        # Create admin user
        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="adminpass123",
            role="admin",
            is_staff=True,
            is_superuser=True,
            is_email_verified=True
        )

        # Create regular user with verified email
        self.verified_user = User.objects.create_user(
            email="verified@example.com",
            password="userpass123",
            role="user",
            is_email_verified=True
        )

        # Create regular user without verified email
        self.unverified_user = User.objects.create_user(
            email="unverified@example.com",
            password="userpass123",
            role="user",
            is_email_verified=False
        )

        # Create a contact message
        self.contact_msg = ContactMessage.objects.create(
            name="Test User",
            email="test@example.com",
            subject="Test Subject",
            message="Test message content",
            is_resolved=False
        )

    def test_create_contact_message_verified_user(self):
        """Test that verified users can create contact messages."""
        self.client.force_authenticate(user=self.verified_user)
        url = reverse('contact-messages-list')
        data = {
            "subject": "Help needed",
            "message": "I need assistance with my order."
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check that message was created with correct data
        contact_msg = ContactMessage.objects.get(subject="Help needed")
        self.assertEqual(contact_msg.email, self.verified_user.email)
        self.assertEqual(contact_msg.name, self.verified_user.email)  # Since no full name

    def test_create_contact_message_unverified_user(self):
        """Test that unverified users cannot create contact messages."""
        self.client.force_authenticate(user=self.unverified_user)
        url = reverse('contact-messages-list')
        data = {
            "subject": "Help needed",
            "message": "I need assistance with my order."
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("email must be verified", response.data['detail'])

    def test_create_contact_message_unauthenticated(self):
        """Test that unauthenticated users cannot create contact messages."""
        url = reverse('contact-messages-list')
        data = {
            "subject": "Help needed",
            "message": "I need assistance with my order."
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_list_contact_messages(self):
        """Test that admin can list all contact messages."""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('contact-messages-list')

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Should see the test message

    def test_regular_user_cannot_list_messages(self):
        """Test that regular users cannot list contact messages."""
        self.client.force_authenticate(user=self.verified_user)
        url = reverse('contact-messages-list')

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_reply_to_message(self):
        """Test that admin can reply to contact messages."""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('contact-messages-reply', kwargs={'pk': self.contact_msg.id})
        data = {
            "reply_message": "Thank you for your message. We'll get back to you soon.",
            "mark_resolved": True
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Reply sent successfully", response.data['detail'])

        # Check that message was marked as resolved
        self.contact_msg.refresh_from_db()
        self.assertTrue(self.contact_msg.is_resolved)

    def test_admin_reply_without_message(self):
        """Test that admin cannot reply without providing a message."""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('contact-messages-reply', kwargs={'pk': self.contact_msg.id})
        data = {}  # Empty data

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Reply message is required", response.data['detail'])

    def test_regular_user_cannot_reply(self):
        """Test that regular users cannot reply to messages."""
        self.client.force_authenticate(user=self.verified_user)
        url = reverse('contact-messages-reply', kwargs={'pk': self.contact_msg.id})
        data = {
            "reply_message": "This should not work"
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
