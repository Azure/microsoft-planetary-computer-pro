from os import path
from unittest.mock import Mock, patch

from pytest import mark, raises
from rasterio import DatasetReader  # type: ignore

from stacforge.engine.raster_info import (
    bbox_to_geom,
    eo_bands_info,
    geometry_info,
    get_raster_file_info,
    get_rasterio_dataset,
    projection_info,
    raster_info,
    url_to_vsi,
)

TEST_DATA_DIRECTORY = path.join(
    path.dirname(__file__),
    "data",
    "scenes",
)


@patch("stacforge.engine.raster_info.get_token", return_value="token")
def test_url_to_vsi_with_storage_account(get_token_mock: Mock) -> None:
    vsi, options = url_to_vsi("https://foo.blob.core.windows.net/bar/baz.tif")

    assert vsi == "/vsiaz/bar/baz.tif"
    assert options == {
        "AZURE_STORAGE_ACCOUNT": "foo",
        "AZURE_STORAGE_ACCESS_TOKEN": "token",
    }
    get_token_mock.assert_called_once()


@patch("stacforge.engine.raster_info.get_token", return_value="token")
def test_url_to_vsi_with_storage_account_and_sas_token(get_token_mock: Mock) -> None:
    vsi, options = url_to_vsi("https://foo.blob.core.windows.net/bar/baz.tif?sig=token")

    assert vsi == "/vsicurl/https://foo.blob.core.windows.net/bar/baz.tif?sig=token"
    assert options == {}
    get_token_mock.assert_not_called()


@patch("stacforge.engine.raster_info.get_token", return_value="token")
def test_url_to_vsi_with_regular_url(get_token_mock: Mock) -> None:
    vsi, options = url_to_vsi("https://example.com/bar/baz.tif")

    assert vsi == "/vsicurl/https://example.com/bar/baz.tif"
    assert options == {}
    get_token_mock.assert_not_called()


@mark.parametrize(
    "file",
    [
        "/foo/bar.tif",
        "foo/bar.tif",
        "file://foo/bar.tif",
        "file:///foo/bar.tif",
    ],
)
@patch("stacforge.engine.raster_info.get_token", return_value="token")
def test_url_to_vsi_with_file_url(get_token_mock: Mock, file: str) -> None:
    vsi, options = url_to_vsi(file)

    assert vsi == file
    assert options == {}
    get_token_mock.assert_not_called()


@mark.parametrize(
    "url",
    [
        "ftp://example.com/bar/baz.tif",
        "gopher://example.com/bar/baz.tif",
        "whatever://example.com/bar/baz.tif",
    ],
)
@patch("stacforge.engine.raster_info.get_token", return_value="token")
def test_url_to_vsi_with_unsupported_url(get_token_mock: Mock, url: str) -> None:
    with raises(NotImplementedError) as error:
        _, _ = url_to_vsi(url)

        assert "Unsupported scheme" in str(error.value)
        get_token_mock.assert_called_once()


def test_get_rasterio_dataset() -> None:
    result = get_rasterio_dataset(
        f"{TEST_DATA_DIRECTORY}/potsdam/dsm_potsdam_02_10.tif"
    )

    assert isinstance(result, DatasetReader)
    assert result.mode == "r", "The dataset should be opened in read mode"
    assert result.crs.to_epsg() == 32633
    assert result.height == 6000
    assert result.width == 6000


def test_bbox_to_geom() -> None:
    result = bbox_to_geom((0, 1, 2, 3))

    assert result == {
        "type": "Polygon",
        "coordinates": [[[0, 1], [2, 1], [2, 3], [0, 3], [0, 1]]],
    }


