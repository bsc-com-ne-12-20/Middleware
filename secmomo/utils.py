import requests
import time
from requests.exceptions import RequestException, Timeout, ConnectionError
from django.conf import settings
from rest_framework.exceptions import APIException
from rest_framework import status
import logging
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class MobileMoneyAPIError(APIException):
    """Custom exception for Mobile Money API errors"""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'Mobile money service temporarily unavailable'
    default_code = 'service_unavailable'

    def __init__(self, detail=None, status_code=None):
        super().__init__(detail=detail)
        if status_code is not None:
            self.status_code = status_code

class MobileMoneyAPI:
    """
    Handles all communications with the Mobile Money API
    with comprehensive error handling and retry logic
    """
    
    @staticmethod
    def _get_api_config() -> Dict[str, Any]:
        """Get and validate API configuration from settings"""
        config = {
            'base_url': getattr(settings, 'MOBILE_MONEY_API_BASE_URL', ''),
            'timeout': getattr(settings, 'MOBILE_MONEY_API_TIMEOUT', 10)
        }
        
        if not config['base_url']:
            logger.error("Mobile Money API base URL not configured")
            raise MobileMoneyAPIError(detail='API service not configured')
        
        return config

    @staticmethod
    def _make_request(
        method: str,
        endpoint: str,
        payload: Optional[Dict] = None,
        retries: int = 1,
        headers: Optional[Dict] = None
    ) -> Dict:
        """
        Generic request handler with:
        - Automatic retries
        - Comprehensive error handling
        - Detailed logging
        """
        config = MobileMoneyAPI._get_api_config()
        url = f"{config['base_url'].rstrip('/')}/{endpoint.lstrip('/')}"
        
        # Use provided headers or default to empty
        request_headers = headers or {}
        request_headers["Content-Type"] = "application/json"
        
        last_exception = None
        
        for attempt in range(retries + 1):
            try:
                logger.info(
                    f"API Request Attempt {attempt + 1}/{retries + 1}: "
                    f"{method} {url}"
                )
                
                response = requests.request(
                    method,
                    url,
                    json=payload,
                    headers=request_headers,
                    timeout=config['timeout']
                )
                
                logger.debug(
                    f"API Response: {response.status_code}\n"
                    f"Headers: {response.headers}\n"
                    f"Body: {response.text[:500]}"  # Log first 500 chars of response
                )
                
                if response.status_code == 401:
                    error_detail = response.json().get('detail', 'Invalid API credentials')
                    raise MobileMoneyAPIError(
                        detail=error_detail,
                        status_code=status.HTTP_401_UNAUTHORIZED
                    )
                
                if response.status_code == 404:
                    raise MobileMoneyAPIError(
                        detail="API endpoint not found",
                        status_code=status.HTTP_404_NOT_FOUND
                    )
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.HTTPError as e:
                last_exception = e
                logger.error(
                    f"HTTP Error: {str(e)}\n"
                    f"Response: {e.response.text if e.response else 'None'}"
                )
                if attempt == retries:
                    raise MobileMoneyAPIError(
                        detail=f"API request failed: {str(e)}",
                        status_code=e.response.status_code if e.response else 503
                    )
                
            except (Timeout, ConnectionError) as e:
                last_exception = e
                logger.error(f"Connection error: {str(e)}")
                if attempt == retries:
                    raise MobileMoneyAPIError(detail="Connection to API service failed")
                
            except RequestException as e:
                last_exception = e
                logger.error(f"Request failed: {str(e)}")
                if attempt == retries:
                    raise MobileMoneyAPIError(detail="API request failed")
                
            except Exception as e:
                last_exception = e
                logger.exception("Unexpected API error")
                if attempt == retries:
                    raise MobileMoneyAPIError(detail="Internal API error")
            
            if attempt < retries:
                logger.info(f"Retrying in {1 + attempt} seconds...")
                time.sleep(1 + attempt)
        
        raise MobileMoneyAPIError(detail="API request failed after retries")

    @classmethod
    def authenticate_user(cls, email: str, password: str) -> Tuple[str, str]:
        """Authenticate user and return access and refresh tokens"""
        try:
            response = cls._make_request(
                'POST',
                '/api/v1/accounts/login/',
                {"email": email, "password": password},
                retries=1
            )
            return response['access'], response.get('refresh', '')
        except MobileMoneyAPIError as e:
            logger.error(f"Authentication failed for {email}: {str(e)}")
            raise MobileMoneyAPIError(detail="Invalid email or password")

    @classmethod
    def check_email_verification(cls, email: str, access_token: str) -> Dict:
        """Check if email is verified with the mobile money provider"""
        try:
            return cls._make_request(
                'POST',
                '/callback/check-verification/',
                {"email": email},
                retries=1,
                headers={"Authorization": f"Bearer {access_token}"}
            )
        except MobileMoneyAPIError as e:
            logger.warning(f"Email verification failed for {email}: {str(e)}")
            raise

    @classmethod
    def get_balance_by_email(cls, email: str, access_token: str) -> Dict:
        """Get current balance for a given email"""
        try:
            return cls._make_request(
                'POST',
                '/api/v1/accounts/get-balance/',
                {"email": email},
                retries=2,
                headers={"Authorization": f"Bearer {access_token}"}
            )
        except MobileMoneyAPIError as e:
            logger.error(f"Balance check failed for {email}: {str(e)}")
            raise

    @classmethod
    def validate_api_connection(cls) -> bool:
        """Validate that API connection is working"""
        try:
            test_response = cls._make_request(
                'GET',
                '/api/v1/health-check/',
                retries=0
            )
            return True
        except MobileMoneyAPIError:
            return False
def get_user_balance(email):
    """Retrieve user balance from main backend"""
    try:
        response = requests.post(
            'https://mtima.onrender.com/api/v1/accounts/get-balance/',
            json={'email': email},
            headers={'Authorization': f'Bearer {settings.MAIN_BACKEND_TOKEN}'}
        )
        response.raise_for_status()
        return response.json().get('balance', 0)
    except requests.exceptions.RequestException as e:
        logger.error(f"Balance retrieval failed: {str(e)}")
        raise MobileMoneyAPIError("Could not retrieve balance from main backend")