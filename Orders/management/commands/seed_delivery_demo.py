from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from Orders.models import DeliveryAssignment, Order
from Users.models import DeliveryBoyProfile, UserAddress


User = get_user_model()


class Command(BaseCommand):
    help = "Seed demo delivery users, emirate assignments, and sample delivery orders"

    def handle(self, *args, **options):
        admin = self._get_or_create_user(
            email="delivery-admin@demo.com",
            password="Admin@123",
            role="admin",
            first_name="Delivery",
            last_name="Admin",
            is_staff=True,
            is_superuser=True,
        )

        delivery_dubai = self._get_or_create_user(
            email="delivery.dubai@demo.com",
            password="Delivery@123",
            role="delivery_boy",
            first_name="Dubai",
            last_name="Rider",
        )

        delivery_abu = self._get_or_create_user(
            email="delivery.abudhabi@demo.com",
            password="Delivery@123",
            role="delivery_boy",
            first_name="Abu",
            last_name="Rider",
        )

        self._set_delivery_profile(delivery_dubai, ["dubai", "sharjah"], "DXB-1001")
        self._set_delivery_profile(delivery_abu, ["abu_dhabi"], "AUH-2001")

        customer = self._get_or_create_user(
            email="delivery.customer@demo.com",
            password="Customer@123",
            role="user",
            first_name="Demo",
            last_name="Customer",
        )

        address_dubai = self._get_or_create_address(
            user=customer,
            label="Dubai Home",
            emirate="dubai",
            city="Dubai",
            area="Business Bay",
            phone_number="+971501111001",
            street_address="Business Bay Street 10",
            is_default=True,
        )

        address_abu = self._get_or_create_address(
            user=customer,
            label="Abu Dhabi Home",
            emirate="abu_dhabi",
            city="Abu Dhabi",
            area="Al Reem",
            phone_number="+971501111002",
            street_address="Al Reem Street 5",
            is_default=False,
        )

        order_available_dubai = self._get_or_create_order(
            user=customer,
            shipping_address=address_dubai,
            status=Order.OrderStatus.PAID,
            total_amount=Decimal("145.00"),
            delivery_notes="Ring bell once",
        )

        order_assigned_processing = self._get_or_create_order(
            user=customer,
            shipping_address=address_dubai,
            status=Order.OrderStatus.PROCESSING,
            total_amount=Decimal("230.00"),
            delivery_notes="Call on arrival",
        )

        order_assigned_shipped = self._get_or_create_order(
            user=customer,
            shipping_address=address_dubai,
            status=Order.OrderStatus.SHIPPED,
            total_amount=Decimal("320.00"),
            delivery_notes="Hand over at reception",
        )

        order_available_abu = self._get_or_create_order(
            user=customer,
            shipping_address=address_abu,
            status=Order.OrderStatus.PAID,
            total_amount=Decimal("180.00"),
            delivery_notes="Customer in office",
        )

        DeliveryAssignment.objects.update_or_create(
            order=order_assigned_processing,
            defaults={
                "delivery_boy": delivery_dubai,
                "assigned_by": admin,
                "status": DeliveryAssignment.AssignmentStatus.ASSIGNED,
                "notes": "Processing stage assignment",
            },
        )

        DeliveryAssignment.objects.update_or_create(
            order=order_assigned_shipped,
            defaults={
                "delivery_boy": delivery_dubai,
                "assigned_by": admin,
                "status": DeliveryAssignment.AssignmentStatus.IN_TRANSIT,
                "notes": "Already picked and out for delivery",
            },
        )

        self.stdout.write(self.style.SUCCESS("Delivery demo seed completed."))
        self.stdout.write("Login credentials:")
        self.stdout.write("  Admin: delivery-admin@demo.com / Admin@123")
        self.stdout.write("  Dubai Delivery: delivery.dubai@demo.com / Delivery@123")
        self.stdout.write("  Abu Dhabi Delivery: delivery.abudhabi@demo.com / Delivery@123")
        self.stdout.write("  Customer: delivery.customer@demo.com / Customer@123")
        self.stdout.write("Demo orders created/updated:")
        self.stdout.write(f"  Available (Dubai): Order #{order_available_dubai.id}")
        self.stdout.write(f"  Assigned Processing (Dubai): Order #{order_assigned_processing.id}")
        self.stdout.write(f"  Assigned Shipped (Dubai): Order #{order_assigned_shipped.id}")
        self.stdout.write(f"  Available (Abu Dhabi): Order #{order_available_abu.id}")

    def _get_or_create_user(self, **kwargs):
        email = kwargs.pop("email")
        password = kwargs.pop("password")
        defaults = kwargs

        user, created = User.objects.get_or_create(email=email, defaults=defaults)

        changed = False
        for key, value in defaults.items():
            if getattr(user, key) != value:
                setattr(user, key, value)
                changed = True

        if created or not user.has_usable_password():
            user.set_password(password)
            changed = True

        if changed:
            user.save()

        return user

    def _set_delivery_profile(self, user, emirates, vehicle_number):
        profile, _ = DeliveryBoyProfile.objects.get_or_create(user=user)
        profile.assigned_emirates = emirates
        profile.is_available = True
        profile.vehicle_number = vehicle_number
        profile.save()
        return profile

    def _get_or_create_address(
        self,
        user,
        label,
        emirate,
        city,
        area,
        phone_number,
        street_address,
        is_default,
    ):
        address, _ = UserAddress.objects.get_or_create(
            user=user,
            label=label,
            defaults={
                "address_type": "home",
                "full_name": f"{user.first_name} {user.last_name}".strip() or "Customer",
                "phone_number": phone_number,
                "street_address": street_address,
                "area": area,
                "city": city,
                "emirate": emirate,
                "country": "AE",
                "is_default": is_default,
            },
        )

        address.address_type = "home"
        address.full_name = f"{user.first_name} {user.last_name}".strip() or "Customer"
        address.phone_number = phone_number
        address.street_address = street_address
        address.area = area
        address.city = city
        address.emirate = emirate
        address.country = "AE"
        address.is_default = is_default
        address.save()
        return address

    def _get_or_create_order(self, user, shipping_address, status, total_amount, delivery_notes):
        order, _ = Order.objects.get_or_create(
            user=user,
            shipping_address=shipping_address,
            status=status,
            total_amount=total_amount,
            defaults={
                "delivery_notes": delivery_notes,
            },
        )
        order.status = status
        order.total_amount = total_amount
        order.delivery_notes = delivery_notes
        order.save()
        return order
