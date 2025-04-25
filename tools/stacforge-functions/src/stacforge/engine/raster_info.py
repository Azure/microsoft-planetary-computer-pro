# This work is based largely in the rasterio plugin rio-stac, which allows
# to generate STAC metadata from raster files.
# https://github.com/developmentseed/rio-stac

import logging
import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

import numpy
import rasterio  # type: ignore
from azure.identity import DefaultAzureCredential
from rasterio import warp
from rasterio.errors import RasterioIOError  # type: ignore
from rasterio.features import bounds as feature_bounds  # type: ignore
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_fixed,
)

from stacforge.logging import LOGGER_NAME
from stacforge.utils import get_cloud

RETRIES = 3
WAIT_SECONDS = 2

EPSG_4326 = rasterio.CRS.from_epsg(4326)  # The World Geodetic System 1984 (WGS84)

_logger = logging.getLogger(LOGGER_NAME)

_access_token = None
"""Cached access token for Azure Storage."""


def get_token() -> str:
    """Get an access token for Azure Storage."""

    global _access_token
    if _access_token is None or datetime.fromtimestamp(
        _access_token.expires_on
    ) < datetime.now() + timedelta(minutes=5):
        cred = DefaultAzureCredential(
            authority=get_cloud().endpoints.active_directory,
        )
        cloud = get_cloud()
        if cloud.scopes is None or cloud.scopes.storage_account_resource_id is None:
            raise ValueError("No scope found for Azure Storage")
        scope = cloud.scopes.storage_account_resource_id
        _access_token = cred.get_token(scope)
    return _access_token.token


def url_to_vsi(url: str) -> Tuple[str, Dict[str, Any]]:
    """Convert a URL to a VSI path and options."""

    url_parsed = urlparse(url)

    # Check if the URL is a file
    if url_parsed.scheme in ("file", ""):
        return url, {}
    elif url_parsed.scheme == "https":
        # Check if the URL is a blob storage URL
        # TODO: check other clouds endpoints (USGov, China, etc.)
        if url_parsed.netloc.endswith("blob.core.windows.net"):
            # Check if there is a SAS token
            if "sig=" in url_parsed.query:
                return f"/vsicurl/{url}", {}

            account = url_parsed.netloc.split(".")[0]
            container = url_parsed.path.split("/")[1]
            blob = "/".join(url_parsed.path.split("/")[2:])
            vsi = f"/vsiaz/{container}/{blob}"
            options = {
                "AZURE_STORAGE_ACCOUNT": account,
                "AZURE_STORAGE_ACCESS_TOKEN": get_token(),
            }

            return vsi, options
        else:
            # Assume it's a regular URL
            return f"/vsicurl/{url}", {}
    else:
        raise NotImplementedError(f"Unsupported scheme: {url_parsed.scheme}")


@retry(
    retry=retry_if_exception(lambda e: isinstance(e, RasterioIOError)),
    before_sleep=before_sleep_log(_logger, logging.WARN),
    stop=stop_after_attempt(RETRIES),
    wait=wait_fixed(WAIT_SECONDS),
    reraise=True,
)
def get_rasterio_dataset(
    url: str,
    options: Dict[str, Any] = {},
) -> rasterio.DatasetReader:
    """Open a rasterio dataset from a URL."""

    vsi_or_file, vsi_options = url_to_vsi(url)

    with rasterio.Env(**vsi_options, **options):
        return rasterio.open(vsi_or_file, "r")


def bbox_to_geom(bbox: Tuple[float, float, float, float]) -> Dict:
    """Return a geojson geometry from a bbox."""

    return {
        "type": "Polygon",
        "coordinates": [
            [
                [bbox[0], bbox[1]],
                [bbox[2], bbox[1]],
                [bbox[2], bbox[3]],
                [bbox[0], bbox[3]],
                [bbox[0], bbox[1]],
            ]
        ],
    }


def projection_info(dataset: rasterio.DatasetReader) -> Dict:
    """Get projection metadata.

    The STAC projection extension allows for three different ways to describe the
    coordinate reference system associated with a raster :
    - EPSG code
    - WKT2
    - PROJJSON

    All are optional, and they can be provided altogether as well. Therefore, as long
    as one can be obtained from the data, we add it to the returned dictionary.

    see: https://github.com/stac-extensions/projection"""
    projjson = None
    wkt2 = None
    epsg = None
    if dataset.crs is not None:
        # EPSG
        epsg = dataset.crs.to_epsg() if dataset.crs.is_epsg_code else None

        # PROJJSON
        try:
            projjson = dataset.crs.to_dict(projjson=True)
        except (AttributeError, TypeError) as ex:
            _logger.warning(f"Could not get PROJJSON from dataset : {ex}")
            pass

        # WKT2
        try:
            wkt2 = dataset.crs.to_wkt()
        except Exception as ex:
            _logger.warning(f"Could not get WKT2 from dataset : {ex}")
            pass

    meta = {
        "epsg": epsg,
        "geometry": bbox_to_geom(dataset.bounds),
        "bbox": list(dataset.bounds),
        "shape": [dataset.height, dataset.width],
        "transform": list(dataset.transform),
    }

    if projjson is not None:
        meta["projjson"] = projjson

    if wkt2 is not None:
        meta["wkt2"] = wkt2

    return meta


