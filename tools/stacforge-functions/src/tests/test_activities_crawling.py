import logging
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from pytest import mark, raises

from stacforge.activities.crawling import (
    CrawlingError,
    FileCrawlingActivityInput,
    IndexCrawlingActivityInput,
)
from stacforge.activities.crawling.file_crawler import (
    _file_crawler,
)
from stacforge.activities.crawling.index_crawler import (
    _index_crawler,
)


@mark.asyncio
@patch("stacforge.activities.crawling.file_crawler.StorageClient")
@patch(
    "stacforge.activities.crawling.file_crawler.logging_context",
)
async def test_file_crawler_ok(
    logging_context_mock: MagicMock,
    storage_client_mock: Mock,
) -> None:
    input = FileCrawlingActivityInput(
        orchestration_id="orchestration_id",
        orchestration_name="orchestration_name",
        container_name="container_name",
        storage_account_name="storage_account_name",
        pattern="pattern",
    )
    context = Mock(invocation_id="activity_id")
    list_blobs_mock = AsyncMock(return_value=(["file1", "file2"]))
    storage_client_mock.return_value.__aenter__.return_value.list_blobs = (
        list_blobs_mock
    )

    result = await _file_crawler(input, context)

    assert result == ["file1", "file2"]
    logging_context_mock.assert_called_once_with(
        orchestration_id="orchestration_id",
        level=logging.DEBUG,
        context={
            "orchestration_name": "orchestration_name",
            "activity_name": "file_crawler",
            "activity_id": "activity_id",
        },
    )
    list_blobs_mock.assert_awaited_once_with(
        pattern="pattern",
    )


@mark.asyncio
@patch("stacforge.activities.crawling.file_crawler.StorageClient")
@patch(
    "stacforge.activities.crawling.file_crawler.logging_context",
)
async def test_file_crawler_list_blobs_error(
    logging_context_mock: MagicMock,
    storage_client_mock: Mock,
    caplog,
) -> None:
    input = FileCrawlingActivityInput(
        orchestration_id="orchestration_id",
        orchestration_name="orchestration_name",
        container_name="container_name",
        storage_account_name="storage_account_name",
        pattern="pattern",
    )
    context = Mock(invocation_id="activity_id")
    list_blobs_mock = AsyncMock(side_effect=Exception("error"))
    storage_client_mock.return_value.__aenter__.return_value.list_blobs = (
        list_blobs_mock
    )

    with raises(CrawlingError) as error:
        _ = await _file_crawler(input, context)
        assert error.value.message == "Error crawling files"

    logging_context_mock.assert_called_once_with(
        orchestration_id="orchestration_id",
        level=logging.DEBUG,
        context={
            "orchestration_name": "orchestration_name",
            "activity_name": "file_crawler",
            "activity_id": "activity_id",
        },
    )
    list_blobs_mock.assert_awaited_once_with(
        pattern="pattern",
    )

    assert caplog.records[-1].levelno == logging.ERROR


@mark.asyncio
@patch("stacforge.activities.crawling.index_crawler.StorageClient")
@patch(
    "stacforge.activities.crawling.index_crawler.logging_context",
)
async def test_index_crawler_text_file_unix_style(
    logging_context_mock: MagicMock,
    storage_client_mock: Mock,
) -> None:
    input = IndexCrawlingActivityInput(
        orchestration_id="orchestration_id",
        orchestration_name="orchestration_name",
        container_name="container_name",
        storage_account_name="storage_account_name",
        index_file="index_file",
        is_ndjson=False,
        ignore_lines_starting_with=None,
    )
    context = Mock(invocation_id="activity_id")
    download_blob_mock = AsyncMock(return_value=b"file1\nfile2\n")
    storage_client_mock.return_value.__aenter__.return_value.download_blob = (
        download_blob_mock
    )

    result = await _index_crawler(input, context)

    assert result == ["file1", "file2"]
    logging_context_mock.assert_called_once_with(
        orchestration_id="orchestration_id",
        level=logging.DEBUG,
        context={
            "orchestration_name": "orchestration_name",
            "activity_name": "index_crawler",
            "activity_id": "activity_id",
        },
    )
    download_blob_mock.assert_awaited_once_with(name="index_file")


