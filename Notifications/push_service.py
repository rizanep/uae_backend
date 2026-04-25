import logging
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings

logger = logging.getLogger(__name__)

# Initialize Firebase app (singleton — safe to call at module level)
_firebase_app = None


def _get_firebase_app():
    global _firebase_app
    if _firebase_app is None:
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_FILE)
        _firebase_app = firebase_admin.initialize_app(cred)
    return _firebase_app


def send_push_to_user(user, title, body, data=None, image=None):
    """
    Send a push notification to all active devices of a user.

    Args:
        user: User model instance
        title: Notification title
        body: Notification body text
        data: Optional dict of custom key-value data (all values must be strings)
        image: Optional image URL for the notification

    Returns:
        dict with 'success_count' and 'failure_count'
    """
    from .models import FCMDevice

    tokens = list(
        FCMDevice.objects.filter(user=user, is_active=True)
        .values_list("registration_token", flat=True)
    )

    if not tokens:
        logger.info(f"No active FCM tokens for user {user.id}")
        return {"success_count": 0, "failure_count": 0}

    return send_push_to_tokens(tokens, title, body, data=data, image=image)


def send_push_to_tokens(tokens, title, body, data=None, image=None):
    """
    Send a push notification to a list of FCM tokens.

    Args:
        tokens: List of FCM registration token strings
        title: Notification title
        body: Notification body text
        data: Optional dict of custom key-value data (all values must be strings)
        image: Optional image URL

    Returns:
        dict with 'success_count' and 'failure_count'
    """
    from .models import FCMDevice

    if not tokens:
        return {"success_count": 0, "failure_count": 0}

    _get_firebase_app()

    notification = messaging.Notification(title=title, body=body, image=image)

    # Ensure all data values are strings (FCM requirement)
    if data:
        data = {k: str(v) for k, v in data.items()}

    message = messaging.MulticastMessage(
        notification=notification,
        data=data,
        tokens=tokens,
    )

    try:
        response = messaging.send_each_for_multicast(message)
    except Exception as e:
        logger.error(f"FCM send failed: {e}")
        return {"success_count": 0, "failure_count": len(tokens)}

    # Deactivate tokens that are no longer valid
    failed_tokens = []
    for idx, send_response in enumerate(response.responses):
        if send_response.exception is not None:
            error_code = getattr(send_response.exception, "code", None)
            if error_code in (
                "NOT_FOUND",
                "UNREGISTERED",
                "INVALID_ARGUMENT",
            ):
                failed_tokens.append(tokens[idx])
            logger.warning(
                f"FCM send error for token {tokens[idx][:20]}...: "
                f"{send_response.exception}"
            )

    if failed_tokens:
        deactivated = FCMDevice.objects.filter(
            registration_token__in=failed_tokens
        ).update(is_active=False)
        logger.info(f"Deactivated {deactivated} invalid FCM tokens")

    logger.info(
        f"FCM multicast: {response.success_count} success, "
        f"{response.failure_count} failure"
    )

    return {
        "success_count": response.success_count,
        "failure_count": response.failure_count,
    }


def send_push_to_all_users(title, body, data=None, image=None):
    """
    Send a push notification to ALL users with active FCM tokens.

    Returns:
        dict with 'success_count' and 'failure_count'
    """
    from .models import FCMDevice

    tokens = list(
        FCMDevice.objects.filter(is_active=True)
        .values_list("registration_token", flat=True)
    )

    if not tokens:
        return {"success_count": 0, "failure_count": 0}

    # FCM multicast limit is 500 tokens per call
    total_success = 0
    total_failure = 0
    batch_size = 500

    for i in range(0, len(tokens), batch_size):
        batch = tokens[i : i + batch_size]
        result = send_push_to_tokens(batch, title, body, data=data, image=image)
        total_success += result["success_count"]
        total_failure += result["failure_count"]

    return {"success_count": total_success, "failure_count": total_failure}
