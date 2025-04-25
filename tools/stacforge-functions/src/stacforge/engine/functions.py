import json
from datetime import UTC, datetime
from typing import Any, Callable, Dict

import xmltodict
from affine import Affine  # type: ignore
from rasterio import transform  # type: ignore

from stacforge.clients import StorageClient
from stacforge.engine.raster_info import get_raster_file_info, get_rasterio_dataset
from stacforge.logging import log

GeoTemplateFunctions: Dict[str, Callable] = {}
"""A dictionary of functions that can be called in a GeoTemplate."""


def register_function(func: Callable) -> Callable:
    """Add a function to the GoTemplateFunctions dictionary."""

    logged_func = log(func)
    GeoTemplateFunctions[func.__name__] = logged_func
    return logged_func


@register_function
def now() -> str:
    """Return the current UTC date and time in ISO 8601 format."""

    return datetime.now(UTC).isoformat().split("+")[0] + "Z"


@register_function
def affine_transform_from_bounds(
    west: float,
    south: float,
    east: float,
    north: float,
    width: int,
    height: int,
) -> Affine:
    """Return an Affine transformation given bounds, width and height.

    Return an Affine transformation for a georeferenced raster given
    its bounds `west`, `south`, `east`, `north` and its `width` and
    `height` in number of pixels."""

    return transform.from_bounds(west, south, east, north, width, height)


@register_function
def affine_transform_from_origin(
    west: float,
    north: float,
    xsize: float,
    ysize: float,
) -> Affine:
    """Return an Affine transformation given upper left and pixel sizes.

    Return an Affine transformation for a georeferenced raster given
    the coordinates of its upper left corner `west`, `north` and pixel
    sizes `xsize`, `ysize`."""

    return transform.from_origin(west, north, xsize, ysize)


@register_function
async def get_text(url: str) -> str:
    """Return the content of a text file at the given URL."""

    b = await StorageClient.download_blob_from_url(url)
    content = b.decode("utf-8")
    return content


@register_function
async def get_xml(url: str, **kwargs) -> Dict[str, Any]:
    """Return the content of an XML file at the given URL as a dictionary."""

    get_text_func = GeoTemplateFunctions["get_text"]
    text = await get_text_func(url)
    xml_dict = xmltodict.parse(text, **kwargs)

    return xml_dict


@register_function
async def get_json(url: str) -> Dict[str, Any]:
    """Return the content of a JSON file at the given URL as a dictionary."""

    get_text_func = GeoTemplateFunctions["get_text"]
    text = await get_text_func(url)
    json_dict = json.loads(text)

    return json_dict


register_function(get_rasterio_dataset)
register_function(get_raster_file_info)