@mark.asyncio
@patch("stacforge.activities.crawling.index_crawler.StorageClient")
@patch(
    "stacforge.activities.crawling.index_crawler.logging_context",
)
async def test_index_crawler_text_file_windows_style(
    logging_context_mock: MagicMock,
    storage_client_mock: Mock,
) -> None:
    input = IndexCrawlingActivityInput(
        orchestration_id="orchestration_id",
        orchestration_name="orchestration_name",
        container_name="container_name",
        storage_account_name="storage_account_name",
        index_file="index_file",
        is_ndjson=False,
        ignore_lines_starting_with=None,
    )
    context = Mock(invocation_id="activity_id")
    download_blob_mock = AsyncMock(return_value=b"file1\r\nfile2\r\n")
    storage_client_mock.return_value.__aenter__.return_value.download_blob = (
        download_blob_mock
    )

    result = await _index_crawler(input, context)

    assert result == ["file1", "file2"]
    logging_context_mock.assert_called_once_with(
        orchestration_id="orchestration_id",
        level=logging.DEBUG,
        context={
            "orchestration_name": "orchestration_name",
            "activity_name": "index_crawler",
            "activity_id": "activity_id",
        },
    )
    download_blob_mock.assert_awaited_once_with(name="index_file")


@mark.asyncio
@patch("stacforge.activities.crawling.index_crawler.StorageClient")
@patch(
    "stacforge.activities.crawling.index_crawler.logging_context",
)
async def test_index_crawler_ndjson_file_unix_style(
    logging_context_mock: MagicMock,
    storage_client_mock: Mock,
) -> None:
    input = IndexCrawlingActivityInput(
        orchestration_id="orchestration_id",
        orchestration_name="orchestration_name",
        container_name="container_name",
        storage_account_name="storage_account_name",
        index_file="index_file",
        is_ndjson=True,
        ignore_lines_starting_with=None,
    )
    context = Mock(invocation_id="activity_id")
    download_blob_mock = AsyncMock(
        return_value=b'{"file": "file1"}\n{"file": "file2"}\n'
    )
    storage_client_mock.return_value.__aenter__.return_value.download_blob = (
        download_blob_mock
    )

    result = await _index_crawler(input, context)

    assert result == [{"file": "file1"}, {"file": "file2"}]
    logging_context_mock.assert_called_once_with(
        orchestration_id="orchestration_id",
        level=logging.DEBUG,
        context={
            "orchestration_name": "orchestration_name",
            "activity_name": "index_crawler",
            "activity_id": "activity_id",
        },
    )
    download_blob_mock.assert_awaited_once_with(name="index_file")


@mark.asyncio
@patch("stacforge.activities.crawling.index_crawler.StorageClient")
@patch(
    "stacforge.activities.crawling.index_crawler.logging_context",
)
async def test_index_crawler_ndjson_file_windows_style(
    logging_context_mock: MagicMock,
    storage_client_mock: Mock,
) -> None:
    input = IndexCrawlingActivityInput(
        orchestration_id="orchestration_id",
        orchestration_name="orchestration_name",
        container_name="container_name",
        storage_account_name="storage_account_name",
        index_file="index_file",
        is_ndjson=True,
        ignore_lines_starting_with=None,
    )
    context = Mock(invocation_id="activity_id")
    download_blob_mock = AsyncMock(
        return_value=b'{"file": "file1"}\r\n{"file": "file2"}\r\n'
    )
    storage_client_mock.return_value.__aenter__.return_value.download_blob = (
        download_blob_mock
    )

    result = await _index_crawler(input, context)

    assert result == [{"file": "file1"}, {"file": "file2"}]
    logging_context_mock.assert_called_once_with(
        orchestration_id="orchestration_id",
        level=logging.DEBUG,
        context={
            "orchestration_name": "orchestration_name",
            "activity_name": "index_crawler",
            "activity_id": "activity_id",
        },
    )
    download_blob_mock.assert_awaited_once_with(name="index_file")


