import re
from typing import Any, Callable, Dict, Iterator, List

import antimeridian
import rasterio  # type: ignore
from jinja2.filters import do_tojson
from jinja2.nodes import EvalContext
from jinja2.utils import pass_eval_context
from markupsafe import Markup
from rasterio import warp
from shapely import (
    Point,
    Polygon,
    make_valid,
)
from shapely import simplify as simplify_shape
from shapely.geometry import mapping
from shapely.geometry import shape as shapely_shape
from shapely.geometry.base import BaseGeometry

from stacforge.engine.raster_info import (
    eo_bands_info,
    geometry_info,
    projection_info,
    raster_info,
)
from stacforge.logging import log

GeoTemplateFilters: Dict[str, Callable] = {}
"""A dictionary of filters that can be applied to variables
in a GeoTemplate."""

# In a GeoTemplate, variables can be modified by filters.
# Filters are separated from the variable by a pipe symbol (|)
# and may have optional arguments in parentheses.
# Multiple filters can be chained.
# The output of one filter is applied to the next.


def register_filter(
    filter: Callable,
) -> Callable:
    """Add a filter to the GeoTemplateFilters dictionary."""

    logged_filter = log(filter)
    GeoTemplateFilters[filter.__name__] = logged_filter
    return logged_filter


@register_filter
def regex_match(
    string: str,
    pattern: str,
    flags: int = 0,
) -> re.Match[str] | None:
    """Try to apply the pattern at the start of the string, returning
    a `Match` object, or `None` if no match was found."""

    return re.match(pattern, string, flags)


@register_filter
def regex_fullmatch(
    string: str,
    pattern: str,
    flags: int = 0,
) -> re.Match[str] | None:
    """Try to apply the pattern to all of the string, returning
    a `Match` object, or `None` if no match was found."""

    return re.fullmatch(pattern, string, flags)


@register_filter
def regex_search(
    string: str,
    pattern: str,
    flags: int = 0,
) -> re.Match[str] | None:
    """Scan through string looking for a match to the pattern, returning
    a Match object, or `None` if no match was found."""

    return re.search(pattern, string, flags)


@register_filter
def regex_sub(
    string: str,
    pattern: str,
    repl: str,
    count: int = 0,
    flags: int = 0,
) -> str:
    """Return the string obtained by replacing the leftmost
    non-overlapping occurrences of the pattern in string by the
    replacement `repl`.  Backslash escapes in `repl` are processed."""

    return re.sub(pattern, repl, string, count, flags)


@register_filter
def regex_subn(
    string: str,
    pattern: str,
    repl: str,
    count: int = 0,
    flags: int = 0,
) -> tuple[str, int]:
    """Perform the same operation as `regex_sub`, but return a tuple
    containing the new string value and the number of replacements made."""

    return re.subn(pattern, repl, string, count, flags)


@register_filter
def regex_split(
    string: str,
    pattern: str,
    maxsplit: int = 0,
    flags: int = 0,
) -> List[str | Any]:
    """Split the source string by the occurrences of the pattern,
    returning a list containing the resulting substrings.  If
    capturing parentheses are used in pattern, then the text of all
    groups in the pattern are also returned as part of the resulting
    list.  If `maxsplit` is nonzero, at most `maxsplit` splits occur,
    and the remainder of the string is returned as the final element
    of the list."""

    return re.split(pattern, string, maxsplit, flags)


@register_filter
def regex_findall(
    string: str,
    pattern: str,
    flags: int = 0,
) -> List[Any]:
    """Return a list of all non-overlapping matches in the string.

    If one or more capturing groups are present in the pattern, return
    a list of groups; this will be a list of tuples if the pattern
    has more than one group.

    Empty matches are included in the result."""

    return re.findall(pattern, string, flags)


@register_filter
def regex_finditer(
    string: str,
    pattern: str,
    flags: int = 0,
) -> Iterator[re.Match[str]]:
    """Return an iterator yielding `Match` objects over all non-overlapping
    matches for the RE pattern in string."""

    return re.finditer(pattern, string, flags)


@register_filter
def shape_from_footprint(
    footprint: List[float],
    rounding: int = 6,
) -> BaseGeometry:
    """Create a shape from a list of coordinates representing a footprint."""

    footprint_points = [
        p[::-1]
        for p in list(zip(*[iter(round(coord, rounding) for coord in footprint)] * 2))
    ]
    poly = Polygon(footprint_points)
    fixed_poly = antimeridian.fix_shape(poly)
    shape = shapely_shape(fixed_poly)
    valid_shape = make_valid(shape)
    return valid_shape


@register_filter
def bbox(
    geo_json: Dict[str, Any] | BaseGeometry,
) -> List[float]:
    """Calculates a GeoJSON-spec conforming bounding box
    for a GeoJSON shape."""

    return antimeridian.bbox(geo_json)


@register_filter
@pass_eval_context
def tojson(
    eval_ctx: EvalContext,
    obj: Any,
    indent: int | None = None,
) -> Markup:
    """Serialize `obj` to a JSON formatted `str`."""

    if hasattr(obj, "__geo_interface__"):
        obj = mapping(obj)
    return do_tojson(eval_ctx, obj, indent)


@register_filter
def centroid(
    geo_json: Dict[str, Any] | BaseGeometry,
) -> Point:
    """Calculates the centroid for a polygon or multipolygon."""

    return antimeridian.centroid(geo_json)


@register_filter
def simplify(
    geometry: Dict[str, Any] | BaseGeometry,
    tolerance: float,
    preserve_topology: bool = True,
) -> BaseGeometry:
    """Returns a simplified version of an input geometry using
    the Douglas-Peucker algorithm."""

    shape = shapely_shape(geometry)
    return simplify_shape(shape, tolerance, preserve_topology)


@register_filter
def transform(
    geometry: Dict[str, Any] | BaseGeometry,
    src_crs: str | int,
    dst_crs: str | int,
    precision: int = -1,
) -> BaseGeometry:
    """Transform a geometry from source coordinate reference
    system into target."""

    if isinstance(src_crs, int):
        source_crs_str = f"EPSG:{src_crs}"
    else:
        source_crs_str = src_crs

    if isinstance(dst_crs, int):
        dest_crs_str = f"EPSG:{dst_crs}"
    else:
        dest_crs_str = dst_crs

    source_crs = rasterio.CRS.from_string(source_crs_str)
    dest_crs = rasterio.CRS.from_string(dest_crs_str)

    warped_dict = warp.transform_geom(
        src_crs=source_crs,
        dst_crs=dest_crs,
        geom=mapping(shapely_shape(geometry)),
        precision=precision,
    )
    fixed_dict = antimeridian.fix_geojson(warped_dict)
    fixed_shape = shapely_shape(fixed_dict)

    return fixed_shape


register_filter(projection_info)
register_filter(geometry_info)
register_filter(raster_info)
register_filter(eo_bands_info)
