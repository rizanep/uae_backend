from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse

from Products.models import Product, Category
from .models import Review

User = get_user_model()


class ReviewVisibilityTestCase(APITestCase):
    """
    Test that users can see their own reviews even when hidden,
    but other users can only see visible reviews.
    """

    def setUp(self):
        # Create test users
        self.user1 = User.objects.create_user(
            email='user1@example.com',
            password='password123',
            first_name='User',
            last_name='One'
        )
        self.user2 = User.objects.create_user(
            email='user2@example.com',
            password='password123',
            first_name='User',
            last_name='Two'
        )
        self.admin = User.objects.create_superuser(
            email='admin@example.com',
            password='password123',
            first_name='Admin',
            last_name='User'
        )

        # Create test category and product
        self.category = Category.objects.create(
            name='Test Category',
            description='Test category description'
        )
        self.product = Product.objects.create(
            name='Test Product',
            description='Test product description',
            price=100.00,
            category=self.category,
            stock_quantity=10
        )

        # Create reviews
        self.visible_review = Review.objects.create(
            product=self.product,
            user=self.user1,
            rating=5,
            comment='Great product!',
            is_visible=True
        )
        self.hidden_review = Review.objects.create(
            product=self.product,
            user=self.user2,
            rating=3,
            comment='Okay product',
            is_visible=False
        )

    def test_user_can_see_own_hidden_review(self):
        """Test that user2 can see their own hidden review"""
        self.client.force_authenticate(user=self.user2)
        url = reverse('review-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should see both reviews: visible one and own hidden one
        self.assertEqual(len(response.data['results']), 2)

        # Check that both reviews are included
        review_ids = [review['id'] for review in response.data['results']]
        self.assertIn(self.visible_review.id, review_ids)
        self.assertIn(self.hidden_review.id, review_ids)

    def test_user_cannot_see_others_hidden_reviews(self):
        """Test that user1 cannot see user2's hidden review"""
        self.client.force_authenticate(user=self.user1)
        url = reverse('review-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should only see the visible review
        self.assertEqual(len(response.data['results']), 1)

        review_ids = [review['id'] for review in response.data['results']]
        self.assertIn(self.visible_review.id, review_ids)
        self.assertNotIn(self.hidden_review.id, review_ids)

    def test_anonymous_user_only_sees_visible_reviews(self):
        """Test that anonymous users only see visible reviews"""
        url = reverse('review-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should only see the visible review
        self.assertEqual(len(response.data['results']), 1)

        review_ids = [review['id'] for review in response.data['results']]
        self.assertIn(self.visible_review.id, review_ids)
        self.assertNotIn(self.hidden_review.id, review_ids)

    def test_admin_sees_all_reviews(self):
        """Test that admin can see all reviews regardless of visibility"""
        self.client.force_authenticate(user=self.admin)
        url = reverse('review-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should see both reviews
        self.assertEqual(len(response.data['results']), 2)

        review_ids = [review['id'] for review in response.data['results']]
        self.assertIn(self.visible_review.id, review_ids)
        self.assertIn(self.hidden_review.id, review_ids)
