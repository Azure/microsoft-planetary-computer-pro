import json
import logging

from azure.functions import Context

from stacforge import blueprint as bp
from stacforge.activities.transformation import (
    CreateCollectionActivityInput,
    TransformationError,
)
from stacforge.clients import StorageClient
from stacforge.logging import LOGGER_NAME, logging_context

from . import CREATE_COLLECTION_ACTIVITY_NAME as ACTIVITY_NAME

_logger = logging.getLogger(LOGGER_NAME)


@bp.activity_trigger(activity=ACTIVITY_NAME, input_name="input")
async def create_collection(
    input: CreateCollectionActivityInput,
    context: Context,
) -> str:
    """Create a STAC collection from a list of STAC item URLs."""

    return await _create_collection(input, context)


async def _create_collection(
    input: CreateCollectionActivityInput,
    context: Context,
) -> str:
    """Create a STAC collection from a list of STAC item URLs."""

    with logging_context(
        orchestration_id=input.orchestration_id,
        level=logging.DEBUG,
        context={
            "orchestration_name": input.orchestration_name,
            "activity_name": ACTIVITY_NAME,
            "activity_id": context.invocation_id,
        },
    ):
        async with StorageClient.get_export_storage_client() as storage_client:
            # Get the list of STAC items
            items = await storage_client.list_blobs(
                prefix=f"{input.base_dir}/items",
                pattern="*.json",
            )

            _logger.info(f"Creating collection for {len(items)} items")

            # This must be a valid STAC Collection
            # https://github.com/radiantearth/stac-spec/blob/master/collection-spec/collection-spec.md
            collection = {
                "stac_version": "1.0.0",
                "type": "Collection",
                "id": "temporary_collection",
                "title": "Temporary collection",
                "description": "Temporary collection for bulk import",
                "license": "other",
                "extent": {
                    "spatial": {"bbox": [[-180, -90, 180, 90]]},
                    "temporal": {"interval": [[None, None]]},
                },
                "links": [
                    {
                        "rel": "item",
                        "href": item_url,
                        "type": "application/json",
                    }
                    for item_url in items
                ],
            }

            collection_path = f"{input.base_dir}/collection.json"

            try:
                # Store the STAC collection in the storage account
                _logger.debug("Uploading collection")
                blob_url = await storage_client.upload_blob(
                    name=collection_path,
                    data=json.dumps(collection),
                )

                _logger.info(f"Collection uploaded to {blob_url}")
                return blob_url
            except Exception as e:
                _logger.error(
                    f"Error storing collection to {collection_path}",
                    exc_info=e,
                )
                raise TransformationError("Error creating collection")
