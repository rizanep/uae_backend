import json
import logging
import http.client
from typing import Dict, List, Optional, Tuple
from django.conf import settings
from django.core.cache import cache
from rest_framework.exceptions import ValidationError
import ssl

logger = logging.getLogger(__name__)


class MSG91WhatsAppService:
    """
    Service for MSG91 WhatsApp API integration
    Handles all API calls securely with proper error handling and logging
    """
    
    BASE_URL = "api.msg91.com"
    CONTROL_URL = "control.msg91.com"
    
    def __init__(self):
        self.auth_key = settings.MSG91_AUTH_KEY
        self.integrated_number = settings.MSG91_INTEGRATED_NUMBER
        
        if not self.auth_key or not self.integrated_number:
            logger.error("MSG91 credentials not configured in settings")
            raise ValueError("MSG91 credentials not configured")

    def _make_request(
        self, 
        host: str, 
        method: str, 
        endpoint: str, 
        payload: Optional[str] = None,
        headers: Optional[Dict] = None
    ) -> Tuple[int, Dict]:
        """
        Make secure HTTPS request to MSG91 API
        
        Args:
            host: API host
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
            conn = http.client.HTTPSConnection(host, context=context, timeout=30)
            
            # Prepare headers
            default_headers = {
                'authkey': self.auth_key,
                'content-type': 'application/json',
                'accept': 'application/json',
                'User-Agent': 'Django-WhatsApp-Integration/1.0'
            }
            
            if headers:
                default_headers.update(headers)
            
            # Log request (without sensitive data)
            logger.info(
                f"MSG91 API Request: {method} /{endpoint}",
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
                    f"MSG91 API Error: {status_code}",
                    extra={'status': status_code, 'response': response_json}
                )
            else:
                logger.info(
                    f"MSG91 API Success: {status_code}",
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
        category: str,
        language_code: str,
        header_format: Optional[str] = None,
        header_text: Optional[str] = None,
        body_text: str = "",
        footer_text: Optional[str] = None,
        buttons: Optional[List[Dict]] = None
    ) -> Tuple[bool, Dict]:
        """
        Create WhatsApp template in MSG91
        
        Args:
            template_name: Name of template
            category: Template category (MARKETING, AUTHENTICATION, etc.)
            language_code: Language code (en, ar, hi, etc.)
            header_format: Header format (TEXT, IMAGE, VIDEO, etc.)
            header_text: Header text content
            body_text: Body text with variables
            footer_text: Optional footer text
            buttons: Optional list of buttons
        
        Returns:
            Tuple of (success, response_data)
        """
        
        # Build components array
        components = []
        
        # Add header if provided
        if header_format and header_text:
            components.append({
                "type": "HEADER",
                "format": header_format,
                "text": header_text if header_format == "TEXT" else None,
                "example": {
                    f"{header_format.lower()}_text": ["Sample header content"]
                } if header_format == "TEXT" else {}
            })
        
        # Add body
        components.append({
            "type": "BODY",
            "text": body_text,
            "example": {
                "body_text": [["Sample variable 1", "Sample variable 2"]]
            }
        })
        
        # Add footer if provided
        if footer_text:
            components.append({
                "type": "FOOTER",
                "text": footer_text
            })
        
        # Add buttons if provided
        if buttons:
            components.append({
                "type": "BUTTONS",
                "buttons": buttons
            })
        
        payload = json.dumps({
            "integrated_number": self.integrated_number,
            "template_name": template_name,
            "language": language_code,
            "category": category,
            "button_url": True,
            "components": components
        })
        
        status_code, response = self._make_request(
            self.BASE_URL,
            "POST",
            "api/v5/whatsapp/client-panel-template/",
            payload
        )
        
        success = status_code == 200 or status_code == 201
        return success, response

    def send_message(
        self,
        template_name: str,
        recipient_number: str,
        variables: Optional[Dict] = None
    ) -> Tuple[bool, Dict]:
        """
        Send WhatsApp message using template
        
        Args:
            template_name: Name of approved template
            recipient_number: Recipient phone number
            variables: Optional variables for template substitution
        
        Returns:
            Tuple of (success, response_data with message_id)
        """
        
        # Build components from variables
        components = {}
        
        if variables:
            # Build body components
            for key, value in variables.items():
                if key.startswith('body_'):
                    components[key] = {
                        "type": "text",
                        "value": str(value)
                    }
                elif key.startswith('header_'):
                    components[key] = {
                        "type": "text",
                        "value": str(value)
                    }
        
        payload = json.dumps({
            "integrated_number": self.integrated_number,
            "content_type": "template",
            "payload": {
                "messaging_product": "whatsapp",
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {
                        "code": "en",
                        "policy": "deterministic"
                    },
                    "namespace": None,
                    "to_and_components": [
                        {
                            "to": [recipient_number],
                            "components": components
                        }
                    ]
                }
            }
        })
        
        status_code, response = self._make_request(
            self.CONTROL_URL,
            "POST",
            "api/v5/whatsapp/whatsapp-outbound-message/bulk/",
            payload
        )
        
        success = status_code == 200
        return success, response

    def send_bulk_messages(
        self,
        template_name: str,
        recipient_numbers: List[str],
        variables_list: Optional[List[Dict]] = None
    ) -> Tuple[bool, Dict]:
        """
        Send bulk WhatsApp messages
        
        Args:
            template_name: Name of approved template
            recipient_numbers: List of recipient phone numbers
            variables_list: Optional list of variables dicts for each recipient
        
        Returns:
            Tuple of (success, response_data)
        """
        
        to_and_components = []
        
        for idx, recipient in enumerate(recipient_numbers):
            components = {}
            
            if variables_list and idx < len(variables_list):
                variables = variables_list[idx]
                for key, value in variables.items():
                    components[key] = {
                        "type": "text",
                        "value": str(value)
                    }
            
            to_and_components.append({
                "to": [recipient],
                "components": components
            })
        
        payload = json.dumps({
            "integrated_number": self.integrated_number,
            "content_type": "template",
            "payload": {
                "messaging_product": "whatsapp",
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {
                        "code": "en",
                        "policy": "deterministic"
                    },
                    "namespace": None,
                    "to_and_components": to_and_components
                }
            }
        })
        
        status_code, response = self._make_request(
            self.CONTROL_URL,
            "POST",
            "api/v5/whatsapp/whatsapp-outbound-message/bulk/",
            payload
        )
        
        success = status_code == 200
        return success, response

    def get_templates(
        self,
        template_name: Optional[str] = None,
        template_status: Optional[str] = None,
        language: Optional[str] = None
    ) -> Tuple[bool, Dict]:
        """
        Retrieve templates from MSG91
        
        Args:
            template_name: Optional filter by name
            template_status: Optional filter by status
            language: Optional filter by language
        
        Returns:
            Tuple of (success, response_data with templates)
        """
        
        params = []
        if template_name:
            params.append(f"template_name={template_name}")
        if template_status:
            params.append(f"template_status={template_status}")
        if language:
            params.append(f"template_language={language}")
        
        query_string = "&".join(params) if params else ""
        endpoint = f"api/v5/whatsapp/get-template-client/{self.integrated_number}"
        if query_string:
            endpoint += f"?{query_string}"
        
        status_code, response = self._make_request(
            self.CONTROL_URL,
            "GET",
            endpoint
        )
        
        success = status_code == 200
        return success, response

    def update_template(
        self,
        template_id: str,
        components: List[Dict]
    ) -> Tuple[bool, Dict]:
        """
        Update existing template
        
        Args:
            template_id: MSG91 template ID
            components: Updated components list
        
        Returns:
            Tuple of (success, response_data)
        """
        
        payload = json.dumps({
            "integrated_number": self.integrated_number,
            "components": components,
            "button_url": True
        })
        
        status_code, response = self._make_request(
            self.CONTROL_URL,
            "PUT",
            f"api/v5/whatsapp/client-panel-template/{template_id}/",
            payload
        )
        
        success = status_code == 200
        return success, response

    def delete_template(self, template_name: str) -> Tuple[bool, Dict]:
        """
        Delete template
        
        Args:
            template_name: Name of template to delete
        
        Returns:
            Tuple of (success, response_data)
        """
        
        endpoint = (
            f"api/v5/whatsapp/client-panel-template/"
            f"?integrated_number={self.integrated_number}"
            f"&template_name={template_name}"
        )
        
        status_code, response = self._make_request(
            self.CONTROL_URL,
            "DELETE",
            endpoint,
            payload=""
        )
        
        success = status_code == 200
        return success, response

    def get_message_logs(
        self,
        start_date: str,
        end_date: str
    ) -> Tuple[bool, Dict]:
        """
        Retrieve message logs/reports
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        
        Returns:
            Tuple of (success, response_data with logs)
        """
        
        endpoint = f"api/v5/report/logs/wa?startDate={start_date}&endDate={end_date}"
        
        status_code, response = self._make_request(
            self.CONTROL_URL,
            "POST",
            endpoint,
            payload=""
        )
        
        success = status_code == 200
        return success, response
