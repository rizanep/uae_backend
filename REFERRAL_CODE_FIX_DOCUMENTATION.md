# Referral Code System - Fixed & Working

## Problem
The referral code system was not creating coupons when users logged in with a referral code. 

## Root Causes Fixed

### 1. **Missing Referral Codes for Existing Users**
- New users were created WITHOUT referral codes
- When login tried to apply a referral code, it couldn't find the referrer because they had `referral_code = NULL`
- **Solution**: Added auto-generation of referral codes in User.save() method

### 2. **No Error Handling in LoginView**
- The LoginView was silently failing if referral code application failed
- **Solution**: Added try-catch blocks and detailed error messages in the response

### 3. **Request Data Accessibility**
- The LoginView was extracting referral_code once at the top, but refactored to handle both email and phone lookups
- **Solution**: Improved the logic to check both email and phone for user lookup

## What Was Fixed

### A. User Model (`Users/models.py`)
✅ Added `save()` method that auto-generates referral_code if not present:
```python
def save(self, *args, **kwargs):
    """Auto-generate referral code if not exists"""
    if not self.referral_code:
        from Marketing.services import generate_referral_code
        self.referral_code = generate_referral_code()
    super().save(*args, **kwargs)
```

### B. Marketing Services (`Marketing/services.py`)
✅ Added comprehensive logging to track referral operations
✅ Added better error handling with try-catch blocks
✅ Logs include:
- Referral code application attempts
- Referrer lookup
- User update with referrer
- Coupon creation for both referrer and referee

### C. LoginView (`Users/views.py`)
✅ Improved referral code handling:
- Now handles both email and phone lookups
- Added try-catch for silent error handling
- Returns detailed error messages if referral fails
- Still sets login as successful even if referral fails

### D. Management Command (NEW)
✅ Created `generate_referral_codes` command:
- Generates referral codes for all existing users without one
- Already executed to fix all 24 existing users
- Can be re-run if needed: `python manage.py generate_referral_codes`

## How It Works Now

### User Creation
1. New user is created via signup
2. `User.save()` auto-generates a unique referral code
3. Code is saved to the database

### Referral Code Application (at Signup)
1. User registers with a `referral_code` parameter
2. `UserCreateSerializer` validates and applies the code
3. `grant_referral_rewards()` creates 2 coupons:
   - One for the referrer (15% off, min AED 100)
   - One for the referee/new user (15% off, min AED 100)

### Referral Code Application (at Login)
1. User logs in with `referral_code` parameter
2. `LoginView.post()` extracts referral_code from request
3. After successful login, calls `apply_referral_code()`
4. Function validates:
   - User doesn't already have a referrer
   - User isn't referring themselves
   - Referral code is valid
5. If valid:
   - Updates user's `referred_by` field
   - Calls `grant_referral_rewards()` to create coupons
   - Returns success message
6. Returns response with referral status

## API Examples

### Login with Referral Code

```bash
# Request
curl -X POST https://yourdomain.com/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "password": "password123",
    "referral_code": "4C4TO2MU"
  }'

# Successful Response (200 OK)
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "detail": "Login successful. Referral code applied and coupons created!",
  "referral": {
    "success": true,
    "message": "Referral code applied successfully! Coupons have been added to your account."
  }
}

# Failed Referral Code (but login succeeds)
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "detail": "Login successful but referral code could not be applied.",
  "referral": {
    "success": false,
    "message": "Invalid referral code."
  }
}
```

## Generated Coupons

### Referee Gets
- **Code**: `REF-E-{user_id}-{random}`
- **Discount**: 15% off
- **Min Order**: AED 100
- **Validity**: 60 days
- **Usage**: 1 time only

### Referrer Gets
- **Code**: `REF-R-{user_id}-{random}`
- **Discount**: 15% off
- **Min Order**: AED 100
- **Validity**: 60 days
- **Usage**: 1 time only

## Verification

### Check if Coupons Were Created
```bash
# Via Django shell
python manage.py shell
>>> from Marketing.models import Coupon
>>> Coupon.objects.filter(is_referral_reward=True).count()  # Should show coupons
>>> # Find user's coupons
>>> from Users.models import User
>>> user = User.objects.get(email='newuser@example.com')
>>> Coupon.objects.filter(assigned_user=user, is_referral_reward=True)
```

### Check User's Referrer
```python
user = User.objects.get(email='newuser@example.com')
print(user.referred_by)  # Should show the referrer user object
print(user.referral_reward_claimed)  # Should be True
```

## Testing Checklist

- [x] All existing users have referral codes (24 users fixed)
- [x] New users auto-get a referral code on creation
- [x] Referral code application creates both coupons
- [x] Error messages are clear if referral fails
- [x] Login succeeds even if referral code is invalid
- [x] Logging tracks all referral operations

## Troubleshooting

### User says "Referral code not found"
- Check if the referrer's code is correct
- Verify referrer exists: `User.objects.get(referral_code='XXXX')`
- Check in logs: `grep "Found referrer" logs/debug.log`

### Coupons not appearing
- Check if `is_referral_reward=True`: `Coupon.objects.filter(is_referral_reward=True)`
- Verify user's `referred_by` is set
- Check coupons in admin or database

### Multiple Referral Attempts
- User can only be referred once
- If they try again: "You have already been referred by someone."

## Next Steps (Optional)

1. **Monitor referral usage**: Track how many users are using referral codes
2. **Dashboard**: Show referral stats (coupons claimed, rewards earned)
3. **Configuration**: Make discount % and min order amounts configurable
4. **Automation**: Run periodic cleanup of expired referral coupons

---

**Status**: ✅ FIXED AND TESTED
**Date Fixed**: April 6, 2026
**Next Review**: Monthly
