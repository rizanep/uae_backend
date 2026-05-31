from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from Orders.models import DeliveryAssignment, DeliveryCancellationRequest, DeliveryProof, Order
from Users.models import DeliveryBoyProfile, UserAddress

User = get_user_model()


class DeliveryWorkflowAPITestCase(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin.delivery@test.com",
            password="adminpass123",
            role="admin",
            is_staff=True,
            is_superuser=True,
        )

        self.delivery_boy = User.objects.create_user(
            email="delivery1@test.com",
            password="deliverypass123",
            role="delivery_boy",
            is_active=True,
        )
        self.delivery_profile, _ = DeliveryBoyProfile.objects.get_or_create(
            user=self.delivery_boy,
            defaults={
                "assigned_emirates": ["dubai"],
                "is_available": True,
            },
        )
        self.delivery_profile.assigned_emirates = ["dubai"]
        self.delivery_profile.is_available = True
        self.delivery_profile.save()

        self.customer = User.objects.create_user(
            email="customer.delivery@test.com",
            password="customerpass123",
            role="user",
            is_active=True,
        )

        self.customer_address = UserAddress.objects.create(
            user=self.customer,
            label="Home",
            address_type="home",
            full_name="Delivery Customer",
            phone_number="+971501234001",
            street_address="Test Street 12",
            area="Business Bay",
            city="Dubai",
            emirate="dubai",
            country="AE",
            is_default=True,
        )

        self.available_order = Order.objects.create(
            user=self.customer,
            status=Order.OrderStatus.PAID,
            shipping_address=self.customer_address,
            total_amount=Decimal("120.00"),
        )

    def test_delivery_dashboard_and_available_orders(self):
        self.client.force_authenticate(user=self.delivery_boy)

        dashboard_url = reverse("order-delivery-dashboard")
        dashboard_res = self.client.get(dashboard_url)

        self.assertEqual(dashboard_res.status_code, status.HTTP_200_OK)
        self.assertIn("delivery_boy", dashboard_res.data)
        self.assertIn("kpis", dashboard_res.data)
        self.assertEqual(dashboard_res.data["kpis"]["available_orders_in_region"], 1)

        available_url = reverse("order-available-orders")
        available_res = self.client.get(available_url)

        self.assertEqual(available_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(available_res.data), 1)
        self.assertEqual(available_res.data[0]["id"], self.available_order.id)

    def test_claim_order_creates_assignment_and_moves_processing(self):
        self.client.force_authenticate(user=self.delivery_boy)

        claim_url = reverse("order-claim-order", args=[self.available_order.id])
        claim_res = self.client.post(claim_url, {"notes": "Claimed for route A"}, format="json")

        self.assertEqual(claim_res.status_code, status.HTTP_200_OK)

        self.available_order.refresh_from_db()
        assignment = DeliveryAssignment.objects.get(order=self.available_order)

        self.assertEqual(assignment.delivery_boy_id, self.delivery_boy.id)
        self.assertEqual(assignment.status, DeliveryAssignment.AssignmentStatus.ASSIGNED)
        self.assertEqual(self.available_order.status, Order.OrderStatus.PROCESSING)

    def test_delivery_status_shipped_and_delivered_with_proof(self):
        DeliveryAssignment.objects.create(
            order=self.available_order,
            delivery_boy=self.delivery_boy,
            assigned_by=self.admin,
            status=DeliveryAssignment.AssignmentStatus.ASSIGNED,
        )
        self.available_order.status = Order.OrderStatus.PROCESSING
        self.available_order.save(update_fields=["status", "updated_at"])

        self.client.force_authenticate(user=self.delivery_boy)

        status_url = reverse("order-delivery-update-status", args=[self.available_order.id])

        ship_res = self.client.post(
            status_url,
            {"status": Order.OrderStatus.SHIPPED, "notes": "Picked up from warehouse"},
            format="json",
        )
        self.assertEqual(ship_res.status_code, status.HTTP_200_OK)

        self.available_order.refresh_from_db()
        assignment = DeliveryAssignment.objects.get(order=self.available_order)
        self.assertEqual(self.available_order.status, Order.OrderStatus.SHIPPED)
        self.assertEqual(assignment.status, DeliveryAssignment.AssignmentStatus.IN_TRANSIT)

        proof_file = SimpleUploadedFile(
            "proof.jpg",
            b"fake-image-bytes",
            content_type="image/jpeg",
        )

        delivered_res = self.client.post(
            status_url,
            {
                "status": Order.OrderStatus.DELIVERED,
                "notes": "Delivered to customer",
                "signature_name": "Customer Name",
                "proof_notes": "Front desk handover",
                "proof_image": proof_file,
            },
            format="multipart",
        )

        self.assertEqual(delivered_res.status_code, status.HTTP_200_OK)

        self.available_order.refresh_from_db()
        assignment.refresh_from_db()
        proof = DeliveryProof.objects.get(order=self.available_order)

        self.assertEqual(self.available_order.status, Order.OrderStatus.DELIVERED)
        self.assertEqual(assignment.status, DeliveryAssignment.AssignmentStatus.COMPLETED)
        self.assertIsNotNone(assignment.delivered_at)
        self.assertEqual(proof.uploaded_by_id, self.delivery_boy.id)

    def test_cancel_request_needs_admin_approval(self):
        DeliveryAssignment.objects.create(
            order=self.available_order,
            delivery_boy=self.delivery_boy,
            assigned_by=self.admin,
            status=DeliveryAssignment.AssignmentStatus.ASSIGNED,
        )
        self.available_order.status = Order.OrderStatus.SHIPPED
        self.available_order.save(update_fields=["status", "updated_at"])

        self.client.force_authenticate(user=self.delivery_boy)
        status_url = reverse("order-delivery-update-status", args=[self.available_order.id])

        cancel_res = self.client.post(
            status_url,
            {"status": Order.OrderStatus.CANCELLED, "reason": "Customer unreachable after multiple attempts"},
            format="json",
        )
        self.assertEqual(cancel_res.status_code, status.HTTP_202_ACCEPTED)

        self.available_order.refresh_from_db()
        cancel_request = DeliveryCancellationRequest.objects.get(order=self.available_order)

        self.assertEqual(self.available_order.status, Order.OrderStatus.SHIPPED)
        self.assertEqual(cancel_request.status, DeliveryCancellationRequest.RequestStatus.PENDING)

        self.client.force_authenticate(user=self.admin)
        review_url = reverse("order-admin-review-cancel-request", args=[self.available_order.id])
        review_res = self.client.post(
            review_url,
            {"decision": "approve", "review_notes": "Approved after call center verification"},
            format="json",
        )

        self.assertEqual(review_res.status_code, status.HTTP_200_OK)

        self.available_order.refresh_from_db()
        cancel_request.refresh_from_db()

        self.assertEqual(self.available_order.status, Order.OrderStatus.CANCELLED)
        self.assertEqual(cancel_request.status, DeliveryCancellationRequest.RequestStatus.APPROVED)
        self.assertEqual(cancel_request.reviewed_by_id, self.admin.id)
