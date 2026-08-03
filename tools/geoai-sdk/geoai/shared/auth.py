"""
geoai.shared.auth

Shared authentication helpers for Azure AI Foundry / Azure ML model endpoints.

Supports both string credentials (API keys / JWT tokens) and Azure credential
objects (e.g. ``DefaultAzureCredential``) with automatic OAuth scope detection
based on the endpoint URL.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# OAuth scopes
COGNITIVE_SERVICES_SCOPE = "https://cognitiveservices.azure.com/.default"
AZURE_ML_SCOPE = "https://ml.azure.com/.default"

# Endpoint URL patterns that map to the Cognitive Services / AI Foundry scope
_AI_FOUNDRY_PATTERNS = (
    "inference.ai.azure.com",  # AI Foundry model inference
    "openai.azure.com",  # Azure OpenAI
    "cognitiveservices.azure.com",  # Cognitive Services
)


def get_auth_scope(endpoint: str) -> str:
    """
    Determine the appropriate OAuth scope based on the endpoint URL.

    Supports both Azure ML and Azure AI Foundry endpoints automatically.

    :param endpoint: Model endpoint URL
    :return: OAuth scope string
    """
    endpoint_lower = (endpoint or "").lower()

    if any(pattern in endpoint_lower for pattern in _AI_FOUNDRY_PATTERNS):
        return COGNITIVE_SERVICES_SCOPE

    # Azure ML managed endpoints (default for backwards compatibility)
    return AZURE_ML_SCOPE


def build_auth_headers(endpoint: str, credential: Any) -> Dict[str, str]:
    """
    Build authentication headers based on credential type.

    Supports:
    - String credentials: API keys or JWT tokens (sent as Bearer token)
    - Azure credential objects: e.g. ``DefaultAzureCredential`` with automatic
      scope detection

    :param endpoint: Model endpoint URL (used for scope detection)
    :param credential: API key (str) or Azure credential object
    :return: Headers dictionary with Authorization header (may be empty)
    """
    headers: Dict[str, str] = {}

    if not credential:
        return headers

    if isinstance(credential, str):
        # API Key or JWT Token authentication
        headers["Authorization"] = f"Bearer {credential}"
    else:
        # Azure AD authentication with dynamic scope detection
        try:
            scope = get_auth_scope(endpoint)
            token = credential.get_token(scope)
            headers["Authorization"] = f"Bearer {token.token}"
            logger.debug(f"Using Azure AD auth with scope: {scope}")
        except Exception as e:  # noqa: BLE001 - surface guidance, do not crash
            logger.warning(f"Failed to get Azure AD token: {e}")
            logger.warning("Ensure you have the appropriate role assignment:")
            logger.warning("  - Azure ML: 'AzureML Data Scientist' role")
            logger.warning("  - AI Foundry: 'Azure AI Developer' or 'Cognitive Services User' role")

    return headers
