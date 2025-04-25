import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Tuple
from urllib.parse import urljoin, urlparse

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientResponseError
from azure.core.credentials import AccessToken
from azure.identity.aio import DefaultAzureCredential
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_fixed,
)

from stacforge.clients.storage_client import StorageClient
from stacforge.logging import LOGGER_NAME
from stacforge.utils import get_cloud

_logger = logging.getLogger(LOGGER_NAME)

API_VERSION = {"api-version": "2024-01-31-preview"}

RETRIES = 3
WAIT_SECONDS = 2


def retry_transient_errors(func):
    """Retry only for transient errors when calling the function."""

    return retry(
        retry=retry_if_exception(
            lambda e: isinstance(e, ClientResponseError)
            and e.code is not None
            and (e.status >= 500 or e.status in (408, 429))
        ),
        before_sleep=before_sleep_log(_logger, logging.WARN),
        stop=stop_after_attempt(RETRIES),
        wait=wait_fixed(WAIT_SECONDS),
        reraise=True,
    )(func)


class GeoCatalogClient:
    """Client for interacting with a Spatio GeoCatalog."""

    def __init__(
        self,
        geocatalog_url: str,
    ):
        self.geocatalog_url = geocatalog_url
        self._session = ClientSession()
        self._access_token: AccessToken | None = None

    async def close(self):
        """Close the client session."""

        if not self._session.closed:
            await self._session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def _get_spatio_bearer_token(self) -> Dict[str, Any]:
        """Get a bearer token for the Spatio API."""

        _logger.debug("Spatio bearer token requested")
        if self._access_token is None or datetime.fromtimestamp(
            self._access_token.expires_on
        ) < datetime.now() + timedelta(minutes=5):
            _logger.debug("Creating new Spatio bearer token")
            async with DefaultAzureCredential(
                authority=get_cloud().endpoints.active_directory,
            ) as credential:
                cloud = get_cloud()
                if cloud.scopes is None or cloud.scopes.geocatalog_resource_id is None:
                    raise ValueError("No scope found for geocatalog")
                scope = cloud.scopes.geocatalog_resource_id
                self._access_token = await credential.get_token(
                    scope,
                )

        return {"Authorization": f"Bearer {self._access_token.token}"}

    @retry_transient_errors
    async def _spatio_post(
        self,
        url: str,
        json: Dict,
    ) -> Dict[str, Any] | List[Dict[str, Any]]:
        """POST to a Spatio API endpoint."""

        _logger.debug(f"POST to {url}")

        async with self._session.post(
            url=url,
            json=json,
            headers=await self._get_spatio_bearer_token(),
            params=API_VERSION,
        ) as response:
            response.raise_for_status()
            return await response.json()

    @retry_transient_errors
    async def _spatio_get(
        self,
        url: str,
    ) -> Dict[str, Any] | List[Dict[str, Any]]:
        """GET to a Spatio API endpoint."""

        _logger.debug(f"GET from {url}")

        async with self._session.get(
            url=url,
            headers=await self._get_spatio_bearer_token(),
            params=API_VERSION,
        ) as response:
            response.raise_for_status()
            return await response.json()

    @retry_transient_errors
    async def _spatio_put(
        self,
        url: str,
        json: Dict,
    ) -> Dict[str, Any] | List[Dict[str, Any]]:
        """PUT to a Spatio API endpoint."""

        _logger.debug(f"PUT to {url}")

        async with self._session.put(
            url=url,
            json=json,
            headers=await self._get_spatio_bearer_token(),
            params=API_VERSION,
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def bulk_ingest_stac_collection(
        self,
        collection_id: str,
        collection_url: str,
    ) -> Tuple[str, str]:
        """Bulk ingest a static collection into a GeoCatalog."""

        # Extract the container URL from the collection URL
        parsed_url = urlparse(collection_url)
        scheme = parsed_url.scheme
        domain = parsed_url.netloc
        first_path_segment = parsed_url.path.split("/")[1]

        container_url = f"{scheme}://{domain}/{first_path_segment}"
        _logger.info(f"Container URL: {container_url}")
        await self.create_or_update_ingestion_source(container_url=container_url)

        ingestion_endpoint = urljoin(
            self.geocatalog_url,
            f"/api/collections/{collection_id}/ingestions",
        )
        _logger.debug(
            f"Creating ingestion for {collection_url} into collection {collection_id} at {self.geocatalog_url}"  # noqa
        )
        _logger.debug(f"Using ingestion endpoint {ingestion_endpoint}")
        ingestion_response = await self._spatio_post(
            url=ingestion_endpoint,
            json={
                "importType": "StaticCatalog",
                "sourceCatalogUrl": collection_url,
                "skipExistingItems": False,
                "keepOriginalAssets": False,
            },
        )
        if not isinstance(ingestion_response, dict):
            raise ValueError("Ingestion response returned an unexpected response")
        ingestion_id = ingestion_response["ingestionId"]
        _logger.debug(f"Ingestion created with ID {ingestion_id}")

        ingestion_run_endpoint = f"{ingestion_endpoint}/{ingestion_id}/runs"
        _logger.debug(f"Running ingestion with ID {ingestion_id}")
        _logger.debug(f"Using ingestion run endpoint {ingestion_run_endpoint}")
        run_response = await self._spatio_post(
            url=ingestion_run_endpoint,
            json={},
        )
        if not isinstance(run_response, dict):
            raise ValueError("Run response returned an unexpected response")
        run_id = run_response["operation"]["operationId"]
        _logger.debug(f"Ingestion {ingestion_id} running with ID {run_id}")

        return ingestion_id, run_id

    async def get_ingestion_sources(
        self,
    ) -> Dict[str, Dict[str, Any]]:
        """Get a list of ingestion sources."""

        _logger.info(f"Getting ingestion sources for {self.geocatalog_url}")

        # Add the ingestion API endpoint to the catalog URL
        ingestion_sources_list_endpoint = urljoin(
            self.geocatalog_url, "/api/ingestion-sources"
        )

        # Get the list of ingestion sources in the catalog
        ingestion_sources_data = await self._spatio_get(
            ingestion_sources_list_endpoint,
        )

        if not isinstance(ingestion_sources_data, list):
            raise ValueError("Ingestion sources returned an unexpected response")

        ingestion_sources = {}
        for ing_source in ingestion_sources_data:
            ingestion_source_id = ing_source["id"]
            # Add the ingestion source ID to the endpoint
            get_ingestion_source_endpoint = (
                ingestion_sources_list_endpoint + f"/{ingestion_source_id}"
            )
            # Get the ingestion source details for the ID
            ingestion_source = await self._spatio_get(get_ingestion_source_endpoint)
            if not isinstance(ingestion_source, dict):
                raise ValueError("Ingestion source returned an unexpected response")
            source_type = ingestion_source["sourceType"]
            connection_info = ingestion_source["connectionInfo"]
            container_url = ingestion_source["connectionInfo"]["containerUrl"]
            sas_expiration = ingestion_source["connectionInfo"]["expiration"]

            if source_type == "SasToken":
                if "expiration" in connection_info:
                    ingestion_sources[container_url] = {
                        "id": ingestion_source_id,
                        "expiration": sas_expiration,
                    }
                else:
                    _logger.info(
                        f"The Container URL {container_url} has a policy based SAS Token."  # noqa E501
                    )

        _logger.info(f"Found {len(ingestion_sources)} ingestion sources")

        return ingestion_sources

    async def create_ingestion_source(
        self,
        container_url: str,
        sas_token: str,
    ) -> Dict[str, Any]:
        """Create an ingestion source for a container."""

        _logger.info(
            f"Creating ingestion source for {container_url} at {self.geocatalog_url}"
        )

        endpoint = urljoin(self.geocatalog_url, "/api/ingestion-sources")

        json = {
            "sourceType": "SasToken",
            "connectionInfo": {
                "containerUrl": container_url,
                "sasToken": sas_token,
            },
        }

        ingestion_source = await self._spatio_post(
            url=endpoint,
            json=json,
        )
        if not isinstance(ingestion_source, dict):
            raise ValueError("Ingestion source returned an unexpected response")

        return ingestion_source

    async def update_ingestion_source(
        self,
        id: str,
        container_url: str,
        new_sas_token: str,
    ) -> None:
        """Update an ingestion source for a container."""

        _logger.info(f"Updating ingestion source {id} at {self.geocatalog_url}")

        endpoint = urljoin(self.geocatalog_url, f"/api/ingestion-sources/{id}")

        json = {
            "id": id,
            "sourceType": "SasToken",
            "connectionInfo": {
                "containerUrl": container_url,
                "sasToken": new_sas_token,
            },
        }

        await self._spatio_put(
            url=endpoint,
            json=json,
        )

    async def create_or_update_ingestion_source(
        self,
        container_url: str,
    ) -> None:
        """Create or update an ingestion source for a container."""

        min_sas_token_expiration = int(os.getenv("MIN_SAS_TOKEN_EXPIRATION_HOURS", 12))
        default_sas_token_expiration = int(
            os.getenv("DEFAULT_SAS_TOKEN_EXPIRATION_HOURS", 24)
        )

        ingestion_sources = await self.get_ingestion_sources()

        parsed_url = urlparse(container_url)
        account_name = parsed_url.netloc.split(".")[0]
        container_name = parsed_url.path.lstrip("/")

        async with StorageClient(
            account_name=account_name,
            container_name=container_name,
        ) as storage_client:
            ingestion_source = ingestion_sources.get(container_url)
            if ingestion_source is None:
                # There is no ingestion source for the container, let's create one

                _logger.info(
                    f"No ingestion source found for {container_url} at {self.geocatalog_url}"  # noqa E501
                )

                sas_token = await storage_client.get_sas_token(
                    expiration=datetime.now(UTC)
                    + timedelta(hours=default_sas_token_expiration),  # noqa E501
                    read=True,
                    list=True,
                )

                await self.create_ingestion_source(
                    container_url=container_url,
                    sas_token=sas_token,
                )
            else:
                # There is an ingestion source for the container, check if the
                # SAS token is still valid
                _logger.info(
                    f"Found ingestion source for {container_url} at {self.geocatalog_url} with ID {ingestion_source['id']}"  # noqa E501
                )
                sas_token_expiration = datetime.fromisoformat(
                    ingestion_source["expiration"]
                )
                if (
                    datetime.now(UTC) + timedelta(hours=min_sas_token_expiration)
                    >= sas_token_expiration
                ):
                    # The SAS token is expired or about to expire, let's update it
                    _logger.info(
                        f"The SAS token with ID {ingestion_source['id']} is expired or about to expire"  # noqa E501
                    )
                    sas_token = await storage_client.get_sas_token(
                        expiration=datetime.now(UTC)
                        + timedelta(hours=default_sas_token_expiration),
                        read=True,
                        list=True,
                    )

                    await self.update_ingestion_source(
                        id=ingestion_source["id"],
                        container_url=container_url,
                        new_sas_token=sas_token,
                    )
