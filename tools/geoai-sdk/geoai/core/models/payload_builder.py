"""
geoai.core.models.payload_builder

PayloadBuilder - Build model-specific payloads.
"""

import base64
import io
import logging
from typing import Any, Dict, List

import numpy as np
import rasterio
from PIL import Image
from rasterio.io import MemoryFile

logger = logging.getLogger(__name__)


class PayloadBuilder:
    """
    PayloadBuilder - Build model-specific request payloads based on spec configuration.

    Supports different payload formats:
    - multipart: Image files in multipart/form-data (EO-OS)
    - json-base64: Base64-encoded images in JSON (MARS)
    - json-temporal-pairs: Before/after images for temporal models (future)

    :param foundry_api_spec: The 'foundry_api' section from model spec JSON

    Example:

      ```python
      spec = ModelSpecLoader.load("microsoft/eo-os-object-detection")
      builder = PayloadBuilder(spec['foundry_api'])

      payload = builder.build(
          images=[image_bytes1, image_bytes2],
          params={"threshold": 0.6}
      )
      ```
    """

    def __init__(self, foundry_api_spec: Dict):
        """
        PayloadBuilder initializes with foundry_api spec.

        :param foundry_api_spec: 'foundry_api' section from model spec
        """
        self.spec = foundry_api_spec
        self.format = foundry_api_spec["payload_format"]
        self.input_format = foundry_api_spec.get("input_format", "jpg")

        logger.info(
            f"Initialized PayloadBuilder: format={self.format}, input_format={self.input_format}"
        )

    def build(self, images: List[Any], params: Dict) -> Any:
        """
        Build payload based on spec format.

        :param images: List of image data (bytes, numpy arrays, or preprocessed data)
        :param params: Model parameters (threshold, etc.)
        :return: Payload in format expected by model endpoint

        :raises ValueError: If format is unsupported
        """
        if self.format == "multipart":
            return self._build_multipart(images, params)
        elif self.format == "json-base64":
            return self._build_json_base64(images, params)
        elif self.format == "json-temporal-pairs":
            return self._build_temporal_pairs(images, params)
        else:
            raise ValueError(f"Unknown payload format: {self.format}")

    def _build_multipart(self, images: List[bytes], params: Dict) -> Dict:
        """
        Build multipart/form-data payload for models like EO-OS.

        Follows Azure ML BentoML endpoint format where images are sent as
        multipart files with 'images' as the field name.

        :param images: List of JPEG image bytes
        :param params: Model parameters
        :return: Dict with 'files' and 'data' keys for httpx
        """
        files = []
        for idx, img_bytes in enumerate(images):
            # Each image as a tuple: (field_name, (filename, file_object, content_type))
            files.append(("images", (f"image_{idx}.jpg", img_bytes, "image/jpeg")))

        logger.debug(f"Built multipart payload with {len(files)} images")

        return {"files": files, "data": params}  # Additional form data (threshold, etc.)

    def _build_json_base64(self, images: List[Any], params: Dict) -> Dict:
        """
        Build JSON payload with base64-encoded images.

        Supports different request formats based on spec:
        - MARS: {"image": "<base64>", "categories": [...]}
        - Default: {"inputs": "<base64>", "parameters": {...}}

        Categories default comes from spec['parameters']['categories']['default'].

        :param images: List of image data (numpy arrays or bytes)
        :param params: Model parameters
        :return: JSON-serializable dict
        """
        if not images:
            raise ValueError("No images provided for inference")

        # Process only the first image (endpoints typically accept one image at a time)
        img_data = images[0]

        # Convert image to the required format (TIF for MARS, PNG for EO-OS)
        if self.input_format == "tif":
            img_bytes = self._convert_to_tif(img_data)
        elif self.input_format == "jpg":
            img_bytes = self._convert_to_jpg(img_data)
        elif self.input_format == "png":
            img_bytes = self._convert_to_png(img_data)
        else:
            raise ValueError(f"Unsupported input_format: {self.input_format}")

        # Base64 encode
        b64_str = base64.b64encode(img_bytes).decode("utf-8")

        logger.debug(f"Built json-base64 payload for single image")

        # Build payload based on request_format in spec
        request_format = self.spec.get("request_format", {})

        # Check if this is MARS format (has "image" field in request_format)
        if "image" in request_format:
            # MARS format: {"image": "<base64>", "categories": [...]}
            payload = {"image": b64_str}

            # Add categories if specified in params
            if "categories" in params:
                payload["categories"] = params["categories"]
            elif "categories" in self.spec.get("parameters", {}):
                # Use default categories from parameters section
                payload["categories"] = self.spec["parameters"]["categories"]["default"]

            return payload
        else:
            # Default format: {"inputs": "<base64>", "parameters": {...}}
            # Filter params to only send those expected by endpoint (from request_format)
            endpoint_params = {}
            if "parameters" in request_format:
                # Only include params that are in the request_format template
                expected_param_keys = request_format["parameters"].keys()
                endpoint_params = {k: v for k, v in params.items() if k in expected_param_keys}

            return {"inputs": b64_str, "parameters": endpoint_params}

    def _convert_to_tif(self, img_data: Any) -> bytes:
        """
        Convert image data to TIF bytes.

        :param img_data: Image data (numpy array, dict with arrays, or bytes)
        :return: TIF bytes
        """
        # If already bytes, return as-is
        if isinstance(img_data, bytes):
            return img_data

        # If dict with rasterio structure (from fetcher)
        if isinstance(img_data, dict) and "arrays" in img_data:
            arrays = img_data["arrays"]
            transform = img_data.get("transform")
            crs = img_data.get("crs", "EPSG:3857")

            # Stack bands (assuming RGB order: red, green, blue)
            band_names = ["red", "green", "blue"]
            band_arrays = [arrays[b] for b in band_names if b in arrays]

            if not band_arrays:
                raise ValueError("No RGB bands found in image data")

            stacked = np.stack(band_arrays, axis=0)

            # Write to in-memory TIF
            with MemoryFile() as memfile:
                with memfile.open(
                    driver="GTiff",
                    height=stacked.shape[1],
                    width=stacked.shape[2],
                    count=len(band_arrays),
                    dtype=stacked.dtype,
                    crs=crs,
                    transform=transform,
                    compress="lzw",
                ) as dst:
                    dst.write(stacked)

                return memfile.read()

        # If numpy array (C, H, W format)
        if isinstance(img_data, np.ndarray):
            with MemoryFile() as memfile:
                with memfile.open(
                    driver="GTiff",
                    height=img_data.shape[1],
                    width=img_data.shape[2],
                    count=img_data.shape[0],
                    dtype=img_data.dtype,
                    compress="lzw",
                ) as dst:
                    dst.write(img_data)

                return memfile.read()

        raise ValueError(f"Cannot convert {type(img_data)} to TIF")

    def _convert_to_jpg(self, img_data: Any) -> bytes:
        """
        Convert image data to JPEG bytes.

        :param img_data: Image data (numpy array, dict, or bytes)
        :return: JPEG bytes
        """
        # If already bytes, assume it's JPEG
        if isinstance(img_data, bytes):
            return img_data

        # If dict with arrays
        if isinstance(img_data, dict) and "arrays" in img_data:
            arrays = img_data["arrays"]

            # Get RGB bands
            band_names = ["red", "green", "blue"]
            band_arrays = [arrays[b] for b in band_names if b in arrays]

            if not band_arrays:
                raise ValueError("No RGB bands found")

            stacked = np.stack(band_arrays, axis=0)  # (C, H, W)
            img_array = stacked.transpose(1, 2, 0)  # (H, W, C)
        elif isinstance(img_data, np.ndarray):
            # Assume (C, H, W) format
            img_array = img_data.transpose(1, 2, 0)  # (H, W, C)
        else:
            raise ValueError(f"Cannot convert {type(img_data)} to JPEG")

        # Normalize to 0-255
        if img_array.max() > 255:
            img_array = (img_array / img_array.max() * 255).astype(np.uint8)
        else:
            img_array = img_array.astype(np.uint8)

        # Convert to PIL Image and save as JPEG
        img = Image.fromarray(img_array)
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=95)

        return buffer.getvalue()

    def _convert_to_png(self, img_data: Any) -> bytes:
        """
        Convert image data to PNG bytes.

        :param img_data: Image data (numpy array, dict, or bytes)
        :return: PNG bytes
        """
        # If already bytes, assume it's PNG
        if isinstance(img_data, bytes):
            return img_data

        # If dict with arrays
        if isinstance(img_data, dict) and "arrays" in img_data:
            arrays = img_data["arrays"]

            # Get RGB bands
            band_names = ["red", "green", "blue"]
            band_arrays = [arrays[b] for b in band_names if b in arrays]

            if not band_arrays:
                raise ValueError("No RGB bands found")

            stacked = np.stack(band_arrays, axis=0)  # (C, H, W)
            img_array = stacked.transpose(1, 2, 0)  # (H, W, C)
        elif isinstance(img_data, np.ndarray):
            # Assume (C, H, W) format
            img_array = img_data.transpose(1, 2, 0)  # (H, W, C)
        else:
            raise ValueError(f"Cannot convert {type(img_data)} to PNG")

        # Normalize to 0-255
        if img_array.max() > 255:
            img_array = (img_array / img_array.max() * 255).astype(np.uint8)
        else:
            img_array = img_array.astype(np.uint8)

        # Convert to PIL Image and save as PNG
        img = Image.fromarray(img_array)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")

        return buffer.getvalue()

    def _build_temporal_pairs(self, images: List, params: Dict) -> Dict:
        """
        Build temporal pairs payload (before/after images).

        For future temporal change detection models.
        """
        raise NotImplementedError("Temporal pairs format not yet implemented")
