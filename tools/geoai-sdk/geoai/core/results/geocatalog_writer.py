"""
geoai.core.results.geocatalog_writer

GeoCatalogWriter - Write results to GeoCatalog as STAC items using HTTP API.
"""

import asyncio
import datetime
import json
import logging
from datetime import timedelta
from typing import Dict, List, Optional, Tuple

import httpx
import requests
from azure.storage.blob import BlobSasPermissions, generate_blob_sas

logger = logging.getLogger(__name__)


class GeoCatalogWriter:
    """
    GeoCatalogWriter - Create STAC collections and items in GeoCatalog using HTTP API.

    Uses HTTP requests approach (compatible with any Python environment).
    """

    def __init__(self, geocatalog_uri: str, credential, storage_account_key: Optional[str] = None):
        """
        Initialize GeoCatalogWriter.

        :param geocatalog_uri: GeoCatalog endpoint
        :param credential: Azure credential (for bearer token)
        :param storage_account_key: Storage account key for generating SAS tokens (required for asset publishing)
        """
        self.geocatalog_uri = geocatalog_uri.rstrip("/")
        self.credential = credential
        self.storage_account_key = storage_account_key
        self.spatio_app_id = "https://geocatalog.spatio.azure.com"
        self._access_token = None

        logger.info(f"Initialized GeoCatalog writer: {self.geocatalog_uri}")

    def _get_bearer_token(self) -> Dict[str, str]:
        """Get bearer token for Spatio API authentication."""
        if not self._access_token or datetime.datetime.fromtimestamp(
            self._access_token.expires_on
        ) < datetime.datetime.now() + timedelta(minutes=5):
            self._access_token = self.credential.get_token(f"{self.spatio_app_id}/.default")

        return {"Authorization": f"Bearer {self._access_token.token}"}

    @staticmethod
    def _redact_sas_token(url: str) -> str:
        """Remove SAS token query parameters from URL for safe logging."""
        if '?' in url:
            return url.split('?')[0] + '?[REDACTED]'
        return url

    async def _poll_operation_status(self, operation_url: str, max_wait_seconds: int = 120) -> bool:
        """
        Poll an async operation until it completes or times out (async version for true parallelism).
        Returns True if operation succeeded, False otherwise.
        """
        import time

        start_time = time.time()
        poll_interval = 1  # Start with 1 second

        logger.debug(f"Polling operation status: {operation_url}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            while time.time() - start_time < max_wait_seconds:
                try:
                    headers = self._get_bearer_token()
                    headers["Content-Type"] = "application/json"

                    # Note: operation-location URL already includes api-version parameter
                    response = await client.get(operation_url, headers=headers)

                    if response.status_code == 200:
                        operation_status = response.json()
                        status = operation_status.get("status", "Unknown")

                        # Log detailed response at DEBUG level
                        logger.debug(f"Operation status: {status}")
                        logger.debug(
                            f"Full operation response: {json.dumps(operation_status, indent=2)}"
                        )

                        if status == "Succeeded":
                            logger.info(f"Operation completed successfully")
                            return True
                        elif status in ["Failed", "Canceled"]:
                            logger.error(f"Operation failed with status: {status}")
                            logger.error(f"Operation details: {operation_status}")
                            return False
                        elif status in ["Pending", "Running"]:
                            # Still processing, wait and retry
                            await asyncio.sleep(poll_interval)
                            poll_interval = min(
                                poll_interval * 1.5, 5
                            )  # Exponential backoff up to 5s
                            continue
                        else:
                            logger.warning(f"Unknown operation status: {status}")
                            logger.warning(f"Full response: {operation_status}")
                            await asyncio.sleep(poll_interval)
                            continue
                    else:
                        logger.warning(f"Failed to get operation status: {response.status_code}")
                        await asyncio.sleep(poll_interval)
                        continue

                except Exception as e:
                    logger.warning(f"Error polling operation status: {e}")
                    await asyncio.sleep(poll_interval)
                    continue

        # Timeout
        logger.error(f"Operation polling timed out after {max_wait_seconds} seconds")
        return False

    async def write_results(
        self,
        collection_name: str,
        results_batch: List[Dict],
        blob_service_client,
        blob_container: str,
    ) -> List[str]:
        """
        Write results to GeoCatalog with parallel STAC item creation.

        Works efficiently for any number of items (1 to 1000+):
        - Single AOI: Creates 1 item (~52s collection + item)
        - Multi-AOI: Creates all items in parallel batches (~52s for collection + 50 items, ~68s for 100 items)

        Batching strategy:
        - Processes 50 items concurrently per batch
        - Prevents overwhelming API and connection pools
        - Scales gracefully from 1 to 1000+ items

        :param collection_name: Target collection name
        :param results_batch: List of result dicts, each containing:
            - results_geojson: Detection results GeoJSON
            - overlay_tif_blob: Blob path to overlay TIF
            - overlay_jpg_blob: Blob path to overlay JPEG
            - geojson_blob: Blob path to GeoJSON
            - metadata: Metadata dict (model_id, workflow_id, bbox, geometry, etc.)
        :param blob_service_client: Azure blob service client
        :param blob_container: Blob container name
        :return: List of GeoCatalog item URLs (one per successful item)
        """
        import asyncio

        num_items = len(results_batch)
        logger.info(f"Publishing {num_items} item(s) to GeoCatalog collection: {collection_name}")

        if not results_batch:
            return []

        # Step 1: Ensure collection exists (async, only once)
        await self._ensure_collection_exists(collection_name, results_batch[0]["metadata"])

        # Step 2: Generate SAS URLs for all assets in batch
        all_blob_paths = []
        for result in results_batch:
            all_blob_paths.extend(
                [result["overlay_tif_blob"], result["overlay_jpg_blob"], result["geojson_blob"]]
            )

        logger.info(f"Generating SAS URLs for {len(all_blob_paths)} assets...")
        all_sas_urls = await self._generate_sas_urls(
            blob_service_client, blob_container, all_blob_paths
        )

        # Step 3: Create STAC item payloads for all items
        item_payloads = []
        for result in results_batch:
            # Extract SAS URLs for this item
            item_sas_urls = {
                result["overlay_tif_blob"]: all_sas_urls[result["overlay_tif_blob"]],
                result["overlay_jpg_blob"]: all_sas_urls[result["overlay_jpg_blob"]],
                result["geojson_blob"]: all_sas_urls[result["geojson_blob"]],
            }

            stac_payload = self._create_stac_item_payload(
                collection_name, item_sas_urls, result["metadata"], result["results_geojson"], None
            )

            item_payloads.append(
                {"payload": stac_payload, "aoi_id": result["metadata"].get("aoi_id", "unknown")}
            )

        # Step 4: Create items in parallel batches (50 at a time for scalability)
        batch_size = 50
        all_results = []

        for batch_idx in range(0, len(item_payloads), batch_size):
            batch = item_payloads[batch_idx : batch_idx + batch_size]
            batch_num = (batch_idx // batch_size) + 1
            total_batches = (len(item_payloads) + batch_size - 1) // batch_size

            logger.info(f"Creating batch {batch_num}/{total_batches}: {len(batch)} items...")

            create_tasks = [
                self._create_single_item(collection_name, item["payload"]) for item in batch
            ]

            batch_results = await asyncio.gather(*create_tasks, return_exceptions=True)

            # Process batch results
            for idx, (result, item_info) in enumerate(zip(batch_results, batch)):
                if isinstance(result, Exception):
                    logger.error(f"Failed to create item {item_info['aoi_id']}: {result}")
                    all_results.append(None)
                else:
                    success, item_url = result
                    if success:
                        all_results.append(item_url)
                    else:
                        logger.error(f"Failed to create item {item_info['aoi_id']}")
                        all_results.append(None)

        successful = sum(1 for r in all_results if r is not None)
        logger.info(f"Publishing complete: {successful}/{num_items} items created successfully")

        # Step 5: Create render configuration (only once)
        self._create_render_config(
            collection_name, results_batch[0]["metadata"].get("output_type", "object_detection")
        )

        # Return successful URLs only
        return [url for url in all_results if url is not None]

    async def _create_single_item(
        self, collection_name: str, stac_item_payload: Dict, max_retries: int = 3
    ) -> Tuple[bool, Optional[str]]:
        """
        Create a single STAC item with retry logic (async version for parallel execution).

        :param collection_name: Collection name
        :param stac_item_payload: STAC item payload
        :param max_retries: Maximum retry attempts
        :return: (success: bool, item_url: Optional[str])
        """
        item_id = stac_item_payload["id"]
        items_endpoint = f"{self.geocatalog_uri}/stac/collections/{collection_name}/items"

        retry_delay = 5  # seconds

        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(max_retries):
                try:
                    logger.info(
                        f"Creating STAC item {item_id} (attempt {attempt + 1}/{max_retries})"
                    )

                    headers = self._get_bearer_token()
                    headers["Content-Type"] = "application/json"

                    response = await client.post(
                        items_endpoint,
                        json=stac_item_payload,
                        headers=headers,
                        params={"api-version": "2025-04-30-preview"},
                    )

                    if response.status_code in [201, 202]:
                        # If async (202), poll operation-location URL
                        if response.status_code == 202:
                            operation_location = response.headers.get(
                                "operation-location"
                            ) or response.headers.get("Location")
                            if operation_location:
                                success = await self._poll_operation_status(
                                    operation_location, max_wait_seconds=120
                                )
                                if not success:
                                    if attempt < max_retries - 1:
                                        await asyncio.sleep(retry_delay)
                                        continue
                                    else:
                                        logger.error(
                                            f"Item {item_id} creation failed after {max_retries} attempts"
                                        )
                                        return False, None

                        item_url = f"{self.geocatalog_uri}/stac/collections/{collection_name}/items/{item_id}"
                        logger.info(f"[SUCCESS] Item {item_id} created successfully")
                        return True, item_url

                    elif response.status_code == 404:
                        # Collection not ready yet
                        if attempt < max_retries - 1:
                            logger.warning(
                                f"Collection not found (404), retrying in {retry_delay}s..."
                            )
                            await asyncio.sleep(retry_delay)
                            continue
                        else:
                            logger.error(
                                f"Failed to create item {item_id}: Collection not found after {max_retries} attempts"
                            )
                            return False, None
                    else:
                        logger.error(
                            f"Failed to create item {item_id}: {response.status_code} - {response.text}"
                        )
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_delay)
                            continue
                        else:
                            return False, None

                except Exception as e:
                    logger.error(f"Error creating item {item_id}: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                    else:
                        return False, None

        return False, None

    def _create_render_config(self, collection_id: str, output_type: str):
        """
        Create render configuration for the collection.

        Maps model_type to appropriate render config:
        - object_detection → Default View (detections overlay)
        - segmentation → Segmentation View (segmentation masks)
        """
        render_config_endpoint = (
            f"{self.geocatalog_uri}/stac/collections/{collection_id}/configurations/render-options"
        )

        headers = self._get_bearer_token()
        headers["Content-Type"] = "application/json"

        # Check if render config already exists
        response = requests.get(
            render_config_endpoint,
            headers=headers,
            params={"api-version": "2025-04-30-preview"},
            timeout=60,
        )

        if response.status_code == 200:
            existing_configs = response.json()
            config_ids = [config["id"] for config in existing_configs if "id" in config]

            if "render-config" in config_ids:
                logger.info(f"Render config already exists for collection: {collection_id}")
                return

        # Create render config based on model type (not output_type which is now model_type)
        if output_type == "segmentation":
            render_json = {
                "id": "render-config",
                "name": "Segmentation View",
                "description": "Segmentation Masks on Satellite Image",
                "type": "raster-tile",
                "options": "assets=image",
                "minZoom": 6,
            }
        else:
            # Default for object_detection and other types
            render_json = {
                "id": "render-config",
                "name": "Default View",
                "description": "Overlay Detections on Satellite Image",
                "type": "raster-tile",
                "options": "assets=image",
                "minZoom": 6,
            }

        # Create the render config
        response = requests.post(
            render_config_endpoint,
            json=render_json,
            headers=headers,
            params={"api-version": "2025-04-30-preview"},
            timeout=60,
        )

        if response.status_code == 201:
            logger.info(f"Created render config for collection: {collection_id}")
        else:
            logger.warning(
                f"Failed to create render config: {response.status_code} - {response.text}"
            )

    async def _ensure_collection_exists(self, collection_id: str, metadata: Dict):
        """Ensure STAC collection exists, create if necessary using HTTP API (async version)."""
        collections_endpoint = f"{self.geocatalog_uri}/stac/collections"

        headers = self._get_bearer_token()
        headers["Content-Type"] = "application/json"

        # Try to get collection first
        response = requests.get(
            f"{collections_endpoint}/{collection_id}",
            headers=headers,
            params={"api-version": "2025-04-30-preview"},
            timeout=60,
        )

        if response.status_code == 200:
            logger.info(f"Collection {collection_id} already exists")
            return

        # Collection doesn't exist, create it
        logger.info(f"Creating new collection: {collection_id}")

        collection_payload = {
            "type": "Collection",
            "stac_version": "1.0.0",
            "id": collection_id,
            "description": f"GeoAI SDK results - {metadata.get('model_id', 'unknown')}",
            "title": f"GeoAI_{collection_id}",
            "license": "proprietary",
            "stac_extensions": [
                "https://stac-extensions.github.io/item-assets/v1.0.0/schema.json",
                "https://stac-extensions.github.io/raster/v1.1.0/schema.json",
                "https://stac-extensions.github.io/label/v1.0.1/schema.json",
            ],
            "extent": {
                "spatial": {"bbox": [metadata.get("bbox", [-180, -90, 180, 90])]},
                "temporal": {
                    "interval": [[datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"), None]]
                },
            },
            "links": [],
            "item_assets": {
                "image": {
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                    "title": "Satellite Image with Detection Overlay",
                }
            },
        }

        # Log the complete collection payload for debugging
        logger.debug(f"Complete collection payload:")
        logger.debug(json.dumps(collection_payload, indent=2))

        response = requests.post(
            collections_endpoint,
            json=collection_payload,
            headers=headers,
            params={"api-version": "2025-04-30-preview"},
            timeout=60,
        )

        if response.status_code in [201, 202, 409]:
            if response.status_code == 202:
                # Async operation - poll operation-location URL until complete (like result-service)
                operation_location = response.headers.get(
                    "operation-location"
                ) or response.headers.get("Location")
                if operation_location:
                    logger.info(f"Collection creation is async (202), polling operation URL...")
                    success = await self._poll_operation_status(
                        operation_location, max_wait_seconds=120
                    )
                    if not success:
                        logger.error(f"Collection creation operation failed or timed out")
                        raise Exception(f"Collection creation operation failed or timed out")
                    logger.info(
                        f"Collection {collection_id} successfully created (async operation completed)"
                    )
                else:
                    # No operation-location header (shouldn't happen with 202, but handle it)
                    logger.warning(
                        f"No operation-location header found for 202 response, waiting 10 seconds..."
                    )
                    await asyncio.sleep(10)
            elif response.status_code == 201:
                # Synchronous creation - still wait a bit for indexing
                logger.info(f"Collection created (201), waiting 2 seconds for indexing...")
                await asyncio.sleep(2)

            logger.info(f"Collection {collection_id} created and ready")
        else:
            logger.warning(f"Failed to create collection: {response.status_code} - {response.text}")

    async def update_collection_extent(self, collection_id: str, new_extent_bbox: List[float]):
        """
        Update collection spatial extent (for multi-AOI workflows).

        Fetches current collection, computes union with new bbox, and updates.

        :param collection_id: Collection ID
        :param new_extent_bbox: New bbox to union with existing [minx, miny, maxx, maxy]
        """
        from geoai.core.spatial.geometry_utils import union_bboxes

        collections_endpoint = f"{self.geocatalog_uri}/stac/collections"

        headers = self._get_bearer_token()
        headers["Content-Type"] = "application/json"

        # Get current collection
        response = requests.get(
            f"{collections_endpoint}/{collection_id}",
            headers=headers,
            params={"api-version": "2025-04-30-preview"},
            timeout=60,
        )

        if response.status_code != 200:
            logger.warning(f"Failed to get collection for extent update: {response.status_code}")
            return

        collection_data = response.json()

        # Get current spatial extent
        current_extent = collection_data.get("extent", {}).get("spatial", {}).get("bbox", [[]])
        if not current_extent or not current_extent[0]:
            # No existing extent, use new one
            updated_bbox = new_extent_bbox
        else:
            # Union with existing
            current_bbox = current_extent[0]  # First bbox
            updated_bbox = union_bboxes(current_bbox, new_extent_bbox)

        # Update collection extent
        collection_data["extent"]["spatial"]["bbox"] = [updated_bbox]

        # PUT request to update collection (PATCH not supported, use PUT)
        response = requests.put(
            f"{collections_endpoint}/{collection_id}",
            json=collection_data,
            headers=headers,
            params={"api-version": "2025-04-30-preview"},
            timeout=60,
        )

        if response.status_code in [200, 201, 202]:
            logger.info(f"Updated collection {collection_id} extent to {updated_bbox}")
        else:
            logger.warning(
                f"Failed to update collection extent: {response.status_code} - {response.text}"
            )

    async def _generate_sas_urls(
        self, blob_service_client, container_name: str, blob_paths: list
    ) -> Dict[str, str]:
        """
        Generate SAS URLs for blob assets.

        Tries user delegation key (Azure AD) first, falls back to account key.
        This matches Azure best practices and AI Workflow behavior.

        Required Azure RBAC roles for user delegation:
        - Storage Blob Data Contributor
        - Storage Blob Delegator
        """
        expiry_date = datetime.datetime.now(datetime.timezone.utc) + timedelta(days=365)
        account_name = blob_service_client.account_name

        # Try user delegation key first (Azure AD-based, more secure)
        delegation_key = None
        try:
            delegation_key = await blob_service_client.get_user_delegation_key(
                key_start_time=datetime.datetime.now(datetime.timezone.utc),
                key_expiry_time=datetime.datetime.now(datetime.timezone.utc) + timedelta(days=7),
            )
            logger.info("[INFO] Using user delegation key for SAS tokens (Azure AD-based)")
            logger.info("   No storage account key needed - using your Azure identity")
        except Exception as e:
            logger.warning(f"[WARNING] Could not get user delegation key: {e}")
            logger.info("   Falling back to account key authentication")

        sas_urls = {}
        for blob_path in blob_paths:
            if delegation_key:
                # Preferred: User delegation SAS (Azure AD)
                sas_token = generate_blob_sas(
                    account_name=account_name,
                    container_name=container_name,
                    blob_name=blob_path,
                    user_delegation_key=delegation_key,
                    permission=BlobSasPermissions(read=True),
                    expiry=expiry_date,
                )
            else:
                # Fallback: Account key SAS (requires storage_account_key)
                if not self.storage_account_key:
                    raise ValueError(
                        "[ERROR] storage_account_key is required when Azure AD delegation is not available.\n"
                        "   Choose one option:\n"
                        "   1. [RECOMMENDED] Grant 'Storage Blob Delegator' role to your Azure identity:\n"
                        "      az role assignment create --assignee $USER_ID \\\n"
                        "        --role 'Storage Blob Delegator' \\\n"
                        "        --scope /subscriptions/.../storageAccounts/...\n"
                        "   2. OR provide storage_account_key:\n"
                        "      Output(..., storage_account_key=os.getenv('STORAGE_ACCOUNT_KEY'))"
                    )

                sas_token = generate_blob_sas(
                    account_name=account_name,
                    container_name=container_name,
                    blob_name=blob_path,
                    account_key=self.storage_account_key,
                    permission=BlobSasPermissions(read=True),
                    expiry=expiry_date,
                )

            sas_url = f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_path}?{sas_token}"
            sas_urls[blob_path] = sas_url

        token_type = "user delegation (Azure AD)" if delegation_key else "account key"
        expiry_days = 365 if delegation_key else 30
        logger.info(
            f"Generated {len(sas_urls)} SAS URLs using {token_type} with {expiry_days}-day expiry"
        )
        return sas_urls

    def _create_stac_item_payload(
        self,
        collection_id: str,
        sas_urls: Dict[str, str],
        metadata: Dict,
        results_geojson: Dict,
        blob_paths: Optional[Dict] = None,
    ) -> Dict:
        """Create STAC item payload matching AI Workflow structure exactly."""
        # Generate unique item ID with timestamp and microseconds for uniqueness
        # (prevents collisions when multiple AOIs processed in parallel)
        aoi_id = metadata.get("aoi_id", "aoi")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        item_id = f"{aoi_id}-Item-{timestamp}"

        # Get bbox and geometry from metadata
        bbox = metadata.get("bbox", [-180, -90, 180, 90])
        geometry = metadata.get(
            "geometry",
            {
                "type": "Polygon",
                "coordinates": [
                    [
                        [bbox[0], bbox[1]],
                        [bbox[2], bbox[1]],
                        [bbox[2], bbox[3]],
                        [bbox[0], bbox[3]],
                        [bbox[0], bbox[1]],
                    ]
                ],
            },
        )

        # Use SAS tokens for assets (required when storage account has public access disabled)
        # Extract blob URLs with SAS tokens
        overlay_tif_url = list(sas_urls.values())[0]
        geojson_url = list(sas_urls.values())[2]  # Third URL is GeoJSON

        logger.debug(f"Using blob URLs with SAS tokens (storage account requires authentication):")
        logger.debug(f"  Image: {self._redact_sas_token(overlay_tif_url)}")
        logger.debug(f"  GeoJSON: {self._redact_sas_token(geojson_url)}")

        # Extract actual detected classes from results
        detected_classes = set()
        for feature in results_geojson.get("features", []):
            label = feature.get("properties", {}).get("label")
            if label:
                detected_classes.add(label)

        # Sort for consistent ordering
        detected_classes_list = sorted(list(detected_classes))

        if not detected_classes_list:
            # Fallback if no detections
            detected_classes_list = ["detection"]

        # Define label classes using actual detected classes
        model_id = metadata.get("model_id", "unknown")
        label_classes = [{"name": "object", "classes": detected_classes_list}]
        label_description = f"Object detections from {model_id} model over satellite imagery."

        # Create STAC item payload (matching AI Workflow structure exactly)
        stac_item = {
            "id": item_id,
            "bbox": bbox,
            "type": "Feature",
            "links": [
                {
                    "rel": "collection",
                    "type": "application/json",
                    "href": f"{self.geocatalog_uri}/stac/collections/{collection_id}",
                },
                {
                    "rel": "parent",
                    "type": "application/json",
                    "href": f"{self.geocatalog_uri}/stac/collections/{collection_id}",
                },
                {"rel": "root", "type": "application/json", "href": f"{self.geocatalog_uri}/stac/"},
                {
                    "rel": "self",
                    "type": "application/geo+json",
                    "href": f"{self.geocatalog_uri}/stac/collections/{collection_id}/items/{item_id}",
                },
            ],
            "assets": {
                "image": {
                    "href": overlay_tif_url,
                    "title": "Satellite Image with Detection Overlay",
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "roles": ["data"],
                },
                "geojson": {
                    "href": geojson_url,
                    "title": "Detection Results GeoJSON",
                    "type": "application/geo+json",
                    "roles": ["data"],
                },
            },
            "geometry": geometry,
            "collection": collection_id,
            "properties": {
                "aoi_id": aoi_id,
                "datetime": datetime.datetime.now(datetime.timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
                "label:type": "vector",
                "output_type": metadata.get("output_type", "object_detection"),
                "workflow_id": metadata.get("workflow_id"),
                "label:classes": label_classes,
                "inference_model": model_id,
                "workflow_run_id": metadata.get("workflow_run_id"),
                "label:properties": ["label", "score"],
                "total_detections": len(results_geojson.get("features", [])),
                "label:description": label_description,
            },
            "stac_extensions": [
                "https://stac-extensions.github.io/raster/v1.1.0/schema.json",
                "https://stac-extensions.github.io/label/v1.0.1/schema.json",
            ],
            "stac_version": "1.0.0",
        }

        # Log the complete STAC item payload for debugging
        logger.debug(f"Complete STAC item payload:")
        logger.debug(json.dumps(stac_item, indent=2))

        return stac_item
