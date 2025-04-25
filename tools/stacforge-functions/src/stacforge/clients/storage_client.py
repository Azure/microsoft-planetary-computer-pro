import fnmatch
import logging
import os
import re
from datetime import UTC, datetime, timedelta
from typing import Optional
from urllib import parse

from azure.core.exceptions import HttpResponseError
from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob import ContainerSasPermissions, generate_container_sas
from azure.storage.blob.aio import BlobServiceClient
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_fixed,
)
from typing_extensions import Self

from stacforge.logging import LOGGER_NAME
from stacforge.utils import get_cloud

_logger = logging.getLogger(LOGGER_NAME)

RETRIES = 3
WAIT_SECONDS = 2


def retry_transient_errors(func):
    """Retry only for transient errors when calling the function."""

    return retry(
        retry=retry_if_exception(
            lambda e: isinstance(e, HttpResponseError)
            and e.status_code is not None
            and (e.status_code >= 500 or e.status_code in (408, 429))
        ),
        before_sleep=before_sleep_log(_logger, logging.WARN),
        stop=stop_after_attempt(RETRIES),
        wait=wait_fixed(WAIT_SECONDS),
        reraise=True,
    )(func)


class StorageClient:
    """Client for interacting with Azure Blob Storage."""

    def __init__(
        self,
        account_name: str,
        container_name: str,
        read_only: bool = False,
    ):
        self._account_name = account_name
        self._container_name = container_name
        self._read_only = read_only
        self._credential = DefaultAzureCredential(
            authority=get_cloud().endpoints.active_directory,
        )
        self._blob_service_client = BlobServiceClient(
            f"https://{self._account_name}.blob.{get_cloud().suffixes.storage_endpoint}",  # noqa: E501
            credential=self._credential,
        )
        self._container_client = self._blob_service_client.get_container_client(
            container_name,
        )

    async def ensure_container(self):
        """Ensure the container exists."""

        if self._read_only:
            raise ValueError("Client is read-only")

        _logger.debug(
            f"Checking if container {self._container_name} exists at {self._account_name}"  # noqa: E501
        )
        if not await self._container_client.exists():
            _logger.info(
                f"Creating container {self._container_name} at {self._account_name}"
            )
            await self._container_client.create_container()

    async def close(self):
        """Close the client."""

        await self._container_client.close()
        await self._blob_service_client.close()
        await self._credential.close()

    async def __aenter__(self):
        if not self._read_only:
            await self.ensure_container()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    @retry_transient_errors
    async def upload_blob(
        self,
        name: str,
        data: bytes | str,
        overwrite: bool = True,
    ) -> str:
        """Upload a blob to the container."""

        if self._read_only:
            raise ValueError("Client is read-only")

        _logger.debug(
            f"Uploading blob {name} to container {self._container_name} at {self._account_name}"  # noqa: E501
        )
        blob = await self._container_client.upload_blob(
            name=name,
            data=data,
            overwrite=overwrite,
        )
        _logger.debug(f"Blob stored at {blob.url}")
        return blob.url

    @retry_transient_errors
    async def list_blobs(
        self,
        prefix: Optional[str] = None,
        pattern: Optional[str] = None,
    ) -> list[str]:
        """List the blobs in the container."""

        _logger.debug(
            f"Listing blobs in container {self._container_name} at {self._account_name} "  # noqa: E501
            f"with {f'prefix {prefix}' if prefix is not None else 'no prefix'} "
            f"and {f'pattern {pattern}' if pattern is not None else 'no pattern'}"
        )
        blobs: list[str] = []
        regex_pattern = None
        if pattern is not None:
            regex_pattern = re.compile(fnmatch.translate(pattern))

        async for blob in self._container_client.list_blobs(name_starts_with=prefix):
            if regex_pattern is None or regex_pattern.match(blob.name):
                blobs.append(f"{self._container_client.url}/{blob.name}")

        _logger.debug(f"Found {len(blobs)} blobs")
        return blobs

    # @retry_transient_errors
    # async def list_directory(
    #     self,
    #     directory: Optional[str] = None,
    #     pattern: Optional[str] = None,
    # ) -> Tuple[list[str], list[str]]:
    #     """List the contents of a directory in the container."""

    #     _logger.debug(
    #         f"Listing directory {directory if directory is not None else '/'} with pattern {pattern if pattern is not None else '*'}"  # noqa: E501
    #     )
    #     files = []
    #     directories = []
    #     regex_pattern = None
    #     if pattern is not None:
    #         regex_pattern = re.compile(fnmatch.translate(pattern))

    #     start_directory = directory or ""
    #     start_directory = (
    #         f"{start_directory}/"
    #         if not start_directory.endswith("/")
    #         else start_directory
    #     )

    #     async for blob in self._container_client.walk_blobs(
    #         name_starts_with=start_directory,
    #         delimiter="/",
    #     ):
    #         if regex_pattern is None or regex_pattern.match(blob.name):
    #             blob_url = (
    #                 f"{self._blob_service_client.url}{self._container_name}/{blob.name}"  # noqa: E501
    #             )
    #             if blob_url.endswith("/"):
    #                 directories.append(blob_url.removesuffix("/"))
    #             else:
    #                 files.append(blob_url)

    #     _logger.debug(f"Found {len(files)} files and {len(directories)} directories")
    #     return directories, files

    @retry_transient_errors
    async def download_blob(
        self,
        name: str,
    ) -> bytes:
        """Download a blob from the container."""

        _logger.debug(
            f"Downloading blob {name} from container {self._container_name} "
            f"at {self._account_name}"
        )
        blob = await self._container_client.download_blob(
            blob=name,
        )
        return await blob.readall()

    async def get_sas_token(
        self,
        expiration: datetime,
        read: bool = False,
        write: bool = False,
        delete: bool = False,
        list: bool = False,
    ) -> str:
        """Generate a SAS token for the container."""

        permissions = ContainerSasPermissions(
            read=read,
            write=write,
            delete=delete,
            list=list,
        )
        permissions_string = "".join(
            [
                "r" if read else "",
                "w" if write else "",
                "d" if delete else "",
                "l" if list else "",
            ]
        )

        # Set the start time to five minutes ago to account for clock skew
        start_time = datetime.now(UTC) + timedelta(minutes=-5)

        _logger.debug(
            f"Generating SAS token for container {self._container_name} "
            f"at {self._account_name} with permissions '{permissions_string}' "
            f"and expiring at {expiration.isoformat()}"
        )

        # Retrieve the user delegation key
        user_delegation_key = await self._blob_service_client.get_user_delegation_key(
            key_start_time=start_time,
            key_expiry_time=expiration,
        )

        sas_token = generate_container_sas(
            account_name=self._account_name,
            container_name=self._container_name,
            user_delegation_key=user_delegation_key,
            permission=permissions,
            expiry=expiration,
            start=start_time,
        )

        return sas_token

    @classmethod
    def get_export_storage_client(cls) -> Self:
        """Get a client for the default export storage account."""

        account_name = os.getenv("DATA_STORAGE_ACCOUNT") or os.getenv(
            "AzureWebJobsStorage__accountName"
        )
        if account_name is None:
            raise ValueError("No storage account configured")
        container_name = os.getenv("DATA_CONTAINER", "collections")

        _logger.debug(
            "Creating export storage client for container "
            f"{container_name} at {account_name}"
        )

        return cls(
            account_name=account_name,
            container_name=container_name,
        )

    @classmethod
    async def download_blob_from_url(
        cls,
        url: str,
    ) -> bytes:
        """Download a blob from a URL."""

        parsed_url = parse.urlparse(url)
        account_name = parsed_url.netloc.split(".")[0]
        container_name = parsed_url.path.split("/")[1]
        blob_name = "/".join(parsed_url.path.split("/")[2:])

        async with cls(
            account_name=account_name,
            container_name=container_name,
            read_only=True,
        ) as client:
            return await client.download_blob(
                name=blob_name,
            )
