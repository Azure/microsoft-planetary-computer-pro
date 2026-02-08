"""
Configuration loader for the register-arcgis-enterprise toolset.

Supports loading from:
  - YAML config file (with ${ENV_VAR} substitution)
  - .env file
  - Environment variables
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class GeoCatalogConfig:
    """MPC Pro GeoCatalog connection settings."""
    endpoint: str = ""


@dataclass
class ArcGISConfig:
    """ArcGIS Enterprise connection settings."""
    portal_url: str = ""
    username: str = ""
    password: str = ""
    verify_cert: bool = True
    server_role: str = "IMAGE_SERVER"


@dataclass
class StorageCredentialConfig:
    """Credentials that ArcGIS Server will use to access blob storage."""
    credential_type: str = "service_principal"
    # Whether to create a new service principal (True) or use existing (False)
    create_service_principal: bool = True
    # Display name for the new service principal (if creating)
    sp_display_name: str = "ArcGIS-Server-GeocatalogReader"
    # Azure subscription for role assignments (auto-detected if empty)
    subscription_id: str = ""
    # Service Principal
    tenant_id: str = ""
    client_id: str = ""
    client_secret: str = ""
    # Access Key
    account_key: str = ""
    # Managed Identity
    managed_identity_client_id: str = ""
    # SAS
    sas_token: str = ""


@dataclass
class Config:
    """Top-level configuration container."""
    geocatalog: GeoCatalogConfig = field(default_factory=GeoCatalogConfig)
    arcgis: ArcGISConfig = field(default_factory=ArcGISConfig)
    storage_credentials: StorageCredentialConfig = field(
        default_factory=StorageCredentialConfig
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ENV_PATTERN = re.compile(r"\$\{(\w+)\}")


def _resolve_env_vars(value: str) -> str:
    """Replace ``${VAR}`` placeholders with environment variable values."""
    def _replacer(match: re.Match) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))
    return _ENV_PATTERN.sub(_replacer, value)


def _walk_and_resolve(obj):
    """Recursively resolve env vars in a nested dict/list structure."""
    if isinstance(obj, dict):
        return {k: _walk_and_resolve(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_walk_and_resolve(v) for v in obj]
    if isinstance(obj, str):
        return _resolve_env_vars(obj)
    return obj


def _build_dataclass(cls, data: dict):
    """Build a dataclass from a dict, ignoring unknown keys."""
    if data is None:
        return cls()
    known_fields = {f.name for f in cls.__dataclass_fields__.values()}
    filtered = {k: v for k, v in data.items() if k in known_fields}
    return cls(**filtered)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_config(
    config_path: Optional[str] = None,
    env_path: Optional[str] = None,
) -> Config:
    """Load configuration from YAML and/or .env file.

    Priority (highest to lowest):
      1. Environment variables
      2. .env file
      3. YAML config file
    """
    # Load .env file if provided (or auto-detect)
    if env_path:
        load_dotenv(env_path, override=False)
    else:
        # Try to find a .env next to the script
        default_env = Path(__file__).resolve().parent.parent / ".env"
        if default_env.exists():
            load_dotenv(default_env, override=False)

    if config_path and Path(config_path).exists():
        return _load_from_yaml(config_path)

    return _load_from_env()


def _load_from_yaml(path: str) -> Config:
    """Parse YAML config with env-var substitution."""
    with open(path, "r") as f:
        raw = yaml.safe_load(f) or {}

    resolved = _walk_and_resolve(raw)

    return Config(
        geocatalog=_build_dataclass(GeoCatalogConfig, resolved.get("geocatalog")),
        arcgis=_build_dataclass(ArcGISConfig, resolved.get("arcgis")),
        storage_credentials=_build_dataclass(
            StorageCredentialConfig, resolved.get("storage_credentials")
        ),
    )


def _load_from_env() -> Config:
    """Build config entirely from environment variables / .env."""
    geocatalog = GeoCatalogConfig(
        endpoint=os.environ.get("GEOCATALOG_ENDPOINT", ""),
    )

    verify_raw = os.environ.get("ARCGIS_VERIFY_CERT", "true")
    arcgis = ArcGISConfig(
        portal_url=os.environ.get("ARCGIS_PORTAL_URL", ""),
        username=os.environ.get("ARCGIS_USERNAME", ""),
        password=os.environ.get("ARCGIS_PASSWORD", ""),
        verify_cert=verify_raw.lower() not in ("false", "0", "no"),
        server_role=os.environ.get("ARCGIS_SERVER_ROLE", "IMAGE_SERVER"),
    )

    cred_type = os.environ.get("STORAGE_CREDENTIAL_TYPE", "service_principal")
    create_sp_raw = os.environ.get("CREATE_SERVICE_PRINCIPAL", "true")
    storage = StorageCredentialConfig(
        credential_type=cred_type,
        create_service_principal=create_sp_raw.lower() not in ("false", "0", "no"),
        sp_display_name=os.environ.get("SP_DISPLAY_NAME", "ArcGIS-Server-GeocatalogReader"),
        subscription_id=os.environ.get("AZURE_SUBSCRIPTION_ID", ""),
        tenant_id=os.environ.get("AZURE_TENANT_ID", ""),
        client_id=os.environ.get("AZURE_CLIENT_ID", ""),
        client_secret=os.environ.get("AZURE_CLIENT_SECRET", ""),
        account_key=os.environ.get("STORAGE_ACCOUNT_KEY", ""),
        managed_identity_client_id=os.environ.get("MANAGED_IDENTITY_CLIENT_ID", ""),
        sas_token=os.environ.get("SAS_TOKEN", ""),
    )

    return Config(
        geocatalog=geocatalog,
        arcgis=arcgis,
        storage_credentials=storage,
    )
