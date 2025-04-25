from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

from affine import Affine  # type: ignore
from pytest import mark

from stacforge.engine.functions import (
    GeoTemplateFunctions,
    StorageClient,
    affine_transform_from_bounds,
    affine_transform_from_origin,
    get_json,
    get_text,
    get_xml,
    now,
)


@mark.parametrize(
    "function_name",
    [
        "affine_transform_from_bounds",
        "affine_transform_from_origin",
        "get_json",
        "get_raster_file_info",
        "get_rasterio_dataset",
        "get_text",
        "get_xml",
        "now",
    ],
)
def test_function_registration(function_name: str) -> None:
    assert function_name in GeoTemplateFunctions


def test_now_function() -> None:
    result = now()

    assert isinstance(result, str)
    assert result.endswith("Z")
    datetime.fromisoformat(result)  # Check if the result is a valid ISO 8601 date


def test_affine_transform_from_bounds_function() -> None:
    result = affine_transform_from_bounds(0, 0, 1, 1, 100, 100)

    assert isinstance(result, Affine)
    assert result.a == 0.01
    assert result.b == 0.0
    assert result.c == 0.0
    assert result.d == 0.0
    assert result.e == -0.01
    assert result.f == 1.0
    assert result.g == 0.0
    assert result.h == 0.0
    assert result.i == 1.0
    assert result.determinant == -0.0001
    assert result.eccentricity == 0.0
    assert result.is_conformal
    assert not result.is_degenerate
    assert not result.is_identity
    assert not result.is_orthonormal
    assert not result.is_proper
    assert result.is_rectilinear


def test_affine_transform_from_origin_function() -> None:
    result = affine_transform_from_origin(0, 1, 0.01, 0.01)

    assert isinstance(result, Affine)
    assert result.a == 0.01
    assert result.b == 0.0
    assert result.c == 0.0
    assert result.d == 0.0
    assert result.e == -0.01
    assert result.f == 1.0
    assert result.g == 0.0
    assert result.h == 0.0
    assert result.i == 1.0
    assert result.determinant == -0.0001
    assert result.eccentricity == 0.0
    assert result.is_conformal
    assert not result.is_degenerate
    assert not result.is_identity
    assert not result.is_orthonormal
    assert not result.is_proper
    assert result.is_rectilinear


@mark.asyncio
@patch.object(
    StorageClient,
    "download_blob_from_url",
    return_value=b"template",
)
async def test_get_text_function(storage_client_mock: Mock) -> None:
    result = await get_text("https://foo.blob.core.windows.net/bar/baz")

    assert result == "template"
    assert storage_client_mock.call_count == 1
    assert (
        storage_client_mock.call_args[0][0]
        == "https://foo.blob.core.windows.net/bar/baz"
    )


@mark.asyncio
async def test_get_xml_function() -> None:
    get_text_async_mock = AsyncMock(return_value='<foo baz="123">bar</foo>')
    GeoTemplateFunctions["get_text"] = get_text_async_mock
    result = await get_xml("https://foo.blob.core.windows.net/bar/baz")

    assert result == {"foo": {"@baz": "123", "#text": "bar"}}
    assert get_text_async_mock.call_count == 1
    assert (
        get_text_async_mock.call_args[0][0]
        == "https://foo.blob.core.windows.net/bar/baz"
    )


@mark.asyncio
async def test_get_json_function() -> None:
    get_text_async_mock = AsyncMock(return_value='{"foo": "bar", "baz": 123}')
    GeoTemplateFunctions["get_text"] = get_text_async_mock
    result = await get_json("https://foo.blob.core.windows.net/bar/baz")

    assert result == {
        "foo": "bar",
        "baz": 123,
    }
    assert get_text_async_mock.call_count == 1
    assert (
        get_text_async_mock.call_args[0][0]
        == "https://foo.blob.core.windows.net/bar/baz"
    )
