import logging
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from pystac import Item
from pytest import mark

from stacforge.activities.transformation.geotemplate_transform import (
    GeoTemplateTransformationActivityInput,
    _geotemplate_transform,
)
from stacforge.engine.geotemplate import GeoTemplate


@mark.asyncio
@patch(
    "stacforge.activities.transformation.geotemplate_transform._environment.get_geotemplate_from_storage"  # noqa: E501
)
@patch(
    "stacforge.activities.transformation.geotemplate_transform.StorageClient.get_export_storage_client",  # noqa: E501
)
@patch("stacforge.activities.transformation.geotemplate_transform.logging_context")
async def test_geotemplate_transform_ok(
    logging_context_mock: MagicMock,
    get_export_storage_client_mock: Mock,
    get_geotemplate_from_storage_mock: Mock,
) -> None:
    geotemplate_mock = Mock(GeoTemplate)
    item_mock = Mock(Item, id="item_id")
    render_stac_mock = AsyncMock(return_value=item_mock)
    item_mock.to_dict = Mock(return_value={"key": "value"})
    geotemplate_mock.render_stac = render_stac_mock
    get_geotemplate_from_storage_mock.return_value = geotemplate_mock

    storage_client_instance = (
        get_export_storage_client_mock.return_value.__aenter__.return_value
    )
    storage_client_instance.upload_blob = AsyncMock(return_value="blob_url")

    input = GeoTemplateTransformationActivityInput(
        orchestration_id="orchestration_id",
        orchestration_name="orchestration_name",
        scene="scene.tif",
        template_url="template_url",
        items_path="items_path",
        validate=True,
    )
    context = Mock(invocation_id="activity_id")

    # Act
    result = await _geotemplate_transform(input, context)

    # Assert
    assert result is True
    get_geotemplate_from_storage_mock.assert_called_once_with("template_url")
    render_stac_mock.assert_awaited_once_with("scene.tif", True)
    storage_client_instance.upload_blob.assert_awaited_once_with(
        name="items_path/activity_id.json", data='{"key": "value"}'
    )
    logging_context_mock.assert_called_once_with(
        orchestration_id="orchestration_id",
        context={
            "orchestration_name": "orchestration_name",
            "activity_name": "geotemplate_transform",
            "activity_id": "activity_id",
            "scene": "scene.tif",
        },
        level=logging.DEBUG,
    )
    logging_context_mock.return_value.__enter__.assert_called_once()
    logging_context_mock.return_value.__exit__.assert_called_once()


@mark.asyncio
@patch(
    "stacforge.activities.transformation.geotemplate_transform._environment.get_geotemplate_from_storage"  # noqa: E501
)
@patch("stacforge.activities.transformation.geotemplate_transform.logging_context")
async def test_geotemplate_transform_get_geotemplate_from_storage_error(
    logging_context_mock: MagicMock,
    get_geotemplate_from_storage_mock: Mock,
    caplog,
) -> None:
    # Mocking to raise an exception for get_geotemplate_from_storage
    get_geotemplate_from_storage_mock.side_effect = Exception("error")

    input = GeoTemplateTransformationActivityInput(
        orchestration_id="orchestration_id",
        orchestration_name="orchestration_name",
        scene="scene.tif",
        template_url="template_url",
        items_path="items_path",
        validate=True,
    )
    context = Mock(invocation_id="activity_id")

    with caplog.at_level(logging.WARNING):
        # Act
        result = await _geotemplate_transform(input, context)

    # Assert
    assert result is False

    # Assert the warning log is produced
    assert any(record.levelno == logging.WARNING for record in caplog.records)
    assert any(
        "Transformation failed for scene" in record.message for record in caplog.records
    )

    logging_context_mock.assert_called_once_with(
        orchestration_id="orchestration_id",
        context={
            "orchestration_name": "orchestration_name",
            "activity_name": "geotemplate_transform",
            "activity_id": "activity_id",
            "scene": "scene.tif",
        },
        level=logging.DEBUG,
    )

    assert caplog.records[-1].levelno == logging.WARNING


