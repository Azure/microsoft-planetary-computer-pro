from typing import Generator
from unittest.mock import AsyncMock, Mock, patch

from azure.core.exceptions import HttpResponseError
from azure.storage.blob.aio import ContainerClient
from pytest import fixture, mark, raises
from tenacity import wait_none

from stacforge.clients import StorageClient


@fixture
def storage_client() -> Generator[StorageClient, None, None]:
    with (
        patch(
            "stacforge.clients.storage_client.DefaultAzureCredential"
        ) as credential_mock,
        patch(
            "stacforge.clients.storage_client.BlobServiceClient"
        ) as blob_service_client_mock,
    ):
        credential_mock.return_value.close = AsyncMock()
        blob_service_client_mock.return_value.close = AsyncMock()
        blob_service_client_mock.return_value.url = (
            "https://account_name.blob.core.windows.net"
        )

        container_client_mock = Mock(ContainerClient)
        container_client_mock.return_value.exists = AsyncMock(return_value=True)
        container_client_mock.return_value.create_container = AsyncMock()
        container_client_mock.return_value.close = AsyncMock()
        container_client_mock.return_value.upload_blob = AsyncMock()
        container_client_mock.return_value.walk_blobs = AsyncMock()
        container_client_mock.return_value.download_blob = AsyncMock()

        blob_service_client_mock.return_value.get_container_client = (
            container_client_mock
        )

        yield StorageClient(
            account_name="account_name",
            container_name="container_name",
        )


def test_storage_client_init(
    storage_client: StorageClient,
):
    assert storage_client._account_name == "account_name"
    assert storage_client._container_name == "container_name"
    assert not storage_client._read_only


@mark.asyncio
async def test_ensure_container_with_existing_container(
    storage_client: StorageClient,
) -> None:
    exists_mock: AsyncMock = storage_client._container_client.exists  # type: ignore
    create_container_mock: AsyncMock = storage_client._container_client.create_container  # type: ignore # noqa: E501

    await storage_client.ensure_container()

    exists_mock.assert_awaited_once()
    create_container_mock.assert_not_awaited()


@mark.asyncio
async def test_ensure_container_with_non_existing_container(
    storage_client: StorageClient,
) -> None:
    exists_mock: AsyncMock = storage_client._container_client.exists  # type: ignore
    create_container_mock: AsyncMock = storage_client._container_client.create_container  # type: ignore # noqa: E501
    exists_mock.return_value = False

    await storage_client.ensure_container()

    exists_mock.assert_awaited_once()
    create_container_mock.assert_awaited_once()


@mark.asyncio
async def test_ensure_container_with_read_only_client(
    storage_client: StorageClient,
) -> None:
    exists_mock: AsyncMock = storage_client._container_client.exists  # type: ignore
    create_container_mock: AsyncMock = storage_client._container_client.create_container  # type: ignore # noqa: E501
    storage_client._read_only = True

    with raises(ValueError):
        await storage_client.ensure_container()

    exists_mock.assert_not_awaited()
    create_container_mock.assert_not_awaited()


@mark.asyncio
async def test_close_implicit(
    storage_client: StorageClient,
) -> None:
    container_client_close_mock: AsyncMock = storage_client._container_client.close  # type: ignore # noqa: E501
    blob_service_client_close_mock: AsyncMock = (
        storage_client._blob_service_client.close  # type: ignore
    )
    credential_close_mock: AsyncMock = storage_client._credential.close  # type: ignore

    async with storage_client:
        ...

    container_client_close_mock.assert_awaited_once()
    blob_service_client_close_mock.assert_awaited_once()
    credential_close_mock.assert_awaited_once()


@mark.asyncio
async def test_close_explicit(
    storage_client: StorageClient,
) -> None:
    container_client_close_mock: AsyncMock = storage_client._container_client.close  # type: ignore # noqa: E501
    blob_service_client_close_mock: AsyncMock = (
        storage_client._blob_service_client.close  # type: ignore
    )
    credential_close_mock: AsyncMock = storage_client._credential.close  # type: ignore

    await storage_client.close()

    container_client_close_mock.assert_awaited_once()
    blob_service_client_close_mock.assert_awaited_once()
    credential_close_mock.assert_awaited_once()


@mark.asyncio
async def test_context_enter_with_read_write_client(
    storage_client: StorageClient,
) -> None:
    ensure_container_mock = AsyncMock()
    storage_client.ensure_container = ensure_container_mock  # type: ignore

    async with storage_client:
        ...

    ensure_container_mock.assert_awaited_once()


@mark.asyncio
async def test_context_enter_with_read_only_client(
    storage_client: StorageClient,
) -> None:
    ensure_container_mock = AsyncMock()
    storage_client.ensure_container = ensure_container_mock  # type: ignore
    storage_client._read_only = True

    async with storage_client:
        ...

    ensure_container_mock.assert_not_awaited()


@mark.asyncio
@mark.parametrize("overwrite", [True, False], ids=["overwrite", "no overwrite"])
async def test_upload_blob(
    overwrite: bool,
    storage_client: StorageClient,
) -> None:
    upload_blob_mock: AsyncMock = storage_client._container_client.upload_blob  # type: ignore # noqa: E501
    upload_blob_mock.return_value.url = (
        "https://account_name.blob.core.windows.net/blob_name"
    )

    result = await storage_client.upload_blob(
        name="blob_name",
        data=b"blob_data",
        overwrite=overwrite,
    )

    assert result == "https://account_name.blob.core.windows.net/blob_name"
    upload_blob_mock.assert_awaited_once_with(
        name="blob_name",
        data=b"blob_data",
        overwrite=overwrite,
    )


