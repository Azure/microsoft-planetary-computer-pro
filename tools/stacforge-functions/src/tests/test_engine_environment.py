from unittest.mock import Mock, patch

from jinja2.exceptions import TemplateNotFound
from pytest import mark, raises

from stacforge.engine import Environment

BASIC_TEMPLATE = "{{ scene_info }}"


def test_environment_init() -> None:
    # The list of builtin filters is available at
    # https://jinja.palletsprojects.com/en/latest/templates/#list-of-builtin-filters
    builtin_filters = [
        "abs",
        "attr",
        "batch",
        "capitalize",
        "center",
        "count",  # Alias for length
        "d",  # Alias for default
        "default",
        "dictsort",
        "e",  # Alias for escape
        "escape",
        "filesizeformat",
        "first",
        "float",
        "forceescape",
        "format",
        "groupby",
        "indent",
        "int",
        "items",
        "join",
        "last",
        "length",
        "list",
        "lower",
        "map",
        "max",
        "min",
        "pprint",
        "random",
        "reject",
        "rejectattr",
        "replace",
        "reverse",
        "round",
        "safe",
        "select",
        "selectattr",
        "slice",
        "sort",
        "string",
        "striptags",
        "sum",
        "title",
        "tojson",
        "trim",
        "truncate",
        "unique",
        "upper",
        "urlencode",
        "urlize",
        "wordcount",
        "wordwrap",
        "xmlattr",
    ]
    geotemplate_filters = [
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
    ]
    expected_filters = builtin_filters + geotemplate_filters

    # The list of builtin functions is available at
    # https://jinja.palletsprojects.com/en/latest/templates/#list-of-global-functions
    builtin_functions = [
        "range",
        "lipsum",
        "dict",
        "cycler",
        "joiner",
        "namespace",
    ]
    geotemplate_functions = [
        "affine_transform_from_bounds",
        "affine_transform_from_origin",
        "get_json",
        "get_raster_file_info",
        "get_rasterio_dataset",
        "get_text",
        "get_xml",
        "now",
    ]
    geotemplate_globals = [
        "RE_NOFLAG",
        "RE_ASCII",
        "RE_IGNORECASE",
        "RE_LOCALE",
        "RE_UNICODE",
        "RE_MULTILINE",
        "RE_DOTALL",
        "RE_VERBOSE",
    ]
    expected_globals = builtin_functions + geotemplate_functions + geotemplate_globals

    # The list of builtin tests is available at
    # https://jinja.palletsprojects.com/en/latest/templates/#jinja-tests.filter
    builtin_tests = [
        "!=",  # Alias for ne
        "<",  # Alias for lt
        "<=",  # Alias for le
        "==",  # Alias for eq
        ">",  # Alias for gt
        ">=",  # Alias for ge
        "boolean",
        "callable",
        "defined",
        "divisibleby",
        "eq",
        "equalto",  # Alias for eq
        "escaped",
        "even",
        "false",
        "filter",
        "float",
        "ge",
        "greaterthan",  # Alias for gt
        "gt",
        "in",
        "integer",
        "iterable",
        "le",
        "lessthan",  # Alias for lt
        "lower",
        "lt",
        "mapping",
        "ne",
        "none",
        "number",
        "odd",
        "sameas",
        "sequence",
        "string",
        "test",
        "true",
        "undefined",
        "upper",
    ]
    geotemplate_tests = [
        "contains",
        "ends_with",
        "starts_with",
    ]
    expected_tests = builtin_tests + geotemplate_tests

    env = Environment()

    assert env._environment.loader
    assert env._environment.bytecode_cache
    assert set(env._environment.filters.keys()) == set(expected_filters)
    assert set(env._environment.globals.keys()) == set(expected_globals)
    assert set(env._environment.tests.keys()) == set(expected_tests)


def test_add_filter() -> None:
    env = Environment()

    def test_filter() -> None:
        pass

    env.add_filter("test_filter", test_filter)

    assert env._environment.filters["test_filter"] == test_filter


def test_add_function() -> None:
    env = Environment()

    def test_function() -> None:
        pass

    env.add_function("test_function", test_function)

    assert env._environment.globals["test_function"] == test_function


def test_add_test() -> None:
    env = Environment()

    def test_test() -> None:
        pass

    env.add_test("test_test", test_test)

    assert env._environment.tests["test_test"] == test_test


def test_add_global_variable() -> None:
    env = Environment()

    env.add_global_variable("test_variable", "test_value")

    assert env._environment.globals["test_variable"] == "test_value"


@mark.asyncio
async def test_get_geotemplate_from_source() -> None:
    env = Environment(enable_cache=False)

    template = env.get_geotemplate_from_source(BASIC_TEMPLATE)
    result = await template.render_text("test_value")

    assert result == "test_value"


@mark.asyncio
@patch(
    "stacforge.engine.environment.load_template_from_storage",
    return_value=BASIC_TEMPLATE,
)
async def test_get_geotemplate_from_storage(
    load_template_from_storage_mock: Mock,
) -> None:
    env = Environment(enable_cache=False)

    template = env.get_geotemplate_from_storage("foo")
    result = await template.render_text("test_value")

    assert result == "test_value"
    assert load_template_from_storage_mock.called_with("foo")
    assert load_template_from_storage_mock.call_count == 1


@patch(
    "stacforge.engine.environment.load_template_from_storage",
    return_value=BASIC_TEMPLATE,
)
def test_cached_geotemplate(load_template_from_storage: Mock) -> None:
    env = Environment(enable_cache=True)
    env.clear_cache()

    env.get_geotemplate_from_storage("foo")
    load_template_from_storage.reset_mock()
    env.get_geotemplate_from_storage("foo")

    assert not load_template_from_storage.called


@patch("stacforge.engine.environment.load_template_from_storage", return_value=None)
def test_non_existing_template(_: Mock) -> None:
    env = Environment(enable_cache=False)

    with raises(TemplateNotFound):
        env.get_geotemplate_from_storage("foo")
