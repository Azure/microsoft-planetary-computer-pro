from dataclasses import dataclass
from typing import Any, Dict

from dataclasses_json import LetterCase, dataclass_json

from stacforge import BaseActivityInput


@dataclass_json(letter_case=LetterCase.CAMEL)  # type: ignore
@dataclass
class GeoTemplateTransformationActivityInput(BaseActivityInput):
    """Input for transforming a scene to a STAC item using a GeoTemplate."""

    scene: str | Dict[str, Any]
    template_url: str
    items_path: str
    validate: bool = False


@dataclass_json(letter_case=LetterCase.CAMEL)  # type: ignore
@dataclass
class CreateCollectionActivityInput(BaseActivityInput):
    """Input for creating a STAC collection from a list of STAC item URLs."""

    base_dir: str


class TransformationError(Exception):
    """Base class for transformation errors."""

    def __init__(self, message: str):
        super().__init__()
        self.message = message

    def __str__(self) -> str:
        return self.message
