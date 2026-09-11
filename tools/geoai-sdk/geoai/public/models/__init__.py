"""
geoai.public.models

Model classes - User-facing model implementations.
"""

from typing import Any, Dict, List, Optional

from geoai.public.models.eoos import EOOS
from geoai.public.models.mars import MARS

__all__ = ["EOOS", "MARS", "list", "get"]

# Registry of all available models
_MODEL_REGISTRY = {"eoos": EOOS, "mars": MARS}


def list() -> List[Dict[str, Any]]:
    """
    List all available models with their requirements.

    Returns:
        List of dictionaries with model information:
        - name: Model name (lowercase)
        - class_name: Python class name
        - model_id: Model specification ID
        - model_name: Display name
        - description: Model description
        - supported_collections: List of supported collection names
        - required_bands: List of required spectral bands

    Example:
        >>> from geoai import models
        >>>
        >>> for model_info in models.list():
        ...     print(f"{model_info['name']}: {model_info['supported_collections']}")
        eoos: ['naip', 'sentinel-2-l2a']
        mars: ['naip', 'sentinel-2-l2a']
    """
    model_list = []

    for name, model_class in _MODEL_REGISTRY.items():
        try:
            info = model_class.get_info()
            model_list.append(
                {
                    "name": name,
                    "class_name": model_class.__name__,
                    "model_id": info.get("model_id"),
                    "model_name": info.get("model_name"),
                    "description": info.get("description"),
                    "supported_collections": info.get("data_requirements", {}).get(
                        "supported_collections", []
                    ),
                    "required_bands": info.get("data_requirements", {}).get("required_bands", []),
                    "preferred_resolution_meters": info.get("data_requirements", {}).get(
                        "preferred_resolution_meters"
                    ),
                }
            )
        except Exception as e:
            # Skip models that fail to load
            print(f"Warning: Could not load model {name}: {e}")

    return model_list


def get(name: str) -> Optional[Dict[str, Any]]:
    """
    Get information about a specific model.

    Args:
        name: Model name (case-insensitive, e.g., "eoos", "mars")

    Returns:
        Dictionary with model information, or None if not found

    Example:
        >>> from geoai import models
        >>>
        >>> model_info = models.get("eoos")
        >>> print(model_info["supported_collections"])
        ['naip', 'sentinel-2-l2a']
        >>>
        >>> print(model_info["required_bands"])
        ['red', 'green', 'blue']
    """
    name_lower = name.lower()

    if name_lower not in _MODEL_REGISTRY:
        return None

    model_class = _MODEL_REGISTRY[name_lower]

    try:
        info = model_class.get_info()
        return {
            "name": name_lower,
            "class_name": model_class.__name__,
            "class": model_class,
            "model_id": info.get("model_id"),
            "model_name": info.get("model_name"),
            "description": info.get("description"),
            "data_requirements": info.get("data_requirements", {}),
        }
    except Exception as e:
        print(f"Warning: Could not load model {name}: {e}")
        return None
