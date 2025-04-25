from dataclasses import dataclass

from dataclasses_json import LetterCase, dataclass_json


@dataclass_json(letter_case=LetterCase.CAMEL)  # type: ignore
@dataclass
class BaseActivityInput:
    """Base class for activity inputs."""

    orchestration_id: str
    orchestration_name: str
