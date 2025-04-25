import re
from typing import Iterator

from pytest import mark
from shapely import Point, Polygon

from stacforge.engine import Environment
from stacforge.engine.filters import (
    GeoTemplateFilters,
    bbox,
    centroid,
    regex_findall,
    regex_finditer,
    regex_fullmatch,
    regex_match,
    regex_search,
    regex_split,
    regex_sub,
    regex_subn,
    shape_from_footprint,
    simplify,
    transform,
)


@mark.parametrize(
    "filter_name",
    [
        "bbox",
        "centroid",
        "eo_bands_info",
        "geometry_info",
        "projection_info",
        "raster_info",
        "regex_findall",
        "regex_finditer",
        "regex_fullmatch",
        "regex_match",
        "regex_search",
        "regex_split",
        "regex_sub",
        "regex_subn",
        "shape_from_footprint",
        "simplify",
        "tojson",
        "transform",
    ],
)
def test_filter_registration(filter_name: str) -> None:
    assert filter_name in GeoTemplateFilters


def test_regex_match_filter() -> None:
    result = regex_match("Hello, World!", r"Hello, (\w+)!")

    assert isinstance(result, re.Match)
    assert result is not None
    assert result.group(1) == "World"


def test_regex_fullmatch_filter() -> None:
    result = regex_fullmatch("Hello, World!", r"Hello, (\w+)!")

    assert isinstance(result, re.Match)
    assert result is not None
    assert result.group(1) == "World"


def test_regex_search_filter() -> None:
    result = regex_search("Hello, World!", r"Hello, (\w+)!")

    assert isinstance(result, re.Match)
    assert result is not None
    assert result.group(1) == "World"


def test_regex_sub_filter() -> None:
    result = regex_sub("Hello, World!", r"Hello, (\w+)!", r"Goodbye, \1!")

    assert result == "Goodbye, World!"


def test_regex_subn_filter() -> None:
    result = regex_subn("Hello, World!", r"Hello, (\w+)!", r"Goodbye, \1!")

    assert isinstance(result, tuple)
    assert result[0] == "Goodbye, World!"
    assert result[1] == 1


def test_regex_split_filter() -> None:
    result = regex_split("Hello, World!", r",\s*")

    assert result == ["Hello", "World!"]


def test_regex_findall_filter() -> None:
    result = regex_findall("Hello, World! Goodbye, World!", r"(\w+), (\w+)!")

    assert result == [
        ("Hello", "World"),
        ("Goodbye", "World"),
    ]


def test_regex_finditer_filter() -> None:
    result = regex_finditer("Hello, World! Goodbye, World!", r"(\w+), (\w+)!")

    assert isinstance(result, Iterator)
    assert [match.groups() for match in result] == [
        ("Hello", "World"),
        ("Goodbye", "World"),
    ]


def test_shape_from_footprint_filter() -> None:
    result = shape_from_footprint(
        [
            40.64479480422486,
            115.81682739339685,
            40.65079881136531,
            117.1154430676197,
            39.66155122739065,
            117.11377991452629,
            39.655752572676114,
            115.83386830444628,
            40.64479480422486,
            115.81682739339685,
        ]
    )

    assert isinstance(result, Polygon)
    assert not result.is_closed
    assert not result.is_empty
    assert not result.is_ring
    assert result.is_simple
    assert result.is_valid
    assert result.bounds == (
        115.81682699999999,
        39.655753,
        117.11544300000003,
        40.650799,
    )


def test_bbox_filter() -> None:
    result = bbox(Polygon([(0, 0), (1, 1), (1, 0), (0, 1)]))

    assert result == [0.0, 0.0, 1.0, 1.0]


@mark.asyncio
async def test_tojson_filter_with_dict() -> None:
    env = Environment()
    tpl = env.get_geotemplate_from_source("{{ {'foo': 'bar'} | tojson }}")
    result = await tpl.render_text("foo")

    assert result == '{"foo": "bar"}'


@mark.asyncio
async def test_tojson_filter_with_list() -> None:
    env = Environment()
    tpl = env.get_geotemplate_from_source("{{ ['foo', 'bar'] | tojson }}")
    result = await tpl.render_text("foo")

    assert result == '["foo", "bar"]'


@mark.asyncio
async def test_tojson_filter_with_polygon() -> None:
    env = Environment()
    env.add_function("polygon", lambda: Polygon([(0, 0), (1, 1), (1, 0), (0, 1)]))
    tpl = env.get_geotemplate_from_source("{{ polygon() | tojson }}")
    result = await tpl.render_text("foo")

    assert (
        result
        == '{"coordinates": [[[0.0, 0.0], [1.0, 1.0], [1.0, 0.0], [0.0, 1.0], [0.0, 0.0]]], "type": "Polygon"}'  # noqa: E501
    )


def test_centroid_filter() -> None:
    result = centroid(Polygon([(0, 0), (1, 1), (1, 0), (0, 1)]))

    assert result == Point(0.5, 0.5)


def test_simplify_filter() -> None:
    result = simplify(
        Polygon([(0, 0), (1, 1), (1, 0), (0, 1)]),
        0.1,
    )

    assert result == Polygon([(0, 0), (1, 1), (1, 0), (0, 1)])


def test_transform_filter() -> None:
    result = transform(
        Polygon([(0, 0), (1, 1), (1, 0), (0, 1)]),
        "EPSG:32633",
        "EPSG:4326",
    )

    assert result == Polygon(
        [
            (10.511256115612781, 0.0),
            (10.511256115612724, 9.019375809373756e-06),
            (10.511265074609526, 0.0),
            (10.511265074609469, 9.01937592083914e-06),
        ]
    )
