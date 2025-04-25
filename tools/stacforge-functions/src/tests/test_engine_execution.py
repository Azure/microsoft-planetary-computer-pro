from os import path

from jinja2.exceptions import TemplateRuntimeError
from pytest import fixture, mark, raises

from stacforge.engine import (
    Environment,
    GeoTemplate,
    GeoTemplateJsonError,
    GeoTemplateRuntimeError,
    GeoTemplateStacError,
)

from .utils import get_template

TEST_DATA_DIRECTORY = path.join(
    path.dirname(__file__),
    "data",
    "scenes",
)


async def get_text(file_path: str) -> str:
    full_path = path.join(TEST_DATA_DIRECTORY, file_path)
    with open(full_path) as file:
        text = file.read()

    return text


@fixture
def environment() -> Environment:
    environment = Environment(enable_cache=False)
    environment.add_function("get_text", get_text)

    return environment


@fixture
def geotemplate(
    template_name: str,
    environment: Environment,
) -> GeoTemplate:
    template = get_template(template_name)

    return environment.get_geotemplate_from_source(template)


@mark.asyncio
@mark.parametrize("template_name", ["valid_text.j2"])
async def test_valid_text(geotemplate: GeoTemplate) -> None:
    text = await geotemplate.render_text("valid_text")

    assert "valid_text" in text


@mark.asyncio
@mark.parametrize("template_name", ["invalid_json.j2"])
async def test_invalid_json(geotemplate: GeoTemplate) -> None:
    with raises(GeoTemplateJsonError) as error:
        await geotemplate.render_json("valid_json")

    assert "Error decoding JSON" in str(error.value)


@mark.asyncio
@mark.parametrize("template_name", ["valid_json.j2"])
async def test_valid_json(geotemplate: GeoTemplate) -> None:
    json = await geotemplate.render_json("valid_json")

    assert json["sceneInfo"] == "valid_json"


@mark.asyncio
@mark.parametrize("template_name", ["valid_stac.j2"])
async def test_valid_stac(geotemplate: GeoTemplate) -> None:
    item = await geotemplate.render_stac("sentinel-2-l2a/valid_scene", validate=True)

    assert item.id == "S2A_MSIL2A_20230815T030551_R075_T50TMK_20230815T082905"

    # Raises an exception if the item is invalid
    item.validate()


@mark.asyncio
@mark.parametrize("template_name", ["security_error.j2"])
async def test_security_error(geotemplate: GeoTemplate) -> None:
    with raises(GeoTemplateRuntimeError) as error:
        await geotemplate.render_stac("sentinel-2-l2a/valid_scene")

    assert "Runtime security error rendering template" in str(error.value)


@mark.asyncio
@mark.parametrize("template_name", ["filter_error.j2"])
async def test_filter_argument_error(geotemplate: GeoTemplate) -> None:
    with raises(GeoTemplateRuntimeError) as error:
        await geotemplate.render_text("valid_scene")

    assert "Filter was called with invalid arguments" in str(error.value)


@mark.asyncio
async def test_other_runtime_error() -> None:
    def error_fn() -> None:
        raise ValueError("Some error")

    env = Environment(enable_cache=False)
    env.add_function("error_fn", error_fn)
    geotemplate = env.get_geotemplate_from_source("{{ error_fn() }}")

    with raises(GeoTemplateRuntimeError) as error:
        await geotemplate.render_stac("sentinel-2/valid_scene")

    assert "Error rendering template" in str(error.value)


@mark.asyncio
async def test_force_template_runtime_error() -> None:
    def error_fn() -> None:
        raise TemplateRuntimeError("Some error")

    env = Environment(enable_cache=False)
    env.add_function("error_fn", error_fn)
    geotemplate = env.get_geotemplate_from_source("{{ error_fn() }}")

    with raises(GeoTemplateRuntimeError) as error:
        await geotemplate.render_stac("sentinel-2/valid_scene")

    assert "Runtime error rendering template" in str(error.value)


@mark.asyncio
async def test_empty_template() -> None:
    env = Environment(enable_cache=False)
    geotemplate = env.get_geotemplate_from_source("")

    with raises(GeoTemplateJsonError) as error:
        await geotemplate.render_stac("sentinel-2/valid_scene")

    assert "Error decoding JSON" in str(error.value)


@mark.asyncio
@mark.parametrize("template_name", ["stac_error.j2"])
async def test_stac_error(geotemplate: GeoTemplate) -> None:
    with raises(GeoTemplateStacError) as error:
        await geotemplate.render_stac("sentinel-2-l2a/valid_scene")

    assert "Error creating STAC Item" in str(error.value)


@mark.asyncio
@mark.parametrize("template_name", ["collection.j2"])
async def test_stac_type_error(geotemplate: GeoTemplate) -> None:
    with raises(GeoTemplateStacError) as error:
        await geotemplate.render_stac("sentinel-2-l2a/valid_scene")

    assert "Entity is not a STAC Item" in str(error.value)


@mark.asyncio
@mark.parametrize("template_name", ["validation_error.j2", "no_bbox.j2"])
async def test_stac_validation_error(geotemplate: GeoTemplate) -> None:
    with raises(GeoTemplateStacError) as error:
        await geotemplate.render_stac("sentinel-2-l2a/valid_scene", validate=True)

    assert "Error validating STAC Item" in str(error.value)


@mark.asyncio
@mark.parametrize("template_name", ["potsdam.j2"])
async def test_potsdam(geotemplate: GeoTemplate) -> None:
    item = await geotemplate.render_stac(
        path.join(TEST_DATA_DIRECTORY, "potsdam/dsm_potsdam_02_10.tif")
    )

    assert item.id == "dsm_potsdam_02_10"

    # Raises an exception if the item is invalid
    item.validate()
