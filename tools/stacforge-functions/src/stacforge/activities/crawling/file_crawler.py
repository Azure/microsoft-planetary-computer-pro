import logging
from typing import List

from azure.functions import Context

from stacforge import blueprint as bp
from stacforge.activities.crawling import (
    CrawlingError,
    FileCrawlingActivityInput,
)
from stacforge.clients import StorageClient
from stacforge.logging import LOGGER_NAME, logging_context

from . import FILE_CRAWLER_ACTIVITY_NAME as ACTIVITY_NAME

_logger = logging.getLogger(LOGGER_NAME)


@bp.activity_trigger(activity=ACTIVITY_NAME, input_name="input")
async def file_crawler(
    input: FileCrawlingActivityInput,
    context: Context,
) -> List[str]:
    """Crawl a directory and return a list of files found."""

    return await _file_crawler(input, context)


async def _file_crawler(
    input: FileCrawlingActivityInput,
    context: Context,
) -> List[str]:
    """Crawl a directory and return a list of files found."""

    with logging_context(
        orchestration_id=input.orchestration_id,
        level=logging.DEBUG,
        context={
            "orchestration_name": input.orchestration_name,
            "activity_name": ACTIVITY_NAME,
            "activity_id": context.invocation_id,
        },
    ):
        _logger.info(
            f"Starting file crawling for container {input.container_name} at {input.storage_account_name}"  # noqa: E501
        )
        _logger.info(
            f'Pattern is "{input.pattern}"'
            if input.pattern is not None
            else "No pattern"
        )

        try:
            async with StorageClient(
                account_name=input.storage_account_name,
                container_name=input.container_name,
                read_only=True,
            ) as storage_client:
                files = await storage_client.list_blobs(
                    pattern=input.pattern,
                )

                _logger.info(f"Found {len(files)} files")
                return files
        except Exception as e:
            _logger.error(
                f"Error crawling files at storage account {input.storage_account_name}, container {input.container_name}",  # noqa: E501
                exc_info=e,
            )
            raise CrawlingError("Error crawling files")
