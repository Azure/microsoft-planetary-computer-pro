from dataclasses import dataclass
from typing import Optional

from dataclasses_json import LetterCase, dataclass_json
from typing_extensions import Self

from stacforge.activities.crawling import CrawlingType


@dataclass_json(letter_case=LetterCase.CAMEL)  # type: ignore
@dataclass
class StaticCatalogIngestionOrchestrationInfo:
    """Input for the bulk transformation static catalog ingestion orchestration."""

    crawling_type: CrawlingType
    source_storage_account_name: str
    source_container_name: str
    template_url: str
    target_collection_id: str
    pattern: Optional[str] = None
    index_file_path: Optional[str] = None
    index_file_is_ndjson: Optional[bool] = False
    index_file_ignore_lines_starting_with: Optional[str] = "#"
    target_geocatalog_url: Optional[str] = None
    validate: bool = False

    def check_crawling_options(self) -> Self:
        """Check the crawling options are valid."""

        if self.crawling_type == CrawlingType.INDEX:
            if self.index_file_path is None:
                raise ValueError("index_file must be provided for index crawling")
            if self.pattern is not None:
                raise ValueError(
                    "pattern must not be provided for index crawling",  # noqa: E501
                )
        elif self.index_file_path is not None:
            raise ValueError("index_file must not be provided for non-index crawling")

        return self

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """Create an instance of `StaticCatalogIngestionOrchestrationInfo`
        from a dictionary."""
        return cls.from_dict(data)
