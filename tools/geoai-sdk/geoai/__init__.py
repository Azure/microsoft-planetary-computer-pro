"""
GeoAI SDK - Unified API for Geospatial AI Models

A simple, consistent interface for running geospatial AI models on
Azure AI Foundry and Planetary Computer Pro.

Example:
    >>> import geoai
    >>> from azure.identity import DefaultAzureCredential
    >>>
    >>> credential = DefaultAzureCredential()
    >>>
    >>> # Define input, constraint, output
    >>> input = geoai.Input(
    ...     geocatalog_uri="https://geocatalog.contoso.com",
    ...     collection="naip",
    ...     credential=credential
    ... )
    >>>
    >>> constraint = geoai.Constraint(
    ...     bbox=[-122.5, 37.5, -122.0, 38.0],
    ...     datetime="2024-01-01/2024-12-31"
    ... )
    >>>
    >>> output = geoai.Output(
    ...     geocatalog_uri="https://geocatalog.contoso.com",
    ...     collection_name="results",
    ...     credential=credential
    ... )
    >>>
    >>> # Run model
    >>> model = geoai.models.EOOS(endpoint="...", credential=credential)
    >>> result = model.run(input, constraint, params={}, output=output)
"""

# Import validation utilities for custom models
from geoai.core.validation import ValidationResult, validate_model_spec

# Import models namespace
from geoai.public import models
from geoai.public.aoi_constraint import Constraint
from geoai.public.estimate_result import EstimateResult
from geoai.public.input import Input
from geoai.public.output import Output
from geoai.public.run_result import RunResult

# Initialize logging (reads GEOAI_LOG_LEVEL environment variable)
from geoai.shared.logging import setup_logging

setup_logging()

__version__ = "0.1.0"

__all__ = [
    "Input",
    "Constraint",
    "Output",
    "RunResult",
    "EstimateResult",
    "models",
    "validate_model_spec",
    "ValidationResult",
]
