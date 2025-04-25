from dataclasses import dataclass
from enum import Enum
from typing import Optional

from dataclasses_json import LetterCase, dataclass_json

from stacforge import BaseActivityInput


class CrawlingType(str, Enum):
    """Enumeration of crawling types."""

    FILE = "file"
    INDEX = "index"


@dataclass_json(letter_case=LetterCase.CAMEL)  # type: ignore
@dataclass
class CrawlingActivityInput(BaseActivityInput):
    """Base class for crawling activity inputs."""

    storage_account_name: str
    container_name: str


@dataclass_json(letter_case=LetterCase.CAMEL)  # type: ignore
@dataclass
class FileCrawlingActivityInput(CrawlingActivityInput):
    """Input for file and directory crawling activities."""

    pattern: Optional[str] = None


@dataclass_json(letter_case=LetterCase.CAMEL)  # type: ignore
@dataclass
class IndexCrawlingActivityInput(CrawlingActivityInput):
    """Input for index crawling activities."""

    index_file: str
    is_ndjson: Optional[bool] = False
    ignore_lines_starting_with: Optional[str] = "#"


class CrawlingError(Exception):
    """Base class for crawling errors."""

    def __init__(self, message: str):
        super().__init__()
        self.message = message

    def __str__(self) -> str:
        return self.message