@mark.asyncio
@patch("stacforge.activities.crawling.index_crawler.StorageClient")
@patch(
    "stacforge.activities.crawling.index_crawler.logging_context",
)
async def test_index_crawler_download_blob_failure(
    logging_context_mock: MagicMock,
    storage_client_mock: Mock,
    caplog,
) -> None:
    input = IndexCrawlingActivityInput(
        orchestration_id="orchestration_id",
        orchestration_name="orchestration_name",
        container_name="container_name",
        storage_account_name="storage_account_name",
        index_file="index_file",
        is_ndjson=False,
        ignore_lines_starting_with=None,
    )
    context = Mock(invocation_id="activity_id")
    download_blob_mock = AsyncMock(side_effect=Exception("error"))
    storage_client_mock.return_value.__aenter__.return_value.download_blob = (
        download_blob_mock
    )

    with raises(CrawlingError) as error:
        await _index_crawler(input, context)
        assert error.value.message == "Error crawling index"

    logging_context_mock.assert_called_once_with(
        orchestration_id="orchestration_id",
        level=logging.DEBUG,
        context={
            "orchestration_name": "orchestration_name",
            "activity_name": "index_crawler",
            "activity_id": "activity_id",
        },
    )
    download_blob_mock.assert_awaited_once_with(name="index_file")
    assert caplog.records[-1].levelno == logging.ERROR


@mark.asyncio
@patch("stacforge.activities.crawling.index_crawler.StorageClient")
@patch(
    "stacforge.activities.crawling.index_crawler.logging_context",
)
async def test_index_crawler_ndjson_conversion_failure(
    logging_context_mock: MagicMock,
    storage_client_mock: Mock,
    caplog,
) -> None:
    input = IndexCrawlingActivityInput(
        orchestration_id="orchestration_id",
        orchestration_name="orchestration_name",
        container_name="container_name",
        storage_account_name="storage_account_name",
        index_file="index_file",
        is_ndjson=True,
        ignore_lines_starting_with=None,
    )
    context = Mock(invocation_id="activity_id")
    download_blob_mock = AsyncMock(return_value=b"this is not a valid ndjson\nnor this")
    storage_client_mock.return_value.__aenter__.return_value.download_blob = (
        download_blob_mock
    )

    with raises(CrawlingError) as error:
        await _index_crawler(input, context)
        assert error.value.message == "Error crawling index"

    logging_context_mock.assert_called_once_with(
        orchestration_id="orchestration_id",
        level=logging.DEBUG,
        context={
            "orchestration_name": "orchestration_name",
            "activity_name": "index_crawler",
            "activity_id": "activity_id",
        },
    )
    download_blob_mock.assert_awaited_once_with(name="index_file")
    assert caplog.records[-1].levelno == logging.ERROR


@mark.asyncio
@mark.parametrize("ignore", ["#", "-", "//", "/*"])
@patch("stacforge.activities.crawling.index_crawler.StorageClient")
@patch(
    "stacforge.activities.crawling.index_crawler.logging_context",
)
async def test_index_crawler_ignore_lines(
    logging_context_mock: MagicMock,
    storage_client_mock: Mock,
    ignore: str,
) -> None:
    input = IndexCrawlingActivityInput(
        orchestration_id="orchestration_id",
        orchestration_name="orchestration_name",
        container_name="container_name",
        storage_account_name="storage_account_name",
        index_file="index_file",
        is_ndjson=False,
        ignore_lines_starting_with=ignore,
    )
    context = Mock(invocation_id="activity_id")
    index_content = f"{ignore}file1\nfile2\nfile3\n"
    download_blob_mock = AsyncMock(return_value=index_content.encode())
    storage_client_mock.return_value.__aenter__.return_value.download_blob = (
        download_blob_mock
    )

    result = await _index_crawler(input, context)

    assert result == ["file2", "file3"]
    logging_context_mock.assert_called_once_with(
        orchestration_id="orchestration_id",
        level=logging.DEBUG,
        context={
            "orchestration_name": "orchestration_name",
            "activity_name": "index_crawler",
            "activity_id": "activity_id",
        },
    )
    download_blob_mock.assert_awaited_once_with(name="index_file")
