"""
geoai.core.models.spec_loader

ModelSpecLoader - Load and validate model specifications.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ModelSpecLoader:
    """
    ModelSpecLoader - Load model specification JSON files with validation.

    Specs define:
    - Data requirements (bands, resolution, collections)
    - Processing parameters (model's internal/optimal configuration - for reference)
    - Parameters (user-overridable parameters with defaults and validation)
    - API details (endpoint format, payload structure, response format)
    - Constraints and parameters

    Example:

      ```python
      spec = ModelSpecLoader.load("microsoft/eo-os-object-detection")

      # Access spec fields
      payload_format = spec['foundry_api']['payload_format']  # 'multipart'
      required_bands = spec['data_requirements']['required_bands']  # ['red', 'green', 'blue']
      default_threshold = spec['parameters']['threshold']['default']  # 0.5
      ```
    """

    # Required top-level keys in spec
    REQUIRED_KEYS = [
        "model_id",
        "model_name",
        "model_type",
        "workflow_type",
        "data_requirements",
        "foundry_api",
        "parameters",
    ]

    # Required keys in foundry_api section
    REQUIRED_API_KEYS = [
        "endpoint_path",
        "method",
        "payload_format",
        "input_format",
        "response_format",
    ]

    @staticmethod
    def load(model_id: str, validate: bool = True) -> Dict:
        """
        Load model specification from specs/ directory.

        :param model_id: Model ID (e.g., "microsoft/eo-os-object-detection")
        :param validate: Whether to validate spec structure (default: True)
        :return: Model spec dictionary

        :raises ValueError: If model_id is unknown
        :raises FileNotFoundError: If spec file doesn't exist
        :raises ValidationError: If spec structure is invalid
        """
        # Convert model_id to filename
        filename_map = {
            "microsoft/eo-os-object-detection": "eoos.json",
            "microsoft/mars-map-autoregressive": "mars.json",
        }

        filename = filename_map.get(model_id)
        if not filename:
            raise ValueError(
                f"Unknown model_id: {model_id}. Supported: {list(filename_map.keys())}"
            )

        # Load from specs/ directory
        specs_dir = Path(__file__).parent.parent.parent / "specs"
        spec_path = specs_dir / filename

        if not spec_path.exists():
            raise FileNotFoundError(f"Model spec not found: {spec_path}")

        logger.info(f"Loading spec from {spec_path}")

        with open(spec_path, "r") as f:
            spec = json.load(f)

        # Validate spec structure if requested
        if validate:
            ModelSpecLoader.validate_spec(spec)

        logger.info(f"Loaded spec for {spec['model_id']} ({spec['model_name']})")

        return spec

    @staticmethod
    def validate_spec(spec: Dict) -> None:
        """
        Validate model spec structure.

        :param spec: Model specification dictionary

        :raises ValueError: If spec is invalid
        """
        # Check required top-level keys
        missing_keys = [key for key in ModelSpecLoader.REQUIRED_KEYS if key not in spec]
        if missing_keys:
            raise ValueError(f"Spec missing required keys: {missing_keys}")

        # Check foundry_api section
        api_spec = spec.get("foundry_api", {})
        missing_api_keys = [key for key in ModelSpecLoader.REQUIRED_API_KEYS if key not in api_spec]
        if missing_api_keys:
            raise ValueError(f"Spec foundry_api missing required keys: {missing_api_keys}")

        # Validate payload_format
        valid_formats = ["multipart", "json-base64", "json-temporal-pairs"]
        payload_format = api_spec.get("payload_format")
        if payload_format not in valid_formats:
            raise ValueError(
                f"Invalid payload_format '{payload_format}', must be one of: {valid_formats}"
            )

        # Validate input_format
        valid_input_formats = ["jpg", "tif", "png"]
        input_format = api_spec.get("input_format")
        if input_format not in valid_input_formats:
            raise ValueError(
                f"Invalid input_format '{input_format}', must be one of: {valid_input_formats}"
            )

        logger.debug(f"Spec validation passed for {spec['model_id']}")

    @staticmethod
    def list_available_models() -> List[str]:
        """
        List all available model IDs.

        :return: List of model IDs
        """
        return ["microsoft/eo-os-object-detection", "microsoft/mars-map-autoregressive"]

    @staticmethod
    def get_model_info(model_id: str) -> Dict[str, str]:
        """
        Get basic model information without loading full spec.

        :param model_id: Model ID
        :return: Dict with model name, type, and workflow type
        """
        spec = ModelSpecLoader.load(model_id, validate=False)

        return {
            "model_id": spec.get("model_id"),
            "model_name": spec.get("model_name"),
            "model_type": spec.get("model_type"),
            "workflow_type": spec.get("workflow_type"),
            "description": spec.get("description", ""),
        }
