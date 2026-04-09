import uuid
import random
import string
import logging
from django.utils import timezone
from .models import Coupon
from Users.models import User

logger = logging.getLogger(__name__)

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
    try:
        # Coupon for Referrer
        referrer_code = f"REF-R-{referrer.id}-{uuid.uuid4().hex[:4].upper()}"
        referrer_coupon = Coupon.objects.create(
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
        logger.info(f"Created referral coupon for referrer: {referrer_code} (ID: {referrer_coupon.id})")

        # Coupon for Referee
        referee_code = f"REF-E-{referee.id}-{uuid.uuid4().hex[:4].upper()}"
        referee_coupon = Coupon.objects.create(
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
        logger.info(f"Created referral coupon for referee: {referee_code} (ID: {referee_coupon.id})")
        
        return True
    except Exception as e:
        logger.error(f"Error granting referral rewards: {str(e)}", exc_info=True)
        raise

def apply_referral_code(user, referral_code):
    """
    Apply a referral code to a user account.
    Returns: (success: bool, message: str)
    """
    logger.info(f"Attempting to apply referral code '{referral_code}' to user {user.email or user.phone_number}")
    
    if user.referred_by:
        msg = f"User {user.id} already has a referrer"
        logger.warning(msg)
        return False, "You have already been referred by someone."
    
    if user.referral_code == referral_code:
        msg = f"User {user.id} attempted to refer themselves with code {referral_code}"
        logger.warning(msg)
        return False, "You cannot refer yourself."

    try:
        referrer = User.objects.get(referral_code=referral_code)
        logger.info(f"Found referrer: {referrer.email or referrer.phone_number} (ID: {referrer.id})")
    except User.DoesNotExist:
        msg = f"Referral code '{referral_code}' not found in database"
        logger.error(msg)
        return False, "Invalid referral code."

    try:
        user.referred_by = referrer
        user.referral_reward_claimed = True
        user.save(update_fields=['referred_by', 'referral_reward_claimed'])
        logger.info(f"User {user.id} referred_by updated to {referrer.id}")
        
        grant_referral_rewards(referrer, user)
        logger.info(f"Referral rewards granted: referrer={referrer.id}, referee={user.id}")
        
        return True, "Referral code applied successfully! Coupons have been added to your account."
    except Exception as e:
        logger.error(f"Error applying referral code: {str(e)}", exc_info=True)
        return False, f"Error applying referral code: {str(e)}"
