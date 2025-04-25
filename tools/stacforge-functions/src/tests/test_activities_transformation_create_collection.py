import json
import logging
from unittest.mock import ANY, AsyncMock, MagicMock, Mock, patch

from pytest import mark, raises

from stacforge.activities.transformation import (
    CreateCollectionActivityInput,
)
from stacforge.activities.transformation.create_collection import (
    TransformationError,
    _create_collection,
)


@mark.asyncio
@patch(
    "stacforge.activities.transformation.create_collection.StorageClient.get_export_storage_client"  # noqa: E501
)
@patch("stacforge.activities.transformation.create_collection.logging_context")
async def test_create_collection_ok(
    logging_context_mock: MagicMock,
    get_export_storage_client_mock: Mock,
) -> None:
    input = CreateCollectionActivityInput(
        orchestration_id="orchestration_id",
        orchestration_name="orchestration_name",
        base_dir="base_dir",
    )

    context = Mock(invocation_id="activity_id")

    storage_client_instance = (
        get_export_storage_client_mock.return_value.__aenter__.return_value
    )
    storage_client_instance.upload_blob = AsyncMock(return_value="collection_url")
    storage_client_instance.list_blobs = AsyncMock(
        return_value=(["stac_item1.json", "stac_item2.json"])
    )

    # Act
    result = await _create_collection(input, context)

    # Assert
    assert result == "collection_url"
    collection = {
        "stac_version": "1.0.0",
        "type": "Collection",
        "id": "temporary_collection",
        "title": "Temporary collection",
        "description": "Temporary collection for bulk import",
        "license": "other",
        "extent": {
            "spatial": {"bbox": [[-180, -90, 180, 90]]},
            "temporal": {"interval": [[None, None]]},
        },
        "links": [
            {
                "rel": "item",
                "href": item_url,
                "type": "application/json",
            }
            for item_url in ["stac_item1.json", "stac_item2.json"]
        ],
    }
    storage_client_instance.upload_blob.assert_awaited_once_with(
        name=f"{input.base_dir}/collection.json", data=json.dumps(collection)
    )
    logging_context_mock.assert_called_once_with(
        orchestration_id=input.orchestration_id,
        level=logging.DEBUG,
        context={
            "orchestration_name": input.orchestration_name,
            "activity_name": "create_collection",
            "activity_id": context.invocation_id,
        },
    )
    logging_context_mock.return_value.__enter__.assert_called_once()
    logging_context_mock.return_value.__exit__.assert_called_once()


@mark.asyncio
@patch(
    "stacforge.activities.transformation.create_collection.StorageClient.get_export_storage_client"  # noqa: E501
)
@patch("stacforge.activities.transformation.create_collection.logging_context")
async def test_create_collection_upload_blob_error(
    logging_context_mock: MagicMock,
    get_export_storage_client_mock: Mock,
    caplog,
) -> None:
    input = CreateCollectionActivityInput(
        orchestration_id="orchestration_id",
        orchestration_name="orchestration_name",
        base_dir="base_dir",
    )

    context = Mock(invocation_id="activity_id")
    storage_client_instance = (
        get_export_storage_client_mock.return_value.__aenter__.return_value
    )
    storage_client_instance.upload_blob = AsyncMock(side_effect=Exception("error"))
    storage_client_instance.list_directory = AsyncMock(
        return_value=(None, ["stac_item1.json", "stac_item2.json"])
    )

    # Act
    with raises(TransformationError) as error:
        await _create_collection(input, context)

    # Assert
    assert "Error creating collection" in str(error.value)
    logging_context_mock.assert_called_once_with(
        orchestration_id=input.orchestration_id,
        level=logging.DEBUG,
        context={
            "orchestration_name": input.orchestration_name,
            "activity_name": "create_collection",
            "activity_id": context.invocation_id,
        },
    )
    logging_context_mock.return_value.__enter__.assert_called_once()
    logging_context_mock.return_value.__exit__.assert_called_once()
    storage_client_instance.upload_blob.assert_called_once_with(
        name=f"{input.base_dir}/collection.json", data=ANY
    )

    assert caplog.records[-1].levelno == logging.ERROR