@mark.asyncio
async def test_upload_blob_with_read_only_client(
    storage_client: StorageClient,
) -> None:
    storage_client._read_only = True

    with raises(ValueError):
        await storage_client.upload_blob(
            name="blob_name",
            data=b"blob_data",
        )


@mark.asyncio
async def test_upload_blob_with_retry(
    storage_client: StorageClient,
) -> None:
    upload_blob_mock: AsyncMock = storage_client._container_client.upload_blob  # type: ignore # noqa: E501
    upload_blob_mock.side_effect = [
        HttpResponseError("Transient error", response=Mock(status_code=408)),
        HttpResponseError("Transient error", response=Mock(status_code=429)),
        AsyncMock(url="https://account_name.blob.core.windows.net/blob_name"),
    ]

    # Disable retry wait time
    storage_client.upload_blob.retry.wait = wait_none()  # type: ignore

    result = await storage_client.upload_blob(
        name="blob_name",
        data=b"blob_data",
        overwrite=True,
    )

    assert result == "https://account_name.blob.core.windows.net/blob_name"
    upload_blob_mock.assert_awaited_with(
        name="blob_name",
        data=b"blob_data",
        overwrite=True,
    )
    assert upload_blob_mock.await_count == 3


@mark.asyncio
async def test_download_blob(
    storage_client: StorageClient,
) -> None:
    download_blob_mock: AsyncMock = storage_client._container_client.download_blob  # type: ignore # noqa: E501
    readall_mock: AsyncMock = AsyncMock(return_value=b"blob_data")
    download_blob_mock.return_value = Mock(readall=readall_mock)

    result = await storage_client.download_blob(
        name="blob_name",
    )

    assert result == b"blob_data"
    download_blob_mock.assert_awaited_once_with(blob="blob_name")
    readall_mock.assert_awaited_once()


@mark.asyncio
async def test_download_blob_with_retry(
    storage_client: StorageClient,
) -> None:
    download_blob_mock: AsyncMock = storage_client._container_client.download_blob  # type: ignore # noqa: E501
    readall_mock: AsyncMock = AsyncMock(return_value=b"blob_data")
    download_blob_mock.side_effect = [
        HttpResponseError("Transient error", response=Mock(status_code=408)),
        HttpResponseError("Transient error", response=Mock(status_code=429)),
        Mock(readall=readall_mock),
    ]

    # Disable retry wait time
    storage_client.download_blob.retry.wait = wait_none()  # type: ignore

    result = await storage_client.download_blob(
        name="blob_name",
    )

    assert result == b"blob_data"
    download_blob_mock.assert_awaited_with(blob="blob_name")
    assert download_blob_mock.await_count == 3
    readall_mock.assert_awaited_once()


@mark.asyncio
def test_get_export_storage_client_no_config() -> None:
    with (
        patch(
            "stacforge.clients.storage_client.os.getenv",
            side_effect=lambda env_var, default=None: {
                "DATA_STORAGE_ACCOUNT": None,
                "AzureWebJobsStorage__accountName": "storage_account",
            }.get(env_var, default),
        ),
        patch(
            "stacforge.clients.storage_client.StorageClient.__init__",
            return_value=None,
        ) as constructor_mock,
    ):
        result = StorageClient.get_export_storage_client()

        constructor_mock.assert_called_once_with(
            account_name="storage_account",
            container_name="collections",
        )
        assert isinstance(result, StorageClient)


def test_get_export_storage_client_with_config() -> None:
    with (
        patch(
            "stacforge.clients.storage_client.os.getenv",
            side_effect=lambda env_var, default=None: {
                "DATA_STORAGE_ACCOUNT": "configured_account_name",
                "DATA_CONTAINER": "configured_container_name",
            }.get(env_var, default),
        ),
        patch(
            "stacforge.clients.storage_client.StorageClient.__init__",
            return_value=None,
        ) as constructor_mock,
    ):
        result = StorageClient.get_export_storage_client()

        constructor_mock.assert_called_once_with(
            account_name="configured_account_name",
            container_name="configured_container_name",
        )
        assert isinstance(result, StorageClient)


def test_get_export_storage_client_with_invalid_config() -> None:
    with patch(
        "stacforge.clients.storage_client.os.getenv",
        return_value=None,
    ):
        with raises(ValueError) as error:
            StorageClient.get_export_storage_client()
            assert error.value == "No storage account configured"


@mark.asyncio
async def test_download_blob_from_url(
    storage_client: StorageClient,
) -> None:
    storage_client._read_only = True
    with (
        patch(
            "stacforge.clients.storage_client.StorageClient.__init__",
            return_value=None,
        ) as constructor_mock,
        patch(
            "stacforge.clients.storage_client.StorageClient.__new__",
            return_value=storage_client,
        ),
        patch(
            "stacforge.clients.storage_client.StorageClient.download_blob",
            new=AsyncMock(return_value=b"blob_data"),
        ) as download_blob_mock,
    ):
        result = await StorageClient.download_blob_from_url(
            url="https://foo.blob.core.windows.net/bar/baz"
        )

        constructor_mock.assert_called_once_with(
            account_name="foo",
            container_name="bar",
            read_only=True,
        )
        download_blob_mock.assert_awaited_once_with(
            name="baz",
        )
        assert result == b"blob_data"
