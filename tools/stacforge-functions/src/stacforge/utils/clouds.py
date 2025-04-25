import json
import os
from dataclasses import dataclass
from typing import Any, Optional

from dataclasses_json import LetterCase, dataclass_json


@dataclass_json(letter_case=LetterCase.CAMEL)  # type: ignore
@dataclass
class Endpoints:
    """Azure cloud endpoints."""

    active_directory: Optional[str] = None
    active_directory_data_lake_resource_id: Optional[str] = None
    active_directory_graph_resource_id: Optional[str] = None
    active_directory_resource_id: Optional[str] = None
    app_insights_resource_id: Optional[str] = None
    app_insights_telemetry_channel_resource_id: Optional[str] = None
    attestation_resource_id: Optional[str] = None
    azmirror_storage_account_resource_id: Optional[str] = None
    batch_resource_id: Optional[str] = None
    gallery: Optional[str] = None
    log_analytics_resource_id: Optional[str] = None
    management: Optional[str] = None
    media_resource_id: Optional[str] = None
    microsoft_graph_resource_id: Optional[str] = None
    ossrdbms_resource_id: Optional[str] = None
    portal: Optional[str] = None
    resource_manager: Optional[str] = None
    sql_management: Optional[str] = None
    synapse_analytics_resource_id: Optional[str] = None
    vm_image_alias_doc: Optional[str] = None


@dataclass_json(letter_case=LetterCase.CAMEL)  # type: ignore
@dataclass
class Suffixes:
    """Azure cloud suffixes."""

    acr_login_server_endpoint: Optional[str] = None
    attestation_endpoint: Optional[str] = None
    azure_datalake_analytics_catalog_and_job_endpoint: Optional[str] = None
    azure_datalake_store_file_system_endpoint: Optional[str] = None
    keyvault_dns: Optional[str] = None
    mariadb_server_endpoint: Optional[str] = None
    mhsm_dns: Optional[str] = None
    mysql_server_endpoint: Optional[str] = None
    postgresql_server_endpoint: Optional[str] = None
    sql_server_hostname: Optional[str] = None
    storage_endpoint: Optional[str] = None
    storage_sync_endpoint: Optional[str] = None
    synapse_analytics_endpoint: Optional[str] = None


@dataclass_json(letter_case=LetterCase.CAMEL)  # type: ignore
@dataclass
class Scopes:
    """Azure cloud scopes."""

    storage_account_resource_id: Optional[str] = None
    geocatalog_resource_id: Optional[str] = None


@dataclass_json(letter_case=LetterCase.CAMEL)  # type: ignore
@dataclass
class Cloud:
    """Azure cloud configuration."""

    name: str
    endpoints: Endpoints
    suffixes: Suffixes
    scopes: Optional[Scopes] = None


# Load the cloud configurations from the clouds.json file
# clouds.json has been created by running the following command:
# az cloud list --query "[].{name:name,suffixes:suffixes,endpoints:endpoints}"
# and then manually adding the scopes for each cloud
clouds: dict[str, Cloud] = {}
with open(os.path.join(os.path.dirname(__file__), "clouds.json"), "r") as file:
    clouds_dict: list[dict[str, Any]] = json.load(file)
    for cloud in clouds_dict:
        clouds[cloud["name"]] = Cloud.from_dict(cloud)  # type: ignore


def get_cloud(cloud_name: str | None = None) -> Cloud:
    """Returns the cloud configuration for the given cloud name.
    If no cloud name is provided, the cloud is determined from
    the AZURE_CLOUD environment variable."""

    cloud = cloud_name or os.getenv("AZURE_CLOUD", "AzureCloud")
    if cloud not in clouds:
        raise ValueError(f"Cloud {cloud} is not supported.")
    return clouds[cloud]