def geometry_info(
    dataset: rasterio.DatasetReader,
    densify_pts: int = 0,
    precision: int = -1,
) -> Dict:
    """Get Raster Footprint."""

    if densify_pts < 0:
        raise ValueError("`densify_pts` must be positive")

    if dataset.crs is not None:
        # 1. Create Polygon from raster bounds
        geom = bbox_to_geom(dataset.bounds)

        # 2. Densify the Polygon geometry
        if dataset.crs != EPSG_4326 and densify_pts:
            # Derived from code found at
            # https://stackoverflow.com/questions/64995977/generating-equidistance-points-along-the-boundary-of-a-polygon-but-cw-ccw
            coordinates = numpy.asarray(geom["coordinates"][0])

            densified_number = len(coordinates) * densify_pts
            existing_indices = numpy.arange(0, densified_number, densify_pts)
            interp_indices = numpy.arange(existing_indices[-1] + 1)
            interp_x = numpy.interp(interp_indices, existing_indices, coordinates[:, 0])
            interp_y = numpy.interp(interp_indices, existing_indices, coordinates[:, 1])
            geom = {
                "type": "Polygon",
                "coordinates": [[(x, y) for x, y in zip(interp_x, interp_y)]],
            }

        # 3. Reproject the geometry to "epsg:4326"
        geom = warp.transform_geom(dataset.crs, EPSG_4326, geom, precision=precision)
        bbox = feature_bounds(geom)

    else:
        _logger.warning(
            "Input file doesn't have CRS information, setting geometry and bbox to (-180,-90,180,90)."  # noqa: E501
        )
        bbox = (-180.0, -90.0, 180.0, 90.0)
        geom = bbox_to_geom(bbox)

    return {"bbox": list(bbox), "footprint": geom}


def get_stats(arr: numpy.ma.MaskedArray, **kwargs: Any) -> Dict:
    """Calculate array statistics."""

    # Avoid non masked nan/inf values
    numpy.ma.fix_invalid(arr, copy=False)
    sample, edges = numpy.histogram(arr[~arr.mask])
    return {
        "statistics": {
            "mean": arr.mean().item(),
            "minimum": arr.min().item(),
            "maximum": arr.max().item(),
            "stddev": arr.std().item(),
            "valid_percent": numpy.count_nonzero(~arr.mask)
            / float(arr.data.size)
            * 100,
        },
        "histogram": {
            "count": len(edges),
            "min": float(edges.min()),
            "max": float(edges.max()),
            "buckets": sample.tolist(),
        },
    }


def raster_info(
    dataset: rasterio.DatasetReader,
    max_size: int = 1024,
) -> List[Dict]:
    """Get raster metadata.
    see: https://github.com/stac-extensions/raster#raster-band-object"""

    height = dataset.height
    width = dataset.width
    if max_size:
        if max(width, height) > max_size:
            ratio = height / width
            if ratio > 1:
                height = max_size
                width = math.ceil(height / ratio)
            else:
                width = max_size
                height = math.ceil(width * ratio)

    meta: List[Dict] = []

    area_or_point = dataset.tags().get("AREA_OR_POINT", "").lower()

    # Missing `bits_per_sample` and `spatial_resolution`
    for band in dataset.indexes:
        value = {
            "data_type": dataset.dtypes[band - 1],
            "scale": dataset.scales[band - 1],
            "offset": dataset.offsets[band - 1],
        }
        if area_or_point:
            value["sampling"] = area_or_point

        # If the Nodata is not set we don't forward it.
        if dataset.nodata is not None:
            if numpy.isnan(dataset.nodata):
                value["nodata"] = "nan"
            elif numpy.isposinf(dataset.nodata):
                value["nodata"] = "inf"
            elif numpy.isneginf(dataset.nodata):
                value["nodata"] = "-inf"
            else:
                value["nodata"] = dataset.nodata

        if dataset.units[band - 1] is not None:
            value["unit"] = dataset.units[band - 1]

        value.update(
            get_stats(
                dataset.read(indexes=band, out_shape=(height, width), masked=True)
            )
        )
        meta.append(value)

    return meta


def eo_bands_info(dataset: rasterio.DatasetReader) -> List[Dict]:
    """Get eo:bands metadata.
    see: https://github.com/stac-extensions/eo#item-properties-or-asset-fields"""

    eo_bands = []

    colors = dataset.colorinterp
    for ix in dataset.indexes:
        band_meta = {"name": f"b{ix}"}

        desc = dataset.descriptions[ix - 1]
        color = colors[ix - 1].name

        # Description metadata or Colorinterp or Nothing
        description = desc or color
        if description:
            band_meta["description"] = description

        eo_bands.append(band_meta)

    return eo_bands


def get_raster_file_info(
    url: str,
    options: Dict[str, Any] = {},
) -> Dict[str, Any]:
    """Get raster file metadata."""

    dataset = get_rasterio_dataset(url, options)
    return {
        "projection": projection_info(dataset),
        "geometry": geometry_info(dataset),
        "raster_bands": raster_info(dataset),
        "eo_bands": eo_bands_info(dataset),
        "tags": dataset.tags(),
    }
