import json
import logging
import http.client
from typing import Dict, List, Optional, Tuple
from django.conf import settings
from rest_framework.exceptions import ValidationError
import ssl

logger = logging.getLogger(__name__)


class MSG91SMSService:
    """
    Service for MSG91 SMS API integration
    Handles all SMS API calls securely with proper error handling and logging
    """
    
    CONTROL_URL = "control.msg91.com"
    
    def __init__(self):
        self.auth_key = settings.MSG91_AUTH_KEY
        
        if not self.auth_key:
            logger.error("MSG91 auth key not configured in settings")
            raise ValueError("MSG91 auth key not configured")

    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        payload: Optional[str] = None,
        headers: Optional[Dict] = None
    ) -> Tuple[int, Dict]:
        """
        Make secure HTTPS request to MSG91 API
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            payload: Request body (JSON string)
            headers: Additional headers
        
        Returns:
            Tuple of (status_code, response_data)
        """
        try:
            # Create connection with SSL verification
            context = ssl.create_default_context()
            conn = http.client.HTTPSConnection(self.CONTROL_URL, context=context, timeout=30)
            
            # Prepare headers
            default_headers = {
                'authkey': self.auth_key,
                'content-type': 'application/json',
                'accept': 'application/json',
                'User-Agent': 'Django-SMS-Integration/1.0'
            }
            
            if headers:
                default_headers.update(headers)
            
            # Log request (without sensitive data)
            logger.info(
                f"MSG91 SMS API Request: {method} /{endpoint}",
                extra={'endpoint': endpoint, 'method': method}
            )
            
            # Make request
            conn.request(method, f"/{endpoint}", payload or "", default_headers)
            
            # Get response
            response = conn.getresponse()
            response_data = response.read().decode('utf-8')
            status_code = response.status
            
            conn.close()
            
            # Parse response
            try:
                response_json = json.loads(response_data) if response_data else {}
            except json.JSONDecodeError:
                response_json = {'raw_response': response_data}
            
            # Log response
            if status_code >= 400:
                logger.warning(
                    f"MSG91 SMS API Error: {status_code}",
                    extra={'status': status_code, 'response': response_json}
                )
            else:
                logger.info(
                    f"MSG91 SMS API Success: {status_code}",
                    extra={'status': status_code}
                )
            
            return status_code, response_json
            
        except http.client.HTTPException as e:
            logger.error(f"HTTP Connection Error: {str(e)}")
            raise ValidationError(f"API Connection Error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected Error in MSG91 Request: {str(e)}")
            raise ValidationError(f"Unexpected Error: {str(e)}")

    def create_template(
        self,
        template_name: str,
        template_content: str,
        sender_id: str,
        sms_type: str = 'NORMAL',
        dlt_template_id: Optional[str] = None
    ) -> Tuple[bool, Dict]:
        """
        Create SMS template in MSG91
        
        Args:
            template_name: Name of template
            template_content: SMS content with variables
            sender_id: Sender ID (max 11 chars)
            sms_type: Type of SMS (NORMAL, TRANSACTIONAL, OTP, PROMOTIONAL)
            dlt_template_id: DLT Template ID (required for India)
        
        Returns:
            Tuple of (success, response_data)
        """
        
        payload = {
            "template": template_content,
            "sender_id": sender_id,
            "template_name": template_name,
            "smsType": sms_type,
        }
        
        if dlt_template_id:
            payload["dlt_template_id"] = dlt_template_id
        
        # Convert to form data format
        form_data = "&".join([f"{k}={v}" for k, v in payload.items()])
        
        status_code, response = self._make_request(
            "POST",
            "api/v5/sms/addTemplate",
            form_data,
            headers={'content-type': 'application/x-www-form-urlencoded'}
        )
        
        success = status_code == 200 or status_code == 201
        return success, response

    def send_message(
        self,
        template_id: str,
        recipient_number: str,
        variables: Optional[Dict] = None,
        short_url: bool = False,
        short_url_expiry: int = 3600,
        realtime_response: bool = False
    ) -> Tuple[bool, Dict]:
        """
        Send SMS using template
        
        Args:
            template_id: MSG91 template ID
            recipient_number: Recipient phone number
            variables: Optional variables for template substitution
            short_url: Enable short URL (1 or 0)
            short_url_expiry: URL expiry in seconds
            realtime_response: Get realtime response (1 or 0)
        
        Returns:
            Tuple of (success, response_data with message_id)
        """
        
        # Build recipient object
        recipient = {
            "mobiles": recipient_number
        }
        
        # Add variables
        if variables:
            for key, value in variables.items():
                recipient[key] = str(value)
        
        payload = {
            "template_id": template_id,
            "short_url": "1" if short_url else "0",
            "recipients": [recipient]
        }
        
        if short_url and short_url_expiry:
            payload["short_url_expiry"] = short_url_expiry
        
        if realtime_response:
            payload["realTimeResponse"] = "1"
        
        payload_json = json.dumps(payload)
        
        status_code, response = self._make_request(
            "POST",
            "api/v5/flow",
            payload_json
        )
        
        success = status_code == 200
        return success, response

    def send_bulk_messages(
        self,
        template_id: str,
        recipient_numbers: List[str],
        variables_list: Optional[List[Dict]] = None,
        short_url: bool = False,
        short_url_expiry: int = 3600,
        realtime_response: bool = False
    ) -> Tuple[bool, Dict]:
        """
        Send bulk SMS
        
        Args:
            template_id: MSG91 template ID
            recipient_numbers: List of recipient phone numbers
            variables_list: Optional list of variables dicts for each recipient
            short_url: Enable short URL
            short_url_expiry: URL expiry in seconds
            realtime_response: Get realtime response
        
        Returns:
            Tuple of (success, response_data)
        """
        
        recipients = []
        
        for idx, recipient_num in enumerate(recipient_numbers):
            recipient = {
                "mobiles": recipient_num
            }
            
            if variables_list and idx < len(variables_list):
                variables = variables_list[idx]
                for key, value in variables.items():
                    recipient[key] = str(value)
            
            recipients.append(recipient)
        
        payload = {
            "template_id": template_id,
            "short_url": "1" if short_url else "0",
            "recipients": recipients
        }
        
        if short_url and short_url_expiry:
            payload["short_url_expiry"] = short_url_expiry
        
        if realtime_response:
            payload["realTimeResponse"] = "1"
        
        payload_json = json.dumps(payload)
        
        status_code, response = self._make_request(
            "POST",
            "api/v5/flow",
            payload_json
        )
        
        success = status_code == 200
        return success, response

    def get_template_versions(
        self,
        template_id: str
    ) -> Tuple[bool, Dict]:
        """
        Get template versions and details
        
        Args:
            template_id: MSG91 template ID
        
        Returns:
            Tuple of (success, response_data with template info)
        """
        
        payload = json.dumps({
            "template_id": template_id
        })
        
        status_code, response = self._make_request(
            "POST",
            "api/v5/sms/getTemplateVersions",
            payload
        )
        
        success = status_code == 200
        return success, response

    def get_sms_logs(
        self,
        start_date: str,
        end_date: str
    ) -> Tuple[bool, Dict]:
        """
        Retrieve SMS delivery logs/reports
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        
        Returns:
            Tuple of (success, response_data with logs)
        """
        
        endpoint = f"api/v5/report/logs/p/sms?startDate={start_date}&endDate={end_date}"
        
        status_code, response = self._make_request(
            "POST",
            endpoint,
            payload=""
        )
        
        success = status_code == 200
        return success, response

    def render_message(self, template_content: str, variables: Optional[Dict] = None) -> str:
        """
        Render SMS template with variables
        
        Args:
            template_content: Template with {{VAR1}}, {{VAR2}}, etc.
            variables: Dictionary of variable values
        
        Returns:
            Rendered message content
        """
        content = template_content
        
        if variables:
            for key, value in variables.items():
                placeholder = "{{" + key + "}}"
                content = content.replace(placeholder, str(value))
        
        return content
