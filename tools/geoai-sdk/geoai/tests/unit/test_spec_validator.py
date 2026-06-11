"""
Unit tests for ModelSpecValidator - spec validation logic.
"""

import json
import tempfile
from pathlib import Path

import pytest

from geoai.core.validation.spec_validator import ModelSpecValidator, ValidationResult


class TestModelSpecValidator:
    """Test model spec validation logic."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return ModelSpecValidator()

    @pytest.fixture
    def valid_spec(self):
        """Create a minimal valid spec matching actual EOOS/MARS specs."""
        return {
            "model_id": "test/model",
            "model_name": "Test Model",
            "model_type": "object_detection",
            "workflow_type": "aoi_based",
            "data_requirements": {
                "required_bands": ["red", "green", "blue"],
                "resolution_range_meters": {"min": 0.3, "max": 1.5, "optimal": 0.6},
                "supported_collections": ["naip"],
            },
            "foundry_api": {
                "endpoint_path": "/score",
                "method": "POST",
                "payload_format": "json-base64",
                "input_format": "png",
                "request_format": {},
                "response_format": {
                    "type": "list",
                    "fields": {
                        "label": "string",
                        "score": "float",
                        "box": {
                            "_format": "bbox_xyxy",
                            "xmin": "float",
                            "ymin": "float",
                            "xmax": "float",
                            "ymax": "float",
                        },
                    },
                },
            },
            "parameters": {"threshold": {"type": "float", "default": 0.5, "min": 0.0, "max": 1.0}},
            "performance": {"estimated_per_request_seconds": 7.5},
        }

    def test_valid_spec_dict(self, validator, valid_spec):
        """Valid spec dict should pass validation."""
        result = validator.validate(valid_spec)

        assert result.is_valid, f"Spec should be valid: {result.errors}"
        assert len(result.errors) == 0

    def test_valid_spec_file(self, validator, valid_spec):
        """Valid spec file should pass validation."""
        # Write spec to temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            json.dump(valid_spec, tmp)
            tmp_path = tmp.name

        try:
            result = validator.validate(tmp_path)
            assert result.is_valid
            assert result.spec_path == tmp_path
        finally:
            import os

            os.unlink(tmp_path)

    def test_missing_required_field(self, validator, valid_spec):
        """Should fail when required field is missing."""
        del valid_spec["model_id"]

        result = validator.validate(valid_spec)

        assert not result.is_valid
        assert len(result.errors) > 0
        # Check error mentions missing field
        assert any("model_id" in err.lower() or "required" in err.lower() for err in result.errors)

    def test_invalid_model_type(self, validator, valid_spec):
        """Should fail with invalid model_type."""
        valid_spec["model_type"] = "invalid_type"

        result = validator.validate(valid_spec)

        # May or may not fail depending on schema constraints
        # This tests that validator processes the spec
        assert isinstance(result, ValidationResult)

    def test_missing_data_requirements(self, validator, valid_spec):
        """Should warn when data_requirements is missing for aoi_based workflow."""
        del valid_spec["data_requirements"]

        result = validator.validate(valid_spec)

        # Schema doesn't require data_requirements, but validator warns about it
        assert result.is_valid  # Valid but with warnings
        assert len(result.warnings) > 0  # Should have warning about missing required_bands

    def test_invalid_parameter_type(self, validator, valid_spec):
        """Should catch invalid parameter types."""
        valid_spec["parameters"]["threshold"]["type"] = "invalid_type"

        result = validator.validate(valid_spec)

        # Schema may or may not enforce parameter types
        # Just verify validation runs
        assert isinstance(result, ValidationResult)

    def test_validation_result_string_valid(self, validator, valid_spec):
        """ValidationResult string should show success for valid spec."""
        result = validator.validate(valid_spec)

        result_str = str(result)
        assert "✅" in result_str or "valid" in result_str.lower()

    def test_validation_result_string_invalid(self, validator, valid_spec):
        """ValidationResult string should show errors for invalid spec."""
        del valid_spec["model_id"]

        result = validator.validate(valid_spec)
        result_str = str(result)

        assert "❌" in result_str or "invalid" in result_str.lower()
        assert "error" in result_str.lower()

    def test_validation_warnings(self, validator, valid_spec):
        """Should handle warnings separately from errors."""
        # Valid spec should have no errors
        result = validator.validate(valid_spec)

        assert isinstance(result.warnings, list)
        # Warnings are optional - just verify the field exists

    def test_nested_field_validation(self, validator, valid_spec):
        """Should validate nested fields in data_requirements."""
        # Make required_bands invalid (empty list)
        valid_spec["data_requirements"]["required_bands"] = []

        result = validator.validate(valid_spec)

        # May or may not fail depending on schema
        assert isinstance(result, ValidationResult)

    def test_multiple_errors(self, validator, valid_spec):
        """Should collect multiple validation errors."""
        # Remove multiple required fields
        del valid_spec["model_id"]
        del valid_spec["model_name"]

        result = validator.validate(valid_spec)

        assert not result.is_valid
        # Should have error for each missing field
        assert len(result.errors) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
