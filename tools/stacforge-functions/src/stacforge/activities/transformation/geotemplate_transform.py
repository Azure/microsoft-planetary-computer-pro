import json
import logging

from azure.functions import Context

from stacforge import blueprint as bp
from stacforge.activities.transformation import GeoTemplateTransformationActivityInput
from stacforge.clients import StorageClient
from stacforge.engine import Environment
from stacforge.logging import LOGGER_NAME, logging_context
from stacforge.utils import Timer

from . import GEOTEMPLATE_TRANSFORM_ACTIVITY_NAME as ACTIVITY_NAME

_logger = logging.getLogger(LOGGER_NAME)

_environment = Environment()


@bp.activity_trigger(activity=ACTIVITY_NAME, input_name="input")
async def geotemplate_transform(
    input: GeoTemplateTransformationActivityInput,
    context: Context,
) -> bool:
    """Transform a scene to a STAC item using a GeoTemplate."""

    return await _geotemplate_transform(input, context)


async def _geotemplate_transform(
    input: GeoTemplateTransformationActivityInput,
    context: Context,
) -> bool:
    """Transform a scene to a STAC item using a GeoTemplate."""

    with logging_context(
        orchestration_id=input.orchestration_id,
        context={
            "orchestration_name": input.orchestration_name,
            "activity_name": ACTIVITY_NAME,
            "activity_id": context.invocation_id,
            "scene": input.scene,
        },
        level=logging.DEBUG,
    ):
        try:
            _logger.info(f"Received scene {input.scene}")

            _logger.info(f"Retrieving template from {input.template_url}")
            template = _environment.get_geotemplate_from_storage(input.template_url)

            # Convert the scene to a STAC item
            try:
                _logger.info(f"Converting {input.scene} scene to STAC item")
                with Timer() as timer:
                    stac_item = await template.render_stac(input.scene, input.validate)
            except Exception as e:
                _logger.error(
                    f"Error converting scene {input.scene} to STAC item", exc_info=e
                )
                raise
            _logger.info(f"Conversion took {timer() * 1_000:.6f} ms")
            stac_dict = stac_item.to_dict()

            # Store the STAC item in the storage account
            item_path = f"{input.items_path}/{context.invocation_id}.json"
            try:
                _logger.debug("Uploading STAC item")
                async with StorageClient.get_export_storage_client() as storage_client:
                    blob_url = await storage_client.upload_blob(
                        name=item_path,
                        data=json.dumps(stac_dict),
                    )
                    _logger.info(f"STAC item uploaded to {blob_url}")

                    return True
            except Exception as e:
                _logger.error(f"Error storing STAC item to {item_path}", exc_info=e)
                raise
        except Exception:
            _logger.warning(f"Transformation failed for scene {input.scene}")
            return False
