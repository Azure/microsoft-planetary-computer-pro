"""
pytest configuration and fixtures for GeoAI SDK tests.
"""

import geopandas as gpd
import pytest
from azure.identity import DefaultAzureCredential
from shapely.geometry import box


@pytest.fixture
def azure_credential():
    """
    Provides an Azure credential for testing.

    :return: Azure credential instance
    :rtype: DefaultAzureCredential
    """
    return DefaultAzureCredential()


@pytest.fixture
def sample_bbox():
    """
    Provides a sample bounding box for testing (Los Angeles area).

    :return: Bounding box [west, south, east, north] in WGS84
    :rtype: list
    """
    return [-118.42, 33.93, -118.40, 33.95]


@pytest.fixture
def sample_datetime():
    """
    Provides a sample datetime range for testing.

    :return: Datetime string in ISO format
    :rtype: str
    """
    return "2020-01-01/2023-12-31"


@pytest.fixture
def mock_geocatalog_uri():
    """
    Provides a mock GeoCatalog URI for testing.

    :return: Mock URI
    :rtype: str
    """
    return "https://test.geocatalog.example.com"


@pytest.fixture
def sample_geometry():
    """
    Provides a sample GeoJSON geometry for testing.

    :return: GeoJSON Polygon geometry
    :rtype: dict
    """
    return box(-118.42, 33.93, -118.40, 33.95).__geo_interface__


@pytest.fixture
def sample_geodataframe():
    """
    Provides a sample GeoDataFrame with multiple AOIs for testing.

    :return: GeoDataFrame with 3 sample AOIs
    :rtype: geopandas.GeoDataFrame
    """
    return gpd.GeoDataFrame(
        {
            "id": ["test_aoi_1", "test_aoi_2", "test_aoi_3"],
            "name": ["Test Area 1", "Test Area 2", "Test Area 3"],
            "geometry": [
                box(-118.42, 33.93, -118.41, 33.94),
                box(-118.40, 33.93, -118.39, 33.94),
                box(-118.38, 33.93, -118.37, 33.94),
            ],
        },
        crs="EPSG:4326",
    )


@pytest.fixture
def sample_detection_feature():
    """
    Provides a sample detection feature for testing.

    :return: GeoJSON Feature with detection properties
    :rtype: dict
    """
    return {
        "type": "Feature",
        "geometry": box(-118.40, 33.93, -118.399, 33.931).__geo_interface__,
        "properties": {"label": "Building", "score": 0.95, "area": 100.0},
    }


@pytest.fixture
def sample_chip_result():
    """
    Provides a sample chip result for testing merger.

    :return: Chip result dict with detections
    :rtype: dict
    """
    return {
        "chip_id": "chip_0_0",
        "features": [
            {
                "type": "Feature",
                "geometry": box(-118.40, 33.93, -118.399, 33.931).__geo_interface__,
                "properties": {"label": "Building", "score": 0.9},
            },
            {
                "type": "Feature",
                "geometry": box(-118.395, 33.93, -118.394, 33.931).__geo_interface__,
                "properties": {"label": "Building", "score": 0.85},
            },
        ],
    }


@pytest.fixture
def minimal_model_spec():
    """
    Provides a minimal valid model spec for testing.

    :return: Model spec dictionary
    :rtype: dict
    """
    return {
        "model_id": "test/model",
        "model_name": "Test Model",
        "model_type": "object_detection",
        "workflow_type": "aoi_based",
        "data_requirements": {
            "required_bands": ["red", "green", "blue"],
            "preferred_resolution_meters": 0.6,
            "resolution_range_meters": {"min": 0.3, "max": 1.5, "optimal": 0.6},
            "supported_collections": ["naip"],
        },
        "foundry_api": {
            "endpoint_path": "/score",
            "method": "POST",
            "payload_format": "json-base64",
            "input_format": "png",
            "request_format": {},
            "response_format": {},
        },
        "parameters": {"threshold": {"type": "float", "default": 0.5, "min": 0.0, "max": 1.0}},
    }
