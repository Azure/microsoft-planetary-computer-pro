"""
geoai.public.input

Input class - Defines where the model gets its data.
"""

import logging
from typing import List, Optional

import httpx

from geoai.shared.exceptions import ValidationResult

logger = logging.getLogger(__name__)


class Input:
    """
    Input - Data source configuration for models.

    Supports both public and private STAC catalogs:
    - Public Planetary Computer (default, no authentication required)
    - Private GeoCatalog instances (authentication required)

    Example:
        >>> # Public Planetary Computer (default - no URI needed!)
        >>> input = Input(collection="naip")
        >>>
        >>> # Private GeoCatalog (specify URI and credential)
        >>> from azure.identity import DefaultAzureCredential
        >>> input = Input(
        ...     collection="your-high-res-imagery",
        ...     geocatalog_uri="https://your-geocatalog.com/stac",
        ...     credential=DefaultAzureCredential()
        ... )
    """

    def __init__(
        self,
        collection: Optional[str] = None,
        geocatalog_uri: str = "https://planetarycomputer.microsoft.com/api/stac/v1",
        credential=None,
        assets: Optional[List[str]] = None,
    ):
        """
        Initialize Input data source.

        :param collection: Collection name (required for AOI-based models)
        :param geocatalog_uri: GeoCatalog/STAC endpoint URL (defaults to Planetary Computer)
        :param credential: Azure credential (optional - only needed for private GeoCatalogs)
                          Use None for public Planetary Computer
        :param assets: Specific assets to fetch (optional)

        Examples:
            Public Planetary Computer (no auth):
                >>> input = Input(
                ...     geocatalog_uri="https://planetarycomputer.microsoft.com/api/stac/v1",
                ...     collection="naip",
                ...     credential=None
                ... )

            Private GeoCatalog (auth required):
                >>> from azure.identity import DefaultAzureCredential
                >>> input = Input(
                ...     geocatalog_uri="https://your-geocatalog.com",
                ...     collection="your-collection",
                ...     credential=DefaultAzureCredential()
                ... )

        :raises ValueError: If geocatalog_uri is missing
        """
        if not geocatalog_uri:
            raise ValueError("geocatalog_uri is required")

        self.geocatalog_uri = geocatalog_uri
        self.credential = credential
        self.collection = collection
        self.assets = assets or []

    async def validate(self) -> ValidationResult:
        """
        Validate Input configuration.

        Checks:
        - GeoCatalog endpoint is reachable
        - Credential works (if provided)
        - Collection exists in catalog (if specified)

        Returns:
            ValidationResult with is_valid, errors, and warnings

        Example:
            >>> input = Input(geocatalog_uri="...", collection="naip", credential=...)
            >>> result = await input.validate()
            >>> if not result.is_valid:
            ...     print(f"Validation failed: {result.errors}")
        """
        errors = []
        warnings = []

        # Check endpoint reachability
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try to reach the root or collections endpoint
                try:
                    resp = await client.get(self.geocatalog_uri)
                    if resp.status_code not in [200, 301, 302]:
                        errors.append(
                            f"GeoCatalog endpoint returned status {resp.status_code}: {self.geocatalog_uri}"
                        )
                except httpx.HTTPStatusError as e:
                    errors.append(f"GeoCatalog endpoint error: {e}")
                except httpx.RequestError as e:
                    errors.append(f"Cannot reach GeoCatalog endpoint: {e}")
        except Exception as e:
            errors.append(f"GeoCatalog validation failed: {e}")

        # Check authentication (if credential provided)
        if self.credential and not errors:  # Only check auth if endpoint is reachable
            try:
                # Try to get a token - this validates the credential works
                # Note: get_token() is synchronous for azure.identity credentials
                token = self.credential.get_token("https://storage.azure.com/.default")
                if not token or not token.token:
                    errors.append("Credential failed to obtain access token")
                else:
                    logger.debug("Credential validated successfully")
            except Exception as e:
                # Sanitize error message to avoid exposing credentials
                error_msg = str(e)
                # Remove common credential patterns from error messages
                if hasattr(self, "credential") and self.credential:
                    error_msg = error_msg.replace(str(self.credential), "[CREDENTIAL_REDACTED]")
                errors.append(f"Authentication failed: {error_msg}")

        # Check collection exists (if specified and endpoint is reachable)
        if self.collection and not errors:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # Build headers with auth if credential provided
                    headers = {}
                    if self.credential:
                        try:
                            token = self.credential.get_token("https://storage.azure.com/.default")
                            headers["Authorization"] = f"Bearer {token.token}"
                        except:
                            pass  # Already caught above

                    # Try to fetch collection metadata
                    collections_url = f"{self.geocatalog_uri.rstrip('/')}/collections"
                    resp = await client.get(collections_url, headers=headers)

                    if resp.status_code == 200:
                        data = resp.json()
                        collection_ids = [c.get("id") for c in data.get("collections", [])]

                        if self.collection not in collection_ids:
                            warnings.append(
                                f"Collection '{self.collection}' not found in catalog. "
                                f"Available: {collection_ids[:5]}{'...' if len(collection_ids) > 5 else ''}"
                            )
                    else:
                        warnings.append(
                            f"Could not verify collection existence (status {resp.status_code})"
                        )
            except Exception as e:
                warnings.append(f"Could not verify collection: {e}")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    def __repr__(self):
        return (
            f"Input(geocatalog_uri='{self.geocatalog_uri}', "
            f"collection='{self.collection}', "
            f"assets={self.assets})"
        )
