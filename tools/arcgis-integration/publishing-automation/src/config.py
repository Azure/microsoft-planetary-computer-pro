"""
Configuration loader for the ArcGIS Publishing Automation pipeline.

Loads, validates, and provides typed access to YAML configuration.
Supports environment variable interpolation using ${ENV_VAR_NAME} syntax.
"""

import os
import re
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

# Pattern for environment variable references: ${VAR_NAME}
_ENV_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")


def _resolve_env_vars(value: Any) -> Any:
    """Recursively resolve ${ENV_VAR} references in strings."""
    if isinstance(value, str):
        def _replace(match: re.Match) -> str:
            var_name = match.group(1)
            env_value = os.environ.get(var_name)
            if env_value is None:
                logger.warning("Environment variable '%s' is not set", var_name)
                return match.group(0)  # Leave unresolved
            return env_value
        return _ENV_VAR_PATTERN.sub(_replace, value)
    elif isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_resolve_env_vars(item) for item in value]
    return value


@dataclass
class GeoCatalogConfig:
    """MPC Pro GeoCatalog connection settings."""
    endpoint: str
    api_version: str = "2025-04-30-preview"


@dataclass
class StacQueryConfig:
    """STAC query parameters."""
    collections: list[str]
    bbox: Optional[list[float]] = None
    datetime: Optional[str] = None
    filter: Optional[dict] = None
    filter_lang: Optional[str] = None
    limit: int = 100


@dataclass
class ImageCollectionConfig:
    """ArcGIS Image Collection settings."""
    name: str
    description: str = ""
    coordinate_system: int = 4326
    raster_type_name: str = "Raster Dataset"
    create_if_missing: bool = True
    source_asset_key: str = "visual"


@dataclass
class ArcGISEnterpriseConfig:
    """ArcGIS Enterprise connection settings."""
    portal_url: str
    image_server_url: str = ""
    auth_method: str = "username_password"
    username: str = ""
    password: str = ""
    client_id: str = ""
    client_secret: str = ""
    verify_cert: bool = True


@dataclass
class CloudStoreConfig:
    """Azure Blob Storage cloud data store settings."""
    store_name: str
    storage_account: str
    container: str


@dataclass
class DeploymentConfig:
    """Deployment and scheduling settings."""
    schedule_cron: str = "0 0 */6 * * *"
    schedule_interval_hours: int = 6
    log_level: str = "INFO"


@dataclass
class PipelineConfig:
    """Top-level configuration for the publishing automation pipeline."""
    geocatalog: GeoCatalogConfig
    stac_query: StacQueryConfig
    image_collection: ImageCollectionConfig
    arcgis_enterprise: ArcGISEnterpriseConfig
    cloud_store: CloudStoreConfig
    deployment: DeploymentConfig = field(default_factory=DeploymentConfig)


class ConfigurationError(Exception):
    """Raised when configuration is invalid or incomplete."""
    pass


def _build_dataclass(cls, data: dict) -> Any:
    """Build a dataclass instance from a dict, ignoring unknown keys."""
    if data is None:
        data = {}
    # Only pass keys that the dataclass accepts
    valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
    filtered = {k: v for k, v in data.items() if k in valid_keys}
    return cls(**filtered)


def load_config(config_path: str | Path) -> PipelineConfig:
    """
    Load and validate configuration from a YAML file.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        A validated PipelineConfig instance.

    Raises:
        ConfigurationError: If required fields are missing or invalid.
        FileNotFoundError: If the config file does not exist.
    """
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ConfigurationError("Configuration file must contain a YAML mapping")

    # Resolve environment variables throughout
    raw = _resolve_env_vars(raw)

    # Validate required top-level sections
    required_sections = ["geocatalog", "stac_query", "image_collection", "arcgis_enterprise", "cloud_store"]
    missing = [s for s in required_sections if s not in raw]
    if missing:
        raise ConfigurationError(f"Missing required configuration sections: {', '.join(missing)}")

    try:
        config = PipelineConfig(
            geocatalog=_build_dataclass(GeoCatalogConfig, raw["geocatalog"]),
            stac_query=_build_dataclass(StacQueryConfig, raw["stac_query"]),
            image_collection=_build_dataclass(ImageCollectionConfig, raw["image_collection"]),
            arcgis_enterprise=_build_dataclass(ArcGISEnterpriseConfig, raw["arcgis_enterprise"]),
            cloud_store=_build_dataclass(CloudStoreConfig, raw["cloud_store"]),
            deployment=_build_dataclass(DeploymentConfig, raw.get("deployment", {})),
        )
    except TypeError as e:
        raise ConfigurationError(f"Invalid configuration: {e}") from e

    # Validate critical fields
    if not config.geocatalog.endpoint:
        raise ConfigurationError("geocatalog.endpoint is required")
    if not config.stac_query.collections:
        raise ConfigurationError("stac_query.collections must contain at least one collection ID")
    if not config.arcgis_enterprise.portal_url:
        raise ConfigurationError("arcgis_enterprise.portal_url is required")
    if not config.cloud_store.store_name:
        raise ConfigurationError("cloud_store.store_name is required")

    logger.info("Configuration loaded from %s", config_path)
    return config
