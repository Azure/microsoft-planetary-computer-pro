import logging
import os
from typing import Any, Dict, Generator, List

import azure.durable_functions as df  # type: ignore
from azure.durable_functions.models.Task import TaskBase  # type: ignore

from stacforge import blueprint as bp
from stacforge.activities.crawling import (
    FILE_CRAWLER_ACTIVITY_NAME,
    INDEX_CRAWLER_ACTIVITY_NAME,
    CrawlingActivityInput,
    CrawlingType,
    FileCrawlingActivityInput,
    IndexCrawlingActivityInput,
)
from stacforge.activities.transformation import (
    CreateCollectionActivityInput,
    GeoTemplateTransformationActivityInput,
)
from stacforge.logging import LOGGER_NAME, logging_context
from stacforge.orchestrations import StaticCatalogIngestionOrchestrationInfo

from . import GEOTEMPLATE_BULK_TRANSFORM_ORCHESTRATION_NAME as ORCHESTRATION_NAME

_logger = logging.getLogger(LOGGER_NAME)

GEOCATALOG_URL = os.getenv("GEOCATALOG_URL")


@bp.orchestration_trigger(orchestration=ORCHESTRATION_NAME, context_name="context")
def geotemplate_bulk_transform(
    context: df.DurableOrchestrationContext,
) -> Generator[TaskBase, Any, dict[Any, Any] | dict[str, str] | dict[str, Any]]:
    """Orchestration to bulk transform scenes to STAC items
    and ingest them into a GeoCatalog."""

    return _geotemplate_bulk_transform(context)


def _geotemplate_bulk_transform(
    context: df.DurableOrchestrationContext,
) -> Generator[TaskBase, Any, dict[Any, Any] | dict[str, str] | dict[str, Any]]:
    """Orchestration to bulk transform scenes to STAC items
    and ingest them into a GeoCatalog."""

    orchestration_id = context.instance_id

    with logging_context(
        orchestration_id=orchestration_id,
        level=logging.DEBUG,
        context={
            "orchestration_name": ORCHESTRATION_NAME,
        },
    ):
        try:

            def log_info(msg: str) -> None:
                """Log an info message if not replaying."""

                if not context.is_replaying:
                    _logger.info(msg)

            def log_warn(msg: str) -> None:
                """Log a warning message if not replaying."""

                if not context.is_replaying:
                    _logger.warning(msg)

            context.set_custom_status("Initializing")

            log_info(
                f"Stating orchestration geotemplate_transform with ID {context.instance_id}"  # noqa: E501
            )

            # Get the orchestration input
            log_info("Getting orchestration input")
            input = context.get_input()
            if input is None:
                raise ValueError("No input provided")

            orchestration_info = StaticCatalogIngestionOrchestrationInfo.from_dict(
                input
            )
            orchestration_info.check_crawling_options()

            crawler_name: str
            crawler_input: CrawlingActivityInput
            if orchestration_info.crawling_type == CrawlingType.FILE:
                crawler_name = FILE_CRAWLER_ACTIVITY_NAME
                crawler_input = FileCrawlingActivityInput(
                    storage_account_name=orchestration_info.source_storage_account_name,
                    container_name=orchestration_info.source_container_name,
                    pattern=orchestration_info.pattern,
                    orchestration_id=orchestration_id,
                    orchestration_name=ORCHESTRATION_NAME,
                )
            elif orchestration_info.crawling_type == CrawlingType.INDEX:
                crawler_name = INDEX_CRAWLER_ACTIVITY_NAME
                assert orchestration_info.index_file_path is not None
                crawler_input = IndexCrawlingActivityInput(
                    storage_account_name=orchestration_info.source_storage_account_name,
                    container_name=orchestration_info.source_container_name,
                    index_file=orchestration_info.index_file_path,
                    is_ndjson=orchestration_info.index_file_is_ndjson,
                    ignore_lines_starting_with=orchestration_info.index_file_ignore_lines_starting_with,  # noqa: E501
                    orchestration_id=orchestration_id,
                    orchestration_name=ORCHESTRATION_NAME,
                )
            else:
                raise NotImplementedError(
                    f"Crawling type {orchestration_info.crawling_type} is not implemented"  # noqa: E501
                )

            # Get the list of scenes
            context.set_custom_status("Crawling")
            log_info(f"Crawling scenes with {crawler_name}")
            scenes: List[str] | List[Dict[str, Any]] = yield context.call_activity(
                crawler_name,
                crawler_input,
            )
            if len(scenes) == 0:
                log_warn("No scenes found!")
                context.set_custom_status("Finished")
                return {}
            log_info(f"Found {len(scenes)} scenes")

            # Transform all scenes to STAC items and store them in a storage account
            context.set_custom_status("Transforming")
            tasks = []
            log_info(f"Transforming {len(scenes)} scenes to STAC items")
            for scene in scenes:
                tasks.append(
                    context.call_activity(
                        "geotemplate_transform",
                        GeoTemplateTransformationActivityInput(
                            scene=scene,
                            template_url=orchestration_info.template_url,
                            items_path=f"{context.instance_id}/items",
                            validate=orchestration_info.validate,
                            orchestration_id=orchestration_id,
                            orchestration_name=ORCHESTRATION_NAME,
                        ),
                    )
                )
            # Get the result of the transforming tasks
            responses: list[bool] = yield context.task_all(tasks)
            failed_count = responses.count(False)
            success_count = responses.count(True)
            if failed_count > 0:
                log_warn(f"{failed_count} items failed to transform")

            # If no items were transformed, finish the orchestration
            if success_count == 0:
                context.set_custom_status(
                    "Finished" if failed_count == 0 else "FinishedWithErrors"
                )
                return {
                    "warning": "No scenes transformed",
                }

            log_info(f"Transformed {success_count} scenes to STAC items")

            # Create a temporary collection from the STAC items
            # and store it in a storage account
            context.set_custom_status("CreatingCollection")
            log_info(f"Creating a collection for {success_count} STAC items")
            collection_url = yield context.call_activity(
                "create_collection",
                CreateCollectionActivityInput(
                    base_dir=context.instance_id,
                    orchestration_id=orchestration_id,
                    orchestration_name=ORCHESTRATION_NAME,
                ),
            )
            log_info(f"Collection created at {collection_url}")

            context.set_custom_status(
                "Finished" if failed_count == 0 else "FinishedWithErrors"
            )
            return {
                "collectionUrl": collection_url,
                "totalItems": len(scenes),
                "successCount": success_count,
                "failedCount": failed_count,
            }
        except Exception as e:
            _logger.error(
                f"Error running {ORCHESTRATION_NAME} with ID {orchestration_id}",
                exc_info=e,
            )
            context.set_custom_status("Failed")
            return {
                "error": str(e).split("\n")[0].rstrip(),
            }
