import logging
from typing import Any, Callable, Optional

from jinja2.bccache import FileSystemBytecodeCache
from jinja2.loaders import FunctionLoader
from jinja2.nodes import Template
from jinja2.sandbox import SandboxedEnvironment

from stacforge.engine.filters import GeoTemplateFilters
from stacforge.engine.functions import GeoTemplateFunctions
from stacforge.engine.geotemplate import GeoTemplate
from stacforge.engine.globals import GeoTemplateGlobals
from stacforge.engine.template_loader import load_template_from_storage
from stacforge.engine.tests import GeoTemplateTests
from stacforge.logging import LOGGER_NAME

_logger = logging.getLogger(LOGGER_NAME)


class Environment:
    """Sandboxed environment pre-configured with custom filters, functions, and test."""

    def __init__(
        self,
        enable_cache: Optional[bool] = True,
    ):
        _logger.debug("Initializing environment")

        # Create the sandboxed environment
        environment = SandboxedEnvironment(enable_async=True)
        # Set the loader to load templates from storage
        environment.loader = FunctionLoader(load_template_from_storage)
        if enable_cache:
            # Enable bytecode caching
            _logger.debug("Enabling bytecode cache")
            environment.bytecode_cache = FileSystemBytecodeCache()
        self._environment = environment

        # Inject filters into the environment
        for filter_name, filter in GeoTemplateFilters.items():
            self.add_filter(filter_name, filter)

        # Inject functions into the environment
        for function_name, function in GeoTemplateFunctions.items():
            self.add_function(function_name, function)

        # Inject tests into the environment
        for test_name, test in GeoTemplateTests.items():
            self.add_test(test_name, test)

        # Inject global variables into the environment
        for global_name, global_value in GeoTemplateGlobals.items():
            self.add_global_variable(global_name, global_value)

    def clear_cache(self) -> None:
        """Clears the environment's template cache."""

        if self._environment.bytecode_cache:
            _logger.debug("Clearing bytecode cache")
            self._environment.bytecode_cache.clear()

    def add_filter(
        self,
        name: str,
        filter: Callable,
    ) -> None:
        """Add a filter to the environment.
        Replaces any existing filter with the same name."""

        _logger.debug(f"Adding filter {name}")
        GeoTemplateFilters[name] = filter
        self._environment.filters[name] = filter

    def add_function(
        self,
        name: str,
        function: Callable,
    ) -> None:
        """Add a function to the environment.
        Replaces any existing function with the same name."""

        _logger.debug(f"Adding function {name}")
        GeoTemplateFunctions[name] = function
        self._environment.globals[name] = function

    def add_test(
        self,
        name: str,
        test: Callable,
    ) -> None:
        """Add a test to the environment.
        Replaces any existing test with the same name."""

        _logger.debug(f"Adding test {name}")
        GeoTemplateTests[name] = test
        self._environment.tests[name] = test

    def add_global_variable(
        self,
        name: str,
        value: Any,
    ) -> None:
        """Add a global variable to the environment.
        Replaces any existing global variable with the same name."""

        _logger.debug(f"Adding global variable {name}")
        GeoTemplateGlobals[name] = value
        self._environment.globals[name] = value

    def get_geotemplate_from_storage(
        self,
        blob_url: str,
    ) -> GeoTemplate:
        """Load a GeoTemplate from a blob storage URL."""

        jinja_template = self._environment.get_template(blob_url)
        geotemplate = GeoTemplate(jinja_template)

        return geotemplate

    def get_geotemplate_from_source(
        self,
        source: str,
    ) -> GeoTemplate:
        """Load a GeoTemplate from a string."""

        _logger.info("Loading GeoTemplate as source code")
        jinja_template = self._environment.from_string(source)
        geotemplate = GeoTemplate(jinja_template)

        return geotemplate

    def parse_template(self, template: str) -> Template:
        """Parse a template string and returns its AST."""

        _logger.debug("Parsing template to abstract syntax tree")
        ast = self._environment.parse(template)

        return ast
