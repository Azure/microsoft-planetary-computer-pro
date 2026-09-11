"""
geoai.core.models.response_parser

ResponseParser - Parse model response outputs using spec-driven schema.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ResponseParser:
    """
    ResponseParser - Parse and normalize model responses based on spec configuration.

    Uses the response_format schema from model spec to extract fields. If the response structure changes,
    just update the spec - no code changes needed.

    Returns normalized detection format with fields as defined in spec.

    :param foundry_api_spec: The 'foundry_api' section from model spec JSON

    Example:

      ```python
      spec = ModelSpecLoader.load("microsoft/eo-os-object-detection")
      parser = ResponseParser(spec['foundry_api'])

      detections = parser.parse(response_json)
      ```
    """

    def __init__(self, foundry_api_spec: Dict):
        """
        ResponseParser initializes with foundry_api spec.

        :param foundry_api_spec: 'foundry_api' section from model spec
        """
        self.spec = foundry_api_spec
        self.response_format = foundry_api_spec.get("response_format", {})

        if not self.response_format:
            raise ValueError("response_format not found in foundry_api spec")

        logger.info(f"Initialized ResponseParser with schema: {self.response_format}")

    def parse(self, response_json: Any) -> List[Dict]:
        """
        Parse model response based on spec-driven schema.

        :param response_json: Raw JSON response from model endpoint
        :return: List of normalized detection dictionaries

        :raises ValueError: If response format doesn't match spec or is invalid
        """
        response_type = self.response_format.get("type")

        if response_type != "list":
            raise ValueError(
                f"Unsupported response type: {response_type}. Only 'list' is supported."
            )

        # Response should be a list
        if not isinstance(response_json, list):
            raise ValueError(f"Expected list response but got {type(response_json).__name__}")

        fields_schema = self.response_format.get("fields", {})

        detections = []

        for item in response_json:
            try:
                # Extract fields based on schema (auto-converts box to bbox)
                parsed_item = self._extract_fields(item, fields_schema)

                detections.append(parsed_item)

            except Exception as e:
                logger.warning(f"Failed to parse item {item}: {e}")
                continue

        logger.debug(f"Parsed {len(detections)} detections from spec-driven schema")
        return detections

    def _extract_fields(self, item: Dict, schema: Dict) -> Dict:
        """
        Recursively extract fields from item based on schema.

        Uses explicit _format declarations to convert special field types (e.g., bbox_xyxy).

        :param item: Item from response list
        :param schema: Field schema mapping field names to types
        :return: Extracted fields dictionary
        """
        result = {}

        for field_name, field_type in schema.items():
            if field_name not in item:
                logger.warning(f"Field '{field_name}' not found in response item")
                continue

            value = item[field_name]

            # Handle nested objects with special format declarations
            if isinstance(field_type, dict):
                # Check for explicit _format declaration
                format_type = field_type.get("_format")

                if format_type == "bbox_xyxy":
                    # Convert {xmin, ymin, xmax, ymax} to [x, y, w, h]
                    xmin = float(value.get("xmin", 0))
                    ymin = float(value.get("ymin", 0))
                    xmax = float(value.get("xmax", 0))
                    ymax = float(value.get("ymax", 0))
                    result["bbox"] = [xmin, ymin, xmax - xmin, ymax - ymin]
                elif format_type:
                    # Unknown format - log warning and skip conversion
                    logger.warning(
                        f"Unknown _format '{format_type}' for field '{field_name}', treating as raw value"
                    )
                    result[field_name] = value
                else:
                    # Regular nested object - recurse (exclude _format key from schema)
                    nested_schema = {k: v for k, v in field_type.items() if k != "_format"}
                    result[field_name] = self._extract_fields(value, nested_schema)
            # Handle typed fields
            elif field_type == "string":
                result[field_name] = str(value)
            elif field_type == "float":
                result[field_name] = float(value)
            elif field_type == "int":
                result[field_name] = int(value)
            elif field_type == "geojson":
                # Keep GeoJSON geometry as-is
                result[field_name] = value
            else:
                logger.warning(
                    f"Unknown field type '{field_type}' for field '{field_name}', using raw value"
                )
                result[field_name] = value

        return result
