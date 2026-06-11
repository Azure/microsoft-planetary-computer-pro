"""
spec_validator.py - Validates model specifications against the JSON schema.

This module provides validation utilities for custom model specifications,
ensuring they conform to the GeoAI SDK schema before being used.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union

try:
    import jsonschema
    from jsonschema import Draft7Validator

    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False


@dataclass
class ValidationResult:
    """
    ValidationResult contains the result of model spec validation.

    :param is_valid: Whether the spec is valid
    :param errors: List of validation error messages
    :param warnings: List of validation warnings
    :param spec_path: Path to the validated spec file
    """

    is_valid: bool
    errors: List[str]
    warnings: List[str]
    spec_path: Optional[str] = None

    def __str__(self) -> str:
        """String representation of validation result."""
        if self.is_valid:
            result = f"[VALID] Spec is valid: {self.spec_path or 'unnamed'}"
            if self.warnings:
                result += f"\n[WARNING] {len(self.warnings)} warning(s):"
                for warning in self.warnings:
                    result += f"\n   - {warning}"
            return result
        else:
            result = f"[INVALID] Spec is invalid: {self.spec_path or 'unnamed'}"
            result += f"\n   {len(self.errors)} error(s) found:"
            for error in self.errors:
                result += f"\n   - {error}"
            if self.warnings:
                result += f"\n[WARNING] {len(self.warnings)} warning(s):"
                for warning in self.warnings:
                    result += f"\n   - {warning}"
            return result


class ModelSpecValidator:
    """
    ModelSpecValidator validates model specifications against the GeoAI SDK schema.

    This class loads the JSON schema and validates user-provided model specs,
    providing detailed error messages for any validation failures.
    """

    def __init__(self, schema_path: Optional[str] = None):
        """
        ModelSpecValidator constructor.

        :param schema_path: Path to the JSON schema file (default: uses bundled schema)
        """
        if not JSONSCHEMA_AVAILABLE:
            raise ImportError(
                "jsonschema is required for spec validation. "
                "Install with: pip install jsonschema"
            )

        if schema_path is None:
            # Default to bundled schema (inside geoai/ folder)
            geoai_root = Path(__file__).parent.parent.parent
            schema_path = geoai_root / "schema" / "model_spec_schema.json"

        self.schema_path = Path(schema_path)
        self.schema = self._load_schema()
        self.validator = Draft7Validator(self.schema)

    def _load_schema(self) -> Dict:
        """Load the JSON schema from file."""
        if not self.schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {self.schema_path}")

        with open(self.schema_path, "r") as f:
            return json.load(f)

    def validate(self, spec: Union[str, Path, Dict]) -> ValidationResult:
        """
        Validate a model specification.

        :param spec: Path to spec JSON file or spec dict
        :return: ValidationResult with validation status and errors

        Example:

          ```python
          validator = ModelSpecValidator()
          result = validator.validate("my_model.json")
          if result.is_valid:
              print("Spec is valid!")
          ```
        """
        # Load spec if path provided
        spec_path = None
        if isinstance(spec, (str, Path)):
            spec_path = str(spec)
            spec_dict = self._load_spec(spec)
        else:
            spec_dict = spec

        errors = []
        warnings = []

        # Validate against schema
        schema_errors = list(self.validator.iter_errors(spec_dict))
        for error in schema_errors:
            error_path = ".".join(str(p) for p in error.path) if error.path else "root"
            errors.append(f"{error_path}: {error.message}")

        # Additional semantic validation
        semantic_warnings = self._semantic_validation(spec_dict)
        warnings.extend(semantic_warnings)

        return ValidationResult(
            is_valid=len(errors) == 0, errors=errors, warnings=warnings, spec_path=spec_path
        )

    def _load_spec(self, spec_path: Union[str, Path]) -> Dict:
        """Load spec from JSON file."""
        spec_path = Path(spec_path)
        if not spec_path.exists():
            raise FileNotFoundError(f"Spec file not found: {spec_path}")

        with open(spec_path, "r") as f:
            return json.load(f)

    def _semantic_validation(self, spec: Dict) -> List[str]:
        """
        Perform semantic validation beyond JSON schema.

        :param spec: Model spec dictionary
        :return: List of warning messages
        """
        warnings = []

        # Check if stride is compatible with chip_size
        if "processing" in spec:
            processing = spec["processing"]
            chip_size = processing.get("chip_size")
            stride = processing.get("stride")

            if chip_size and stride:
                if isinstance(chip_size, int) and isinstance(stride, int):
                    if stride > chip_size:
                        warnings.append(
                            f"processing.stride ({stride}) is larger than "
                            f"chip_size ({chip_size}), which may cause gaps"
                        )

        # Check if foundry_api.endpoint_url looks valid
        if "foundry_api" in spec:
            endpoint_url = spec["foundry_api"].get("endpoint_url", "")
            if endpoint_url and not any(
                domain in endpoint_url
                for domain in [
                    "inference.ml.azure.com",
                    "azureml.net",
                    "inference.ai.azure.com",
                    "localhost",
                ]
            ):
                warnings.append(
                    f"foundry_api.endpoint_url doesn't look like a standard "
                    f"Azure AI Foundry endpoint: {endpoint_url}"
                )

        # Check if required_bands are specified for aoi_based workflows
        if spec.get("workflow_type") == "aoi_based":
            if not spec.get("data_requirements", {}).get("required_bands"):
                warnings.append(
                    "workflow_type is 'aoi_based' but no required_bands specified. "
                    "This may cause issues with imagery selection."
                )

        return warnings


def validate_model_spec(
    spec: Union[str, Path, Dict], schema_path: Optional[str] = None
) -> ValidationResult:
    """
    Convenience function to validate a model specification.

    :param spec: Path to spec JSON file or spec dict
    :param schema_path: Optional path to custom schema file
    :return: ValidationResult

    Example:

      ```python
      from geoai import validate_model_spec

      result = validate_model_spec("my_model.json")
      print(result)
      ```
    """
    validator = ModelSpecValidator(schema_path=schema_path)
    return validator.validate(spec)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python spec_validator.py <spec_file.json>")
        sys.exit(1)

    spec_path = sys.argv[1]
    result = validate_model_spec(spec_path)
    print(result)

    sys.exit(0 if result.is_valid else 1)
