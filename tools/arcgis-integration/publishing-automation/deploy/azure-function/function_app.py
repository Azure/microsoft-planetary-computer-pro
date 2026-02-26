"""
Azure Function App for ArcGIS Publishing Automation.

Timer-triggered function that discovers new imagery from an MPC Pro
GeoCatalog and publishes it to ArcGIS Enterprise via the ArcGIS API
for Python.

The function runs the same pipeline as the CLI tool, with configuration
loaded from app settings / environment variables or a config file stored
in Azure Blob Storage.
"""

import json
import logging
import os
from datetime import datetime

import azure.functions as func
import yaml

# Add the function app root to the path so we can import the src package
# (deploy.sh copies the shared src/ directory into the function app root)
import sys
sys.path.insert(0, os.path.dirname(__file__))

from src.config import PipelineConfig, load_config, ConfigurationError, _resolve_env_vars, _build_dataclass
from src.config import (
    GeoCatalogConfig,
    StacQueryConfig,
    ImageCollectionConfig,
    ArcGISEnterpriseConfig,
    CloudStoreConfig,
    DeploymentConfig,
)
from src.pipeline import run as run_pipeline

app = func.FunctionApp()

logger = logging.getLogger(__name__)


def _load_config_from_env() -> PipelineConfig:
    """
    Build pipeline configuration from environment variables / app settings.

    Supports two modes:
    1. CONFIG_YAML_PATH: Path to a YAML config file (e.g., in a mounted volume)
    2. CONFIG_JSON: Inline JSON configuration in an app setting
    3. Individual app settings for each config section

    Returns:
        Validated PipelineConfig.
    """
    # Mode 1: YAML file path
    config_path = os.environ.get("CONFIG_YAML_PATH")
    if config_path:
        return load_config(config_path)

    # Mode 2: Inline JSON
    config_json = os.environ.get("CONFIG_JSON")
    if config_json:
        raw = json.loads(config_json)
        raw = _resolve_env_vars(raw)
        return PipelineConfig(
            geocatalog=_build_dataclass(GeoCatalogConfig, raw["geocatalog"]),
            stac_query=_build_dataclass(StacQueryConfig, raw["stac_query"]),
            image_collection=_build_dataclass(ImageCollectionConfig, raw["image_collection"]),
            arcgis_enterprise=_build_dataclass(ArcGISEnterpriseConfig, raw["arcgis_enterprise"]),
            cloud_store=_build_dataclass(CloudStoreConfig, raw["cloud_store"]),
            deployment=_build_dataclass(DeploymentConfig, raw.get("deployment", {})),
        )

    # Mode 3: Individual app settings
    geocatalog_endpoint = os.environ.get("GEOCATALOG_ENDPOINT")
    if not geocatalog_endpoint:
        raise ConfigurationError(
            "No configuration found. Set CONFIG_YAML_PATH, CONFIG_JSON, "
            "or individual app settings (GEOCATALOG_ENDPOINT, etc.)"
        )

    stac_collections = os.environ.get("STAC_COLLECTIONS", "").split(",")
    stac_bbox_str = os.environ.get("STAC_BBOX", "")
    stac_bbox = [float(x) for x in stac_bbox_str.split(",")] if stac_bbox_str else None
    stac_datetime = os.environ.get("STAC_DATETIME")

    return PipelineConfig(
        geocatalog=GeoCatalogConfig(
            endpoint=geocatalog_endpoint,
            api_version=os.environ.get("GEOCATALOG_API_VERSION", "2025-04-30-preview"),
        ),
        stac_query=StacQueryConfig(
            collections=stac_collections,
            bbox=stac_bbox,
            datetime=stac_datetime,
            limit=int(os.environ.get("STAC_LIMIT", "100")),
        ),
        image_collection=ImageCollectionConfig(
            name=os.environ.get("IMAGE_COLLECTION_NAME", ""),
            description=os.environ.get("IMAGE_COLLECTION_DESCRIPTION", ""),
            source_asset_key=os.environ.get("SOURCE_ASSET_KEY", "visual"),
        ),
        arcgis_enterprise=ArcGISEnterpriseConfig(
            portal_url=os.environ.get("ARCGIS_PORTAL_URL", ""),
            image_server_url=os.environ.get("ARCGIS_IMAGE_SERVER_URL", ""),
            auth_method=os.environ.get("ARCGIS_AUTH_METHOD", "username_password"),
            username=os.environ.get("ARCGIS_USERNAME", ""),
            password=os.environ.get("ARCGIS_PASSWORD", ""),
            verify_cert=os.environ.get("ARCGIS_VERIFY_CERT", "true").lower() != "false",
        ),
        cloud_store=CloudStoreConfig(
            store_name=os.environ.get("CLOUD_STORE_NAME", ""),
            storage_account=os.environ.get("CLOUD_STORE_ACCOUNT", ""),
            container=os.environ.get("CLOUD_STORE_CONTAINER", ""),
        ),
    )


@app.timer_trigger(
    schedule=os.environ.get("PIPELINE_SCHEDULE", "0 0 */6 * * *"),
    arg_name="timer",
    run_on_startup=False,
)
def publishing_automation_timer(timer: func.TimerRequest) -> None:
    """
    Timer-triggered function that runs the publishing automation pipeline.

    Executes on the configured schedule (default: every 6 hours).
    """
    invocation_time = datetime.utcnow().isoformat()
    logger.info("Publishing automation triggered at %s", invocation_time)

    if timer.past_due:
        logger.warning("Timer is past due — executing anyway")

    try:
        config = _load_config_from_env()
    except (ConfigurationError, Exception) as e:
        logger.error("Configuration error: %s", e)
        raise

    try:
        result = run_pipeline(config, dry_run=False)
    except Exception as e:
        logger.exception("Pipeline execution failed: %s", e)
        raise

    if not result.success:
        logger.error("Pipeline completed with error: %s", result.error)
        raise RuntimeError(f"Pipeline failed: {result.error}")

    logger.info(
        "Pipeline completed: discovered=%d, new=%d, added=%d, skipped=%d",
        result.items_discovered,
        result.items_new,
        result.items_added,
        result.items_skipped,
    )
