import json
import os
import sys
from datetime import UTC, datetime
from hashlib import md5
from logging import Handler, LogRecord

import humps
from azure.core.exceptions import HttpResponseError
from azure.data.tables import TableServiceClient, UpdateMode
from azure.identity import DefaultAzureCredential
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_fixed,
)

from stacforge.utils import get_cloud

RETRIES = 3
WAIT_SECONDS = 1

# skip natural LogRecord attributes
# http://docs.python.org/library/logging.html#logrecord-attributes
_RESERVED_ATTRS = frozenset(
    (
        "asctime",
        "args",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "message",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    )
)


class AzureStorageTableHandler(Handler):
    """A logging handler that emits log records to an Azure Storage Table."""

    def __init__(
        self,
        orchestration_id: str,
        level: int | str = 0,
    ):
        super().__init__(level)

        self._orchestration_id = orchestration_id

        # Get the Azure Storage Table service account
        table_service_account = os.getenv("LOGS_STORAGE_ACCOUNT") or os.getenv(
            "AzureWebJobsStorage__accountName"
        )
        if table_service_account is None:
            raise ValueError("No logs storage account configured")

        # Get the Azure Storage Table name
        table_name = os.getenv("LOGS_TABLE", "logs")
        if table_name is None:
            raise ValueError("Missing LOGS_TABLE environment variable")

        # Create the Azure Storage Table client
        self._credential = DefaultAzureCredential(
            authority=get_cloud().endpoints.active_directory,
        )
        table_service_endpoint = f"https://{table_service_account}.table.{get_cloud().suffixes.storage_endpoint}"  # noqa: E501
        self._table_service_client = TableServiceClient(
            endpoint=table_service_endpoint,
            credential=self._credential,
        )
        self._table_client = self._table_service_client.create_table_if_not_exists(
            table_name
        )

    def __del__(self):
        # Close the managed resources
        self._table_client.close()
        self._table_service_client.close()
        self._credential.close()

    @retry(
        retry=retry_if_exception(
            lambda e: isinstance(e, HttpResponseError)
            and e.status_code is not None
            and (e.status_code >= 500 or e.status_code in (408, 429))
        ),
        stop=stop_after_attempt(RETRIES),
        wait=wait_fixed(WAIT_SECONDS),
        reraise=True,
    )
    def emit(
        self,
        record: LogRecord,
    ) -> None:
        """Emit a log record to the Azure Storage Table."""

        record_time = datetime.fromtimestamp(
            record.created,
            tz=UTC,
        )

        MAX_LENGTH = 4096
        message = record.getMessage()
        if len(message) > MAX_LENGTH:
            message = message[: MAX_LENGTH - 3] + "..."

        entity = {
            "PartitionKey": self._orchestration_id,
            "Time": record_time.isoformat().split("+")[0] + "Z",
            "Level": record.levelname,
            "Message": message,
            "Module": record.module,
            "Function": record.funcName,
        }

        entity["RowKey"] = md5(json.dumps(entity, sort_keys=True).encode()).hexdigest()

        attributes = {
            humps.pascalize(key): str(value)
            for key, value in vars(record).items()
            if key not in _RESERVED_ATTRS
        }
        entity.update(attributes)

        try:
            self._table_client.upsert_entity(
                entity=entity,
                mode=UpdateMode.REPLACE,
            )
        except HttpResponseError as e:
            print(
                f"Failed to log to Azure Storage Table: {record}, {e}",  # noqa: E501
                file=sys.stderr,
            )
