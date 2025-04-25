import json
import logging
from typing import Any, Dict, List

from azure.functions import Context

from stacforge import blueprint as bp
from stacforge.activities.crawling import (
    CrawlingError,
    IndexCrawlingActivityInput,
)
from stacforge.clients import StorageClient
from stacforge.logging import LOGGER_NAME, logging_context

from . import INDEX_CRAWLER_ACTIVITY_NAME as ACTIVITY_NAME

_logger = logging.getLogger(LOGGER_NAME)


@bp.activity_trigger(activity=ACTIVITY_NAME, input_name="input")
async def index_crawler(
    input: IndexCrawlingActivityInput,
    context: Context,
) -> List[str] | List[Dict[str, Any]]:
    """Crawl a directory and return a list of files found."""

    return await _index_crawler(input, context)


async def _index_crawler(
    input: IndexCrawlingActivityInput,
    context: Context,
) -> List[str] | List[Dict[str, Any]]:
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
            f"Starting index crawling with file {input.index_file} at {input.container_name}@{input.storage_account_name}"  # noqa: E501
        )
        _logger.info(f"Index file {'is' if input.is_ndjson else 'is not'} NDJSON")
        if (
            input.ignore_lines_starting_with is not None
            or input.ignore_lines_starting_with != ""
        ):
            _logger.info(
                f"Ignoring lines starting with '{input.ignore_lines_starting_with}'"
            )

        try:
            async with StorageClient(
                account_name=input.storage_account_name,
                container_name=input.container_name,
                read_only=True,
            ) as storage_client:
                bytes = await storage_client.download_blob(
                    name=input.index_file,
                )

                lines = bytes.decode().splitlines()
                _logger.debug(f"The index file has {len(lines)} lines")

                if (
                    input.ignore_lines_starting_with is not None
                    and input.ignore_lines_starting_with != ""
                ):
                    lines = [
                        line
                        for line in lines
                        if not line.startswith(input.ignore_lines_starting_with)
                    ]

                _logger.info(f"Found {len(lines)} files")

                if input.is_ndjson:
                    _logger.debug("Parsing NDJSON")
                    lines = [json.loads(line) for line in lines]

                return lines
        except Exception as e:
            _logger.error(
                f"Error crawling index file {input.index_file} at {input.container_name}@{input.storage_account_name}",  # noqa: E501
                exc_info=e,
            )
            raise CrawlingError("Error crawling index")
