from unittest.mock import Mock, patch

from azure.core.exceptions import (
    HttpResponseError,
    ResourceNotFoundError,
)

from stacforge.engine.template_loader import BlobClient, load_template_from_storage


@patch.object(
    BlobClient,
    "download_blob",
    return_value=Mock(readall=Mock(return_value=b"template")),
)
def test_load_existing_template(download_blob_mock: Mock) -> None:
    result = load_template_from_storage("https://foo.blob.core.windows.net/bar/baz")

    assert result == "template"
    assert download_blob_mock.call_count == 1


@patch.object(
    BlobClient,
    "download_blob",
    side_effect=ResourceNotFoundError("Not found"),
)
def test_load_non_existing_template(_: Mock) -> None:
    result = load_template_from_storage("https://foo.blob.core.windows.net/bar/baz")

    assert result is None


@patch(
    "stacforge.engine.template_loader.load_template_from_storage.retry.sleep",
    return_value=Mock(),  # Disable retry wait time
)
@patch.object(
    BlobClient,
    "download_blob",
    side_effect=[
        HttpResponseError("Transient error", response=Mock(status_code=408)),
        HttpResponseError("Transient error", response=Mock(status_code=408)),
        Mock(readall=Mock(return_value=b"template")),
    ],
)
def test_load_with_transient_error(download_blob_mock: Mock, _: Mock) -> None:
    result = load_template_from_storage("https://foo.blob.core.windows.net/bar/baz")

    assert result == "template"
    assert download_blob_mock.call_count == 3
