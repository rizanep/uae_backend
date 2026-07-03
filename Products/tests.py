from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Category, Product, ProductUnit


class ProductUnitApiTests(APITestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.admin_user = self.user_model.objects.create_user(
            email="admin@example.com",
            password="password123",
            is_staff=True,
            is_superuser=True,
            role="admin",
        )
        self.category = Category.objects.create(name="Fish")
        self.unit = ProductUnit.objects.create(name="box", sort_order=1)
        self.client.force_authenticate(self.admin_user)

    def test_admin_can_create_product_with_unit_id_and_response_keeps_unit_text(self):
        response = self.client.post(
            "/api/products/products/",
            {
                "category": self.category.id,
                "name": "Salmon Box",
                "description": "Fresh salmon",
                "price": "25.00",
                "stock": 10,
                "is_available": True,
                "unit_id": self.unit.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        product = Product.objects.get(id=response.data["id"])
        self.assertEqual(product.unit_option, self.unit)
        self.assertEqual(product.unit, "box")
        self.assertEqual(response.data["unit"], "box")
        self.assertEqual(response.data["unit_id"], self.unit.id)

    def test_existing_text_unit_is_preserved_in_api_response(self):
        product = Product.objects.create(
            category=self.category,
            name="Shrimp",
            description="Fresh shrimp",
            price="10.00",
            stock=5,
            is_available=True,
            unit="kg",
        )

        response = self.client.get(f"/api/products/products/{product.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["unit"], "kg")
