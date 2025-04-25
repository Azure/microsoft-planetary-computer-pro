import logging
import os
from contextlib import contextmanager
from logging.handlers import QueueHandler, QueueListener
from queue import Queue
from typing import Any, Generator

import humps  # type: ignore

from stacforge.logging.storage_table_handler import AzureStorageTableHandler

LOGGER_NAME = "stacforge"


class ContextFilter(logging.Filter):
    """Add context to log records."""

    def __init__(
        self,
        context: dict[str, Any],
    ):
        self.context = context
        super().__init__()

    def filter(self, record: logging.LogRecord) -> bool:
        for key, value in self.context.items():
            setattr(record, humps.pascalize(key), value)

        return True


class OverrideFilter(logging.Filter):
    """Override the log record's attributes."""

    def __init__(
        self,
    ):
        super().__init__()

    def filter(self, record: logging.LogRecord) -> bool:
        overrides = {
            key: value
            for key, value in vars(record).items()
            if key.endswith("_override")
        }
        for key, value in overrides.items():
            setattr(record, key[:-9], value)
            delattr(record, key)

        return True


@contextmanager
def logging_context(
    orchestration_id: str,
    context: dict[str, Any] = {},
    level: int | str = 0,
) -> Generator[None, None, None]:
    """Provide a context for asynchronous logging."""

    handler_level = os.getenv("STORAGE_TABLE_LOGS_LEVEL", logging.INFO)

    queue: Queue[Any] = Queue()

    stacforge_logger = logging.getLogger(LOGGER_NAME)
    stacforge_logger.setLevel(level)
    stacforge_logger.addHandler(QueueHandler(queue))

    handler = AzureStorageTableHandler(
        orchestration_id=orchestration_id,
        level=handler_level,
    )
    handler.addFilter(OverrideFilter())
    handler.addFilter(ContextFilter(context))

    listener = QueueListener(
        queue,
        handler,
        respect_handler_level=True,
    )
    listener.start()

    try:
        yield
    finally:
        # Stop the listener
        listener.stop()
