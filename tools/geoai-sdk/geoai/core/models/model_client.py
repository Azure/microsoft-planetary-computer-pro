"""
geoai.core.models.model_client

ModelClient - Handles all model communication using specs.
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from .payload_builder import PayloadBuilder
from .response_parser import ResponseParser
from .spec_loader import ModelSpecLoader

logger = logging.getLogger(__name__)


class ModelClient:
    """
    ModelClient - Handles inference requests to models using spec-driven configuration.

    Responsibilities:
    - Load model spec
    - Build request payloads (via PayloadBuilder)
    - Execute HTTP requests with proper auth
    - Parse responses (via ResponseParser)

    :param endpoint: Model endpoint URL
    :param credential: Authentication credential (API key string or Azure credential object)
    :param model_spec: Model specification dictionary

    Example:

      ```python
      spec = ModelSpecLoader.load("microsoft/eo-os-object-detection")
      client = ModelClient(
          endpoint="https://eoos.ml.azure.com/detect_objects_batch",
          credential="api_key_or_credential",
          model_spec=spec
      )

      detections = await client.infer_batch(
          images=[image_data1, image_data2],
          params={"threshold": 0.6}
      )
      ```
    """

    def __init__(self, endpoint: str, credential: Any, model_spec: Dict):
        """
        ModelClient initializes with endpoint, credential, and model spec.

        :param endpoint: Model endpoint URL
        :param credential: API key (str) or Azure credential object
        :param model_spec: Model specification dictionary from spec_loader
        """
        self.endpoint = endpoint
        self.credential = credential
        self.spec = model_spec

        # Initialize spec-driven components
        self.payload_builder = PayloadBuilder(model_spec["foundry_api"])
        self.response_parser = ResponseParser(model_spec["foundry_api"])

        logger.info(f"Initialized ModelClient for {model_spec['model_id']}")
        logger.info(f"  Payload format: {model_spec['foundry_api']['payload_format']}")
        logger.info(f"  Endpoint: {endpoint}")

    async def infer(self, image: Dict, params: Dict) -> List[Dict]:
        """
        Run inference on a SINGLE image.

        Note: Endpoints accept one image per request but support concurrent requests.
        For parallel processing, use asyncio.gather() with multiple infer() calls.

        :param image: Single preprocessed image (bytes or array)
        :param params: Model parameters (threshold, etc.)
        :return: List of detection dictionaries from this image

        :raises httpx.HTTPError: If request fails
        :raises ValueError: If response parsing fails

        Example:
            # Process multiple chips concurrently (recommended)
            tasks = [model_client.infer(img, params) for img in images]
            results = await asyncio.gather(*tasks)
        """
        import time

        start_time = time.time()

        # 1. Build payload using spec-driven builder (wraps single image in list)
        payload = self.payload_builder.build(images=[image], params=params)

        # 2. Execute request with authentication
        logger.debug(f"[INFO] Starting inference request...")
        response_data = await self._execute_request(payload)

        elapsed = time.time() - start_time

        # 3. Parse response using spec-driven parser
        detections = self.response_parser.parse(response_data)

        logger.info(f"[SUCCESS] Inference complete: {len(detections)} detections in {elapsed:.2f}s")

        return detections

    async def validate_auth(self) -> tuple[bool, Optional[str]]:
        """
        Validate model endpoint authentication with a lightweight test request.

        Tests that:
        - Endpoint is reachable
        - Authentication credentials are valid
        - Endpoint accepts requests

        :return: (is_valid: bool, error_message: Optional[str])

        Example:
            >>> client = ModelClient(endpoint="...", credential="...", model_spec=spec)
            >>> is_valid, error = await client.validate_auth()
            >>> if not is_valid:
            ...     print(f"Auth failed: {error}")
        """
        try:
            headers = self._build_auth_headers()

            # Use a short timeout for validation
            timeout = httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=10.0)

            async with httpx.AsyncClient(timeout=timeout) as client:
                # Try a simple GET request first (health check if available)
                # Many endpoints return 405 for GET, which still confirms auth works
                try:
                    response = await client.get(self.endpoint, headers=headers)

                    # Any response means endpoint is reachable
                    if response.status_code == 401:
                        return (
                            False,
                            f"Authentication failed (401 Unauthorized). Check your credential/API key.",
                        )
                    elif response.status_code == 403:
                        return (
                            False,
                            f"Access forbidden (403). Ensure you have proper role assignments.",
                        )
                    elif response.status_code in [200, 405]:
                        # 200 = success, 405 = method not allowed (but auth passed)
                        logger.debug(f"Endpoint authentication validated successfully")
                        return True, None
                    else:
                        # Other status codes still mean endpoint is reachable
                        logger.debug(f"Endpoint responded with status {response.status_code}")
                        return True, None

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 401:
                        return (
                            False,
                            f"Authentication failed (401 Unauthorized). Check your credential/API key.",
                        )
                    elif e.response.status_code == 403:
                        return (
                            False,
                            f"Access forbidden (403). Ensure you have proper role assignments.",
                        )
                    else:
                        # Other errors might still mean auth is OK
                        logger.debug(f"Endpoint validation: {e}")
                        return True, None

                except httpx.ConnectError as e:
                    return False, f"Cannot connect to endpoint: {str(e)}"

                except httpx.TimeoutException:
                    # Timeout might mean endpoint is slow but reachable
                    logger.warning("Endpoint validation timed out, but endpoint may be valid")
                    return True, None

        except Exception as e:
            return False, f"Endpoint validation failed: {str(e)}"

    async def _execute_request(self, payload: Dict) -> Dict:
        """
        Execute HTTP request to model endpoint with authentication.

        :param payload: Request payload from PayloadBuilder
        :return: Response JSON

        :raises httpx.HTTPError: If request fails
        """
        # Build headers with authentication
        headers = self._build_auth_headers()

        # Determine request type based on payload structure
        # Use longer timeout for large payloads (e.g., TIF images can be 5-10MB)
        timeout = httpx.Timeout(connect=30.0, read=300.0, write=300.0, pool=30.0)

        async with httpx.AsyncClient(timeout=timeout) as client:
            # Check if payload has 'files' (multipart) or is JSON
            if "files" in payload:
                # Multipart request (EO-OS style)
                response = await client.post(
                    self.endpoint,
                    files=payload["files"],
                    data=payload.get("data", {}),
                    headers=headers,
                )
            else:
                # JSON request (MARS style)
                response = await client.post(self.endpoint, json=payload, headers=headers)

            # Log errors for debugging
            if response.status_code != 200:
                logger.error(f"Endpoint returned status {response.status_code}")
                logger.error(f"Response headers: {response.headers}")
                logger.error(f"Response body: {response.text[:500]}")  # First 500 chars

            response.raise_for_status()

            return response.json()

    def _get_auth_scope(self) -> str:
        """
        Determine appropriate OAuth scope based on endpoint URL.

        Supports both Azure ML and Azure AI Foundry endpoints automatically.

        :return: OAuth scope string
        """
        endpoint_lower = self.endpoint.lower()

        # Azure AI Foundry / Cognitive Services endpoints
        if any(
            pattern in endpoint_lower
            for pattern in [
                "inference.ai.azure.com",  # AI Foundry model inference
                "openai.azure.com",  # Azure OpenAI
                "cognitiveservices.azure.com",  # Cognitive Services
            ]
        ):
            return "https://cognitiveservices.azure.com/.default"

        # Azure ML managed endpoints (default for backwards compatibility)
        # Patterns: *.inference.ml.azure.com, *.azureml.net, etc.
        return "https://ml.azure.com/.default"

    def _build_auth_headers(self) -> Dict[str, str]:
        """
        Build authentication headers based on credential type.

        Supports:
        - String credentials: API keys or JWT tokens (Bearer auth)
        - Azure credential objects: DefaultAzureCredential with automatic scope detection

        :return: Headers dictionary with Authorization header
        """
        headers = {}

        if self.credential:
            if isinstance(self.credential, str):
                # API Key or JWT Token authentication
                headers["Authorization"] = f"Bearer {self.credential}"
            else:
                # Azure AD authentication with dynamic scope detection
                try:
                    scope = self._get_auth_scope()
                    token = self.credential.get_token(scope)
                    headers["Authorization"] = f"Bearer {token.token}"
                    logger.debug(f"Using Azure AD auth with scope: {scope}")
                except Exception as e:
                    logger.warning(f"Failed to get Azure AD token: {e}")
                    logger.warning(f"Ensure you have the appropriate role assignment:")
                    logger.warning(f"  - Azure ML: 'AzureML Data Scientist' role")
                    logger.warning(
                        f"  - AI Foundry: 'Azure AI Developer' or 'Cognitive Services User' role"
                    )

        return headers

    async def close(self):
        """Close any open resources (for future connection pooling)."""
        pass
