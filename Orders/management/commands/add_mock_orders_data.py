from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
import random

from Users.models import User, UserAddress
from Products.models import Product
from Cart.models import Cart, CartItem
from Orders.models import Order, OrderItem, Payment
from Reviews.models import Review


class Command(BaseCommand):
    help = "Create mock cart, order, payment, and review data for demo purposes"

    def handle(self, *args, **options):
        user = User.objects.filter(is_active=True).order_by("id").first()
        if not user:
            self.stdout.write(self.style.ERROR("No active users found. Create a user first."))
            return

        products = list(Product.objects.filter(is_available=True, stock__gt=0)[:5])
        if not products:
            self.stdout.write(self.style.ERROR("No products with stock found. Run product seed first."))
            return

        address, _ = UserAddress.objects.get_or_create(
            user=user,
            is_default=True,
            defaults={
                "label": "Home",
                "address_type": "home",
                "full_name": f"{user.first_name or ''} {user.last_name or ''}".strip() or "Customer",
                "phone_number": user.phone_number or "+971501234567",
                "street_address": "Demo Street 1",
                "area": "Demo Area",
                "city": "Dubai",
                "emirate": "dubai",
                "country": "AE",
            },
        )

        cart, _ = Cart.objects.get_or_create(user=user)
        cart.items.all().delete()

        for product in products[:3]:
            CartItem.objects.create(
                cart=cart,
                product=product,
                quantity=random.randint(1, 3),
            )

        self.stdout.write(self.style.SUCCESS(f"Created cart with {cart.total_items} items for {user}"))

        order_total = cart.total_price
        order = Order.objects.create(
            user=user,
            status=Order.OrderStatus.PENDING,
            shipping_address=address,
            total_amount=order_total,
            preferred_delivery_date=timezone.now().date(),
            preferred_delivery_slot="9AM - 12PM",
            delivery_notes="Leave at the door.",
        )

        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                product_name=item.product.name,
                quantity=item.quantity,
                price=item.product.final_price,
            )

        payment_amount = order.total_amount
        payment = Payment.objects.create(
            order=order,
            transaction_id=f"MOCK-{order.id}-{random.randint(1000,9999)}",
            telr_reference=f"TREF-{random.randint(100000,999999)}",
            amount=payment_amount,
            status=Payment.PaymentStatus.SUCCESS,
            payment_method="MOCK",
            provider_response={"mock": True},
        )

        self.stdout.write(self.style.SUCCESS(f"Created order #{order.id} and payment {payment.transaction_id}"))

        cart.items.all().delete()

        created_reviews = 0
        for product in products[:3]:
            if not Review.objects.filter(user=user, product=product).exists():
                Review.objects.create(
                    product=product,
                    user=user,
                    rating=random.randint(4, 5),
                    comment=f"Great quality {product.name.lower()}!",
                )
                created_reviews += 1

        self.stdout.write(self.style.SUCCESS(f"Created {created_reviews} review(s) for {user}"))

