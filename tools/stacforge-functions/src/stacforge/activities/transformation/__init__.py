from .models import (
    CreateCollectionActivityInput,
    GeoTemplateTransformationActivityInput,
    TransformationError,
)

CREATE_COLLECTION_ACTIVITY_NAME = "create_collection"
GEOTEMPLATE_TRANSFORM_ACTIVITY_NAME = "geotemplate_transform"

__all__ = [
    "CREATE_COLLECTION_ACTIVITY_NAME",
    "CreateCollectionActivityInput",
    "GEOTEMPLATE_TRANSFORM_ACTIVITY_NAME",
    "GeoTemplateTransformationActivityInput",
    "TransformationError",
]
