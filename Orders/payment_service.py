import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

ZIINA_API_BASE = "https://api-v2.ziina.com/api"


class ZiinaPaymentService:
    """
    Service for Ziina Payment Gateway integration.
    Handles creating payment intents, checking status, and refunds.
    """

    @staticmethod
    def _get_headers():
        return {
            "Authorization": f"Bearer {settings.ZIINA_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @staticmethod
    def create_payment_intent(order, use_app_urls=False, success_url=None, cancel_url=None, failure_url=None):
        """
        Create a Ziina payment intent for the given order.
        Amount is sent in fils (1 AED = 100 fils).
        Returns dict with payment_intent_id and redirect_url.
        """
        amount_fils = int(order.total_amount * 100)

        if use_app_urls:
            success_url = success_url or settings.ZIINA_APP_SUCCESS_URL
            cancel_url = cancel_url or settings.ZIINA_APP_CANCEL_URL
            failure_url = failure_url or settings.ZIINA_APP_FAILURE_URL
        else:
            success_url = success_url or settings.ZIINA_SUCCESS_URL
            cancel_url = cancel_url or settings.ZIINA_CANCEL_URL
            failure_url = failure_url or settings.ZIINA_FAILURE_URL

        payload = {
            "amount": amount_fils,
            "currency_code": "AED",
            "message": f"Order #{order.id}",
            "success_url": success_url,
            "cancel_url": cancel_url,
            "failure_url": failure_url,
            "test": settings.ZIINA_TEST_MODE,
        }

        logger.info(f"Creating Ziina payment intent for Order #{order.id}, amount={amount_fils} fils")

        try:
            resp = requests.post(
                f"{ZIINA_API_BASE}/payment_intent",
                json=payload,
                headers=ZiinaPaymentService._get_headers(),
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            logger.info(f"Ziina payment intent created: {data.get('id')} for Order #{order.id}")

            return {
                "payment_intent_id": data["id"],
                "redirect_url": data["redirect_url"],
                "status": data.get("status"),
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Ziina create_payment_intent failed for Order #{order.id}: {e}")
            raise

    @staticmethod
    def get_payment_intent(payment_intent_id):
        """
        Retrieve a Ziina payment intent by ID.
        Returns the full payment intent object.
        """
        logger.info(f"Fetching Ziina payment intent: {payment_intent_id}")

        try:
            resp = requests.get(
                f"{ZIINA_API_BASE}/payment_intent/{payment_intent_id}",
                headers=ZiinaPaymentService._get_headers(),
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            logger.info(f"Ziina payment intent {payment_intent_id} status: {data.get('status')}")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Ziina get_payment_intent failed for {payment_intent_id}: {e}")
            raise

    @staticmethod
    def create_refund(payment_intent_id, amount_fils=None, currency_code="AED"):
        """
        Create a refund for a Ziina payment intent.
        amount_fils: amount in fils to refund (None = full refund via the original amount).
        """
        payload = {
            "payment_intent_id": payment_intent_id,
            "currency_code": currency_code,
        }
        if amount_fils is not None:
            payload["amount"] = amount_fils

        logger.info(f"Creating Ziina refund for payment intent {payment_intent_id}")

        try:
            resp = requests.post(
                f"{ZIINA_API_BASE}/refund",
                json=payload,
                headers=ZiinaPaymentService._get_headers(),
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            logger.info(f"Ziina refund created: {data.get('id')} for payment intent {payment_intent_id}")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Ziina create_refund failed for {payment_intent_id}: {e}")
            raise

    @staticmethod
    def get_refund(refund_id):
        """
        Retrieve a Ziina refund by ID.
        """
        logger.info(f"Fetching Ziina refund: {refund_id}")

        try:
            resp = requests.get(
                f"{ZIINA_API_BASE}/refund/{refund_id}",
                headers=ZiinaPaymentService._get_headers(),
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            logger.info(f"Ziina refund {refund_id} status: {data.get('status')}")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Ziina get_refund failed for {refund_id}: {e}")
            raise
