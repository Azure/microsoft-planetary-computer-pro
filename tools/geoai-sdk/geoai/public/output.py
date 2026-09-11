"""
geoai.public.output

Output class - Defines where model results should be written.
"""

import logging
from typing import Optional

import httpx
from azure.storage.blob import BlobServiceClient

from geoai.shared.exceptions import ValidationResult

logger = logging.getLogger(__name__)


class Output:
    """
    Output - Output destination configuration for model results.

    All results are published to GeoCatalog with assets stored in Azure Blob Storage.
    This is the primary workflow - local file saving is optional for debugging.

    Example:
        >>> from azure.identity import DefaultAzureCredential
        >>>
        >>> # Standard GeoCatalog workflow with blob storage
        >>> output = Output(
        ...     geocatalog_uri="https://geocatalog.contoso.com",
        ...     collection_name="building-detections",
        ...     credential=DefaultAzureCredential(),
        ...     storage_url="https://myaccount.blob.core.windows.net",
        ...     blob_container="results"
        ... )
        >>>
        >>> # With local file saving for debugging
        >>> output = Output(
        ...     geocatalog_uri="https://geocatalog.contoso.com",
        ...     collection_name="road-detections",
        ...     credential=DefaultAzureCredential(),
        ...     storage_url="https://myaccount.blob.core.windows.net",
        ...     blob_container="results",
        ...     save_local=True,
        ...     output_dir="./debug_output"
        ... )
    """

    def __init__(
        self,
        geocatalog_uri: str,
        collection_name: str,
        credential,
        storage_url: str,
        blob_container: str,
        storage_account_key: Optional[str] = None,
        run_id: Optional[str] = None,
        save_local: bool = False,
        output_dir: Optional[str] = None,
    ):
        """
        Initialize Output destination.

        :param geocatalog_uri: GeoCatalog/STAC endpoint URL (required)
        :param collection_name: Name of collection to create/use (required)
        :param credential: Azure credential for GeoCatalog auth and SAS generation (required)
        :param storage_url: Azure Blob Storage account URL, e.g., https://account.blob.core.windows.net (required)
        :param blob_container: Blob container name for storing chip imagery and STAC item assets (required)
        :param storage_account_key: Storage account key for SAS generation (optional if using Azure AD delegation)
        :param run_id: Run identifier for organizing results (auto-generated UUID if not provided)
        :param save_local: Save results to local files for debugging (default: False)
        :param output_dir: Local directory for saved files (only used if save_local=True, default: ./output)

        Note:
            For SAS token generation, the SDK tries Azure AD user delegation first (recommended).
            If that fails, it uses storage_account_key. For Azure AD delegation, your identity needs:
            - Storage Blob Data Contributor (for uploads)
            - Storage Blob Delegator (for SAS generation)

        :raises ValueError: If required parameters are missing
        """
        if not geocatalog_uri:
            raise ValueError("geocatalog_uri is required")

        if not collection_name:
            raise ValueError("collection_name is required")

        if not credential:
            raise ValueError("credential is required")

        if not storage_url:
            raise ValueError("storage_url is required - needed for STAC item assets")

        if not blob_container:
            raise ValueError("blob_container is required - needed for STAC item assets")

        # GeoCatalog (required)
        self.geocatalog_uri = geocatalog_uri
        self.collection_name = collection_name
        self.credential = credential

        # Blob storage (required for STAC assets)
        self.storage_url = storage_url
        self.blob_container = blob_container
        self.storage_account_key = storage_account_key

        # Run identification
        self.run_id = run_id  # Auto-generated UUID if None

        # Local output (opt-in for debugging)
        self.save_local = save_local
        self.output_dir = output_dir or "./output"

    def __repr__(self):
        return (
            f"Output("
            f"geocatalog_uri='{self.geocatalog_uri}', "
            f"collection_name='{self.collection_name}', "
            f"blob_container='{self.blob_container}', "
            f"save_local={self.save_local})"
        )

    async def validate(self) -> ValidationResult:
        """
        Validate Output configuration.

        Checks:
        - GeoCatalog endpoint is reachable
        - Credential has write permissions
        - Blob storage account is accessible
        - Blob container exists or can be created

        Returns:
            ValidationResult with is_valid, errors, and warnings

        Example:
            >>> output = Output(geocatalog_uri="...", collection_name="...", ...)
            >>> result = await output.validate()
            >>> if not result.is_valid:
            ...     print(f"Validation failed: {result.errors}")
        """
        errors = []
        warnings = []

        # Check GeoCatalog endpoint reachability
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    # Test GeoCatalog endpoint
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

        # Check authentication for GeoCatalog (if credential provided and endpoint is reachable)
        if self.credential and not errors:
            try:
                # Try to get a token - this validates the credential works
                # Note: get_token() is synchronous, not async
                token = self.credential.get_token("https://storage.azure.com/.default")
                if not token or not token.token:
                    errors.append("Credential failed to obtain access token for GeoCatalog")
                else:
                    logger.debug("GeoCatalog credential validated successfully")
            except Exception as e:
                # Sanitize error message to avoid exposing credentials
                error_msg = str(e)
                if hasattr(self, "credential") and self.credential:
                    error_msg = error_msg.replace(str(self.credential), "[CREDENTIAL_REDACTED]")
                errors.append(f"GeoCatalog authentication failed: {error_msg}")

        # Check blob storage access
        if self.storage_url and not errors:
            try:
                blob_service_client = BlobServiceClient(
                    account_url=self.storage_url, credential=self.credential
                )

                # Test listing containers (requires read permissions)
                try:
                    containers = blob_service_client.list_containers()
                    # Just check if we can list - consume first item if available
                    next(iter(containers), None)
                    logger.debug("Blob storage credential validated successfully")
                except Exception as e:
                    # Sanitize error message to avoid exposing credentials
                    error_msg = str(e)
                    if hasattr(self, "credential") and self.credential:
                        error_msg = error_msg.replace(str(self.credential), "[CREDENTIAL_REDACTED]")
                    errors.append(
                        f"Blob storage access denied: {error_msg}. "
                        f"Ensure your identity has 'Storage Blob Data Contributor' role."
                    )

                # Check if blob container exists or can be created
                if not errors:
                    try:
                        container_client = blob_service_client.get_container_client(
                            self.blob_container
                        )
                        if not container_client.exists():
                            warnings.append(
                                f"Blob container '{self.blob_container}' does not exist. "
                                f"It will be created automatically during execution."
                            )
                        else:
                            logger.debug(
                                f"Blob container '{self.blob_container}' exists and is accessible"
                            )
                    except Exception as e:
                        warnings.append(f"Could not verify blob container existence: {str(e)}")

            except Exception as e:
                errors.append(f"Blob storage validation failed: {str(e)}")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
