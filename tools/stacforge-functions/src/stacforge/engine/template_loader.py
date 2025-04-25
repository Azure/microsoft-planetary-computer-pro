import logging
from typing import Union

from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobClient
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_fixed,
)

from stacforge.logging import LOGGER_NAME
from stacforge.utils import get_cloud

RETRIES = 3
WAIT_SECONDS = 1


_logger = logging.getLogger(LOGGER_NAME)


@retry(
    retry=retry_if_exception(
        lambda e: isinstance(e, HttpResponseError)
        and e.status_code is not None
        and (e.status_code >= 500 or e.status_code in (408, 429))
    ),
    stop=stop_after_attempt(RETRIES),
    wait=wait_fixed(WAIT_SECONDS),
    reraise=True,
)
def load_template_from_storage(
    blob_url: str,
) -> Union[str, None]:
    """Load a template from a blob storage URL.
    It returns the template as a string or None if the blob does not exist."""

    try:
        _logger.debug(f"Loading template from {blob_url}")
        with BlobClient.from_blob_url(
            blob_url=blob_url,
            credential=DefaultAzureCredential(
                authority=get_cloud().endpoints.active_directory,
            ),
        ) as client:
            blob = client.download_blob()
            blob_data = blob.readall()
            result = blob_data.decode("utf-8")

            _logger.debug(f"Template loaded from {blob_url}")
            return result
    except ResourceNotFoundError:
        # Return None if the template does not exist
        _logger.warning(f"Template not found at {blob_url}")
        return None