@mark.asyncio
@patch(
    "stacforge.activities.transformation.geotemplate_transform._environment.get_geotemplate_from_storage"  # noqa: E501
)
@patch("stacforge.activities.transformation.geotemplate_transform.logging_context")
async def test_geotemplate_transform_render_stac_error(
    logging_context_mock: MagicMock,
    get_geotemplate_from_storage_mock: Mock,
    caplog,
) -> None:
    geotemplate_mock = Mock(GeoTemplate)
    item_mock = Mock(Item, id="item_id")
    render_stac_mock = AsyncMock(return_value=item_mock)
    item_mock.to_dict = Mock(return_value={"key": "value"})
    geotemplate_mock.render_stac = render_stac_mock
    get_geotemplate_from_storage_mock.return_value = geotemplate_mock

    get_geotemplate_from_storage_mock.return_value.render_stac.side_effect = Exception(
        "error"
    )

    input = GeoTemplateTransformationActivityInput(
        orchestration_id="orchestration_id",
        orchestration_name="orchestration_name",
        scene="scene.tif",
        template_url="template_url",
        items_path="items_path",
        validate=True,
    )
    context = Mock(invocation_id="activity_id")

    with caplog.at_level(logging.WARNING):
        # Act
        result = await _geotemplate_transform(input, context)

    # Assert
    assert result is False

    # Assert the warning log is produced
    assert any(record.levelno == logging.WARNING for record in caplog.records)
    assert any(
        "Transformation failed for scene" in record.message for record in caplog.records
    )

    logging_context_mock.assert_called_once_with(
        orchestration_id="orchestration_id",
        context={
            "orchestration_name": "orchestration_name",
            "activity_name": "geotemplate_transform",
            "activity_id": "activity_id",
            "scene": "scene.tif",
        },
        level=logging.DEBUG,
    )

    assert caplog.records[-1].levelno == logging.WARNING


@mark.asyncio
@patch(
    "stacforge.activities.transformation.geotemplate_transform._environment.get_geotemplate_from_storage"  # noqa: E501
)
@patch(
    "stacforge.activities.transformation.geotemplate_transform.StorageClient.get_export_storage_client",  # noqa: E501
)
@patch("stacforge.activities.transformation.geotemplate_transform.logging_context")
async def test_geotemplate_transform_upload_blob_error(
    logging_context_mock: MagicMock,
    get_export_storage_client_mock: Mock,
    get_geotemplate_from_storage_mock: Mock,
    caplog,
) -> None:
    geotemplate_mock = Mock(GeoTemplate)
    item_mock = Mock(Item, id="item_id")
    render_stac_mock = AsyncMock(return_value=item_mock)
    item_mock.to_dict = Mock(return_value={"key": "value"})
    geotemplate_mock.render_stac = render_stac_mock
    get_geotemplate_from_storage_mock.return_value = geotemplate_mock

    storage_client_instance = (
        get_export_storage_client_mock.return_value.__aenter__.return_value
    )

    storage_client_instance.upload_blob.side_effect = Exception("error")

    input = GeoTemplateTransformationActivityInput(
        orchestration_id="orchestration_id",
        orchestration_name="orchestration_name",
        scene="scene.tif",
        template_url="template_url",
        items_path="items_path",
        validate=True,
    )
    context = Mock(invocation_id="activity_id")

    with caplog.at_level(logging.WARNING):
        # Act
        result = await _geotemplate_transform(input, context)

    # Assert
    assert result is False

    # Assert the warning log is produced
    assert any(record.levelno == logging.WARNING for record in caplog.records)
    assert not any("Uploading STAC item" in record.message for record in caplog.records)

    logging_context_mock.assert_called_once_with(
        orchestration_id="orchestration_id",
        context={
            "orchestration_name": "orchestration_name",
            "activity_name": "geotemplate_transform",
            "activity_id": "activity_id",
            "scene": "scene.tif",
        },
        level=logging.DEBUG,
    )

    assert caplog.records[-1].levelno == logging.WARNING
