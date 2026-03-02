import uuid
import random
import string
from django.utils import timezone
from .models import Coupon
from Users.models import User

def generate_referral_code():
    """Generate a unique referral code."""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if not User.objects.filter(referral_code=code).exists():
            return code

def create_first_order_coupon(user):
    """Create a coupon for the user's first order."""
    if Coupon.objects.filter(assigned_user=user, is_first_order_reward=True).exists():
        return None

    code = f"WELCOME-{user.id}-{uuid.uuid4().hex[:4].upper()}"
    coupon = Coupon.objects.create(
        code=code,
        description="Welcome Gift! Enjoy a discount on your first order.",
        discount_type='percentage',
        discount_value=10.00,  # 10% off, can be configured
        min_order_amount=50.00,
        valid_from=timezone.now(),
        valid_to=timezone.now() + timezone.timedelta(days=30),
        usage_limit=1,
        assigned_user=user,
        is_first_order_reward=True
    )
    return coupon

def grant_referral_rewards(referrer, referee):
    """Grant coupons to both referrer and referee."""
    # Coupon for Referrer
    referrer_code = f"REF-R-{referrer.id}-{uuid.uuid4().hex[:4].upper()}"
    Coupon.objects.create(
        code=referrer_code,
        description=f"Referral Reward for inviting {referee.email or referee.phone_number}",
        discount_type='percentage',
        discount_value=15.00,  # 15% off
        min_order_amount=100.00,
        valid_from=timezone.now(),
        valid_to=timezone.now() + timezone.timedelta(days=60),
        usage_limit=1,
        assigned_user=referrer,
        is_referral_reward=True
    )

    # Coupon for Referee
    referee_code = f"REF-E-{referee.id}-{uuid.uuid4().hex[:4].upper()}"
    Coupon.objects.create(
        code=referee_code,
        description=f"Referral Bonus for joining via {referrer.email or referrer.phone_number}",
        discount_type='percentage',
        discount_value=15.00,  # 15% off
        min_order_amount=100.00,
        valid_from=timezone.now(),
        valid_to=timezone.now() + timezone.timedelta(days=60),
        usage_limit=1,
        assigned_user=referee,
        is_referral_reward=True
    )

def apply_referral_code(user, referral_code):
    """
    Apply a referral code to a user account.
    Returns: (success: bool, message: str)
    """
    if user.referred_by:
        return False, "You have already been referred by someone."
    
    if user.referral_code == referral_code:
        return False, "You cannot refer yourself."

    try:
        referrer = User.objects.get(referral_code=referral_code)
    except User.DoesNotExist:
        return False, "Invalid referral code."

    user.referred_by = referrer
    user.referral_reward_claimed = True
    user.save(update_fields=['referred_by', 'referral_reward_claimed'])
    
    grant_referral_rewards(referrer, user)
    
    return True, "Referral code applied successfully! Coupons have been added to your account."
