import uuid
import logging

logger = logging.getLogger(__name__)

class TelrPaymentService:
    """
    Mock service for Telr Payment Integration.
    In production, this would use the Telr API to initiate and verify payments.
    """
    
    @staticmethod
    def initiate_payment(order):
        """
        Mock initiating a payment with Telr.
        Returns a mock payment URL and reference.
        """
        mock_ref = f"TELR_{uuid.uuid4().hex[:10].upper()}"
        logger.info(f"Initiating mock payment for Order #{order.id}, Amount: {order.total_amount}")
        
        # In real Telr, we would call their API here
        return {
            "payment_url": f"https://secure.telr.com/gateway/process.html?ref={mock_ref}",
            "reference": mock_ref
        }

    @staticmethod
    def verify_payment(reference):
        """
        Mock verifying a payment status from Telr.
        Always returns success for now.
        """
        logger.info(f"Verifying mock payment for Reference: {reference}")
        
        # Mocking a successful payment verification
        return {
            "status": "SUCCESS",
            "transaction_id": f"TXN_{uuid.uuid4().hex[:12].upper()}"
        }
