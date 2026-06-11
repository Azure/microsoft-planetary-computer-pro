"""
geoai.shared.exceptions

Custom exceptions for GeoAI SDK.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ValidationResult:
    """
    Result of validation check.

    Attributes:
        is_valid: True if validation passed
        errors: List of error messages (validation failures)
        warnings: List of warning messages (non-fatal issues)
        detected_resolution: Detected resolution in meters/pixel (if STAC queried)
        bands_found: List of bands found in collection (if STAC queried)
        stac_items_count: Number of STAC items found (if STAC queried)
    """

    is_valid: bool
    errors: List[str]
    warnings: List[str]
    detected_resolution: Optional[float] = None
    bands_found: Optional[List[str]] = None
    stac_items_count: Optional[int] = None

    def __str__(self):
        if self.is_valid:
            msg = "Validation passed"
            if self.warnings:
                msg += f" with {len(self.warnings)} warning(s)"
            if self.stac_items_count is not None:
                msg += f" ({self.stac_items_count} imagery items found)"
            return msg
        else:
            return f"Validation failed: {', '.join(self.errors)}"


class ValidationError(Exception):
    """Raised when validation fails"""

    def __init__(self, message: str, validation_result: ValidationResult = None):
        super().__init__(message)
        self.validation_result = validation_result
