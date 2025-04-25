from .models import (
    CrawlingActivityInput,
    CrawlingError,
    CrawlingType,
    FileCrawlingActivityInput,
    IndexCrawlingActivityInput,
)

FILE_CRAWLER_ACTIVITY_NAME = "file_crawler"
INDEX_CRAWLER_ACTIVITY_NAME = "index_crawler"

__all__ = [
    "CrawlingActivityInput",
    "CrawlingError",
    "CrawlingType",
    "FILE_CRAWLER_ACTIVITY_NAME",
    "FileCrawlingActivityInput",
    "INDEX_CRAWLER_ACTIVITY_NAME",
    "IndexCrawlingActivityInput",
]