def test_projection_info() -> None:
    ds = get_rasterio_dataset(f"{TEST_DATA_DIRECTORY}/potsdam/dsm_potsdam_02_10.tif")

    result = projection_info(ds)

    assert result == {
        "epsg": 32633,
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [366976.5, 5808262.6],
                    [367276.5, 5808262.6],
                    [367276.5, 5808562.6],
                    [366976.5, 5808562.6],
                    [366976.5, 5808262.6],
                ]
            ],
        },
        "bbox": [366976.5, 5808262.6, 367276.5, 5808562.6],
        "shape": [6000, 6000],
        "transform": [0.05, 0.0, 366976.5, 0.0, -0.05, 5808562.6, 0.0, 0.0, 1.0],
        "projjson": {
            "$schema": "https://proj.org/schemas/v0.7/projjson.schema.json",
            "type": "ProjectedCRS",
            "name": "WGS 84 / UTM zone 33N",
            "base_crs": {
                "name": "WGS 84",
                "datum": {
                    "type": "GeodeticReferenceFrame",
                    "name": "World Geodetic System 1984",
                    "ellipsoid": {
                        "name": "WGS 84",
                        "semi_major_axis": 6378137,
                        "inverse_flattening": 298.257223563,
                    },
                },
                "coordinate_system": {
                    "subtype": "ellipsoidal",
                    "axis": [
                        {
                            "name": "Geodetic latitude",
                            "abbreviation": "Lat",
                            "direction": "north",
                            "unit": "degree",
                        },
                        {
                            "name": "Geodetic longitude",
                            "abbreviation": "Lon",
                            "direction": "east",
                            "unit": "degree",
                        },
                    ],
                },
                "id": {"authority": "EPSG", "code": 4326},
            },
            "conversion": {
                "name": "UTM zone 33N",
                "method": {
                    "name": "Transverse Mercator",
                    "id": {"authority": "EPSG", "code": 9807},
                },
                "parameters": [
                    {
                        "name": "Latitude of natural origin",
                        "value": 0,
                        "unit": "degree",
                        "id": {"authority": "EPSG", "code": 8801},
                    },
                    {
                        "name": "Longitude of natural origin",
                        "value": 15,
                        "unit": "degree",
                        "id": {"authority": "EPSG", "code": 8802},
                    },
                    {
                        "name": "Scale factor at natural origin",
                        "value": 0.9996,
                        "unit": "unity",
                        "id": {"authority": "EPSG", "code": 8805},
                    },
                    {
                        "name": "False easting",
                        "value": 500000,
                        "unit": "metre",
                        "id": {"authority": "EPSG", "code": 8806},
                    },
                    {
                        "name": "False northing",
                        "value": 0,
                        "unit": "metre",
                        "id": {"authority": "EPSG", "code": 8807},
                    },
                ],
            },
            "coordinate_system": {
                "subtype": "Cartesian",
                "axis": [
                    {
                        "name": "Easting",
                        "abbreviation": "",
                        "direction": "east",
                        "unit": "metre",
                    },
                    {
                        "name": "Northing",
                        "abbreviation": "",
                        "direction": "north",
                        "unit": "metre",
                    },
                ],
            },
            "id": {"authority": "EPSG", "code": 32633},
        },
        "wkt2": 'PROJCS["WGS 84 / UTM zone 33N",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",15],PARAMETER["scale_factor",0.9996],PARAMETER["false_easting",500000],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH],AUTHORITY["EPSG","32633"]]',  # noqa: 501
    }


def test_geometry_info() -> None:
    ds = get_rasterio_dataset(f"{TEST_DATA_DIRECTORY}/potsdam/dsm_potsdam_02_10.tif")

    result = geometry_info(ds)

    assert result == {
        "bbox": [
            13.04424788998661,
            52.40840210737653,
            13.048774795821945,
            52.41117048974132,
        ],
        "footprint": {
            "type": "Polygon",
            "coordinates": [
                [
                    (13.044367153241899, 52.40840210737653),
                    (13.048774795821945, 52.40847495599907),
                    (13.04865580094816, 52.41117048974132),
                    (13.04424788998661, 52.411097634072696),
                    (13.044367153241899, 52.40840210737653),
                ]
            ],
        },
    }


def test_raster_info() -> None:
    ds = get_rasterio_dataset(f"{TEST_DATA_DIRECTORY}/potsdam/dsm_potsdam_02_10.tif")

    result = raster_info(ds)

    assert result == [
        {
            "data_type": "float32",
            "scale": 1.0,
            "offset": 0.0,
            "sampling": "area",
            "statistics": {
                "mean": 0.0,
                "minimum": 0.0,
                "maximum": 0.0,
                "stddev": 0.0,
                "valid_percent": 9.5367431640625e-05,
            },
            "histogram": {
                "count": 11,
                "min": -0.5,
                "max": 0.5,
                "buckets": [0, 0, 0, 0, 0, 1048576, 0, 0, 0, 0],
            },
        }
    ]


def test_eo_bands_info() -> None:
    ds = get_rasterio_dataset(f"{TEST_DATA_DIRECTORY}/potsdam/dsm_potsdam_02_10.tif")

    result = eo_bands_info(ds)

    assert result == [{"name": "b1", "description": "gray"}]


@patch("stacforge.engine.raster_info.get_rasterio_dataset")
@patch("stacforge.engine.raster_info.projection_info", return_value="projection_info")
@patch("stacforge.engine.raster_info.geometry_info", return_value="geometry_info")
@patch("stacforge.engine.raster_info.raster_info", return_value="raster_info")
@patch("stacforge.engine.raster_info.eo_bands_info", return_value="eo_bands_info")
def test_get_raster_file_info(
    eo_bands_info_mock: Mock,
    raster_info_mock: Mock,
    geometry_info_mock: Mock,
    projection_info_mock: Mock,
    get_rasterio_dataset_mock: Mock,
) -> None:
    ds_mock = Mock(DatasetReader)
    ds_mock.configure_mock(**({"tags.return_value": "tags"}))
    get_rasterio_dataset_mock.return_value = ds_mock

    result = get_raster_file_info("https://example.com/foo/bar.tif")

    assert result == {
        "projection": "projection_info",
        "geometry": "geometry_info",
        "raster_bands": "raster_info",
        "eo_bands": "eo_bands_info",
        "tags": "tags",
    }
    get_rasterio_dataset_mock.assert_called_once_with(
        "https://example.com/foo/bar.tif", {}
    )
    projection_info_mock.assert_called_once_with(ds_mock)
    geometry_info_mock.assert_called_once_with(ds_mock)
    raster_info_mock.assert_called_once_with(ds_mock)
    eo_bands_info_mock.assert_called_once_with(ds_mock)
