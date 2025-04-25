import logging
from json import JSONDecodeError, loads
from typing import Any, Dict, Optional

from jinja2 import Template
from jinja2.exceptions import FilterArgumentError, SecurityError, TemplateRuntimeError
from pystac import Item, STACError, STACTypeError, STACValidationError

from stacforge.logging import LOGGER_NAME

_logger = logging.getLogger(LOGGER_NAME)


class GeoTemplateRenderError(Exception):
    """Exception raised when an error occurs while rendering
    a GeoTemplate."""

    def __init__(self, message: Optional[str] = None):
        super().__init__(message)


class GeoTemplateRuntimeError(GeoTemplateRenderError):
    """Exception raised when a runtime error occurs while rendering
    a GeoTemplate."""

    def __init__(self, message: Optional[str] = None):
        super().__init__(message)


class GeoTemplateJsonError(GeoTemplateRenderError):
    """Exception raised when an error occurs while rendering
    a GeoTemplate as JSON."""

    def __init__(self, message: Optional[str] = None):
        super().__init__(message)


class GeoTemplateStacError(GeoTemplateRenderError):
    """Exception raised when an error occurs while rendering
    a GeoTemplate as a STAC Item."""

    def __init__(self, message: Optional[str] = None):
        super().__init__(message)


class GeoTemplate:
    """Wrapper around a Jinja2 template that renders scene information into
    text, JSON, or a STAC Item."""

    def __init__(
        self,
        template: Template,
    ):
        """Initializes the GeoTemplate with a Jinja2 template."""

        self._template = template

    async def render_text(
        self,
        scene_info: str | Dict[str, Any],
    ) -> str:
        """Renders the scene information into text using the template."""

        try:
            _logger.debug(f"Rendering template with scene: {scene_info}")
            text = await self._template.render_async(scene_info=scene_info)
            _logger.debug(f"Rendered text: {text}")

            return text
        except FilterArgumentError as e:
            _logger.error(f"Filter was called with invalid arguments: {e}")
            raise GeoTemplateRuntimeError(
                f"Filter was called with invalid arguments: {e}"
            )
        except SecurityError as e:
            _logger.error(f"Security error rendering template: {e}")
            raise GeoTemplateRuntimeError(
                f"Runtime security error rendering template: {e}"
            )
        except TemplateRuntimeError as e:
            _logger.error(f"Runtime error rendering template: {e}")
            raise GeoTemplateRuntimeError(f"Runtime error rendering template: {e}")
        except Exception as e:
            _logger.error(f"Error rendering template: {e}")
            raise GeoTemplateRuntimeError(f"Error rendering template: {e}")

    async def render_json(
        self,
        scene_info: str | Dict[str, Any],
    ) -> dict:
        """Renders the scene information into JSON using the template."""

        try:
            text = await self.render_text(scene_info)
            _logger.debug("Transforming rendered text to JSON")
            json = loads(text)
            _logger.debug("Transformed text to JSON")

            return json
        except JSONDecodeError as e:
            _logger.error(f"Error decoding JSON: {e}")
            raise GeoTemplateJsonError(f"Error decoding JSON: {e}")
        except GeoTemplateRuntimeError:
            raise
        except Exception as e:
            raise GeoTemplateJsonError(f"Error rendering JSON: {e}")

    async def render_stac(
        self,
        scene_info: str | Dict[str, Any],
        validate: Optional[bool] = False,
    ) -> Item:
        """Renders the scene information into a STAC Item using the template."""

        try:
            json_item = await self.render_json(scene_info)
            _logger.debug("Creating STAC Item from JSON")
            item = Item.from_dict(json_item)
            _logger.debug("Created STAC Item from JSON")

            if validate:
                # TODO: Add the same name validation applied in the GeoCatalog
                _logger.debug("Validating STAC Item")
                validation_result = item.validate()
                _logger.debug("STAC Item successfully validated")
                _logger.debug(f"Validation result: {validation_result}")

            return item
        except STACError as e:
            _logger.error(f"Error creating STAC Item: {e}")
            raise GeoTemplateStacError(f"Error creating STAC Item: {e}")
        except STACTypeError as e:
            _logger.error(f"Entity is not a STAC Item: {e}")
            raise GeoTemplateStacError(f"Entity is not a STAC Item: {e}")
        except STACValidationError as e:
            _logger.error(f"Error validating STAC Item: {e}")
            raise GeoTemplateStacError(f"Error validating STAC Item: {e}")
        except GeoTemplateJsonError:
            raise
        except GeoTemplateRuntimeError:
            raise
        except Exception as e:
            raise GeoTemplateStacError(f"Error rendering STAC Item: {e}")
