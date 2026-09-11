"""
geoai.core.imagery.preprocessor

ImagePreprocessor - Normalize and preprocess imagery.
"""

import io
import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """
    ImagePreprocessor - Normalize, resample, and prepare imagery for models.

    Operations:
    - Resampling to target resolution
    - Normalization (0-1, 0-255, z-score)
    - Band selection and ordering
    - Clipping to valid ranges
    """

    def __init__(self):
        """Initialize ImagePreprocessor"""
        pass

    def preprocess(
        self,
        image_data: Dict,
        target_bands: List[str],
        target_size: Optional[Tuple[int, int]] = None,
        normalization: str = "0-255",
        output_format: str = "pil",
    ) -> Any:
        """
        Preprocess image data for model input.

        :param image_data: Dict from ImageFetcher with band arrays
        :param target_bands: Ordered list of bands for model (e.g., ["red", "green", "blue"])
        :param target_size: Target (width, height) in pixels, or None to keep original
        :param normalization: "0-255" (uint8), "0-1" (float), or "z-score"
        :param output_format: "numpy", "pil", or "bytes"
        :return: Preprocessed image in requested format
        """
        try:
            band_arrays = image_data["arrays"]

            # Stack bands in correct order
            stacked_bands = []
            for band_name in target_bands:
                if band_name not in band_arrays:
                    logger.warning(f"Band {band_name} not found, using zeros")
                    # Use zeros with same shape as other bands
                    ref_shape = next(iter(band_arrays.values())).shape
                    stacked_bands.append(np.zeros(ref_shape, dtype=np.float32))
                else:
                    stacked_bands.append(band_arrays[band_name].astype(np.float32))

            # Stack to (bands, height, width)
            image_array = np.stack(stacked_bands, axis=0)

            # Normalize
            if normalization == "0-255":
                # Scale to 0-255
                if image_array.max() <= 1.0:
                    image_array = image_array * 255
                image_array = np.clip(image_array, 0, 255).astype(np.uint8)
            elif normalization == "0-1":
                # Scale to 0-1
                if image_array.max() > 1.0:
                    image_array = image_array / 255.0
                image_array = np.clip(image_array, 0, 1).astype(np.float32)
            elif normalization == "z-score":
                # Z-score normalization
                mean = np.mean(image_array)
                std = np.std(image_array)
                image_array = (image_array - mean) / (std + 1e-8)
                image_array = image_array.astype(np.float32)

            # Transpose to (height, width, bands) for PIL
            image_array = np.transpose(image_array, (1, 2, 0))

            # Resize if needed
            if target_size:
                pil_image = Image.fromarray(image_array)
                pil_image = pil_image.resize(target_size, Image.BILINEAR)
                image_array = np.array(pil_image)

            logger.debug(
                f"Preprocessed image: shape={image_array.shape}, "
                f"dtype={image_array.dtype}, range=[{image_array.min()}, {image_array.max()}]"
            )

            # Convert to requested format
            if output_format == "numpy":
                return image_array
            elif output_format == "pil":
                return Image.fromarray(image_array)
            elif output_format == "bytes":
                pil_image = Image.fromarray(image_array)
                buffer = io.BytesIO()
                pil_image.save(buffer, format="JPEG", quality=95)
                return buffer.getvalue()
            else:
                raise ValueError(f"Unsupported output format: {output_format}")

        except Exception as e:
            logger.error(f"Failed to preprocess image: {e}")
            raise

    def apply_imagenet_normalization(
        self, band_arrays: Dict[str, np.ndarray], target_mean: List[float], target_std: List[float]
    ) -> Dict[str, np.ndarray]:
        """
        Apply ImageNet-style color normalization (domain adaptation).

        Matches source image statistics to target distribution (e.g., DIOR/ImageNet).
        Linear transformation: (x - src_mean) / src_std * tgt_std + tgt_mean

        :param band_arrays: Dict of band_name -> uint8 array [0, 255]
        :param target_mean: Target mean per channel [R, G, B]
        :param target_std: Target std per channel [R, G, B]
        :return: Normalized band arrays (still uint8 [0, 255])

        Example:
            >>> preprocessor = ImagePreprocessor()
            >>> # ImageNet normalization
            >>> normalized = preprocessor.apply_imagenet_normalization(
            ...     band_arrays={'red': red_array, 'green': green_array, 'blue': blue_array},
            ...     target_mean=[123.675, 116.28, 103.53],
            ...     target_std=[58.395, 57.12, 57.375]
            ... )
        """
        band_order = ["red", "green", "blue"]
        normalized = {}

        for idx, band_name in enumerate(band_order):
            if band_name not in band_arrays:
                logger.warning(f"Band {band_name} missing for color normalization, skipping")
                normalized[band_name] = band_arrays.get(band_name, np.zeros((1, 1), dtype=np.uint8))
                continue

            band_array = band_arrays[band_name].astype(np.float32)

            # Calculate source statistics
            src_mean = band_array.mean()
            src_std = band_array.std()

            # Apply linear color transfer: (x - src_mean) / src_std * tgt_std + tgt_mean
            if src_std > 1e-6:  # Avoid division by zero
                normalized_band = (band_array - src_mean) / src_std * target_std[idx] + target_mean[
                    idx
                ]
                normalized_band = np.clip(normalized_band, 0, 255).astype(np.uint8)
                logger.debug(
                    f"  {band_name}: mean {src_mean:.1f}→{target_mean[idx]:.1f}, "
                    f"std {src_std:.1f}→{target_std[idx]:.1f}"
                )
            else:
                # Constant band, just center at target mean
                normalized_band = np.full_like(band_array, target_mean[idx], dtype=np.uint8)
                logger.debug(
                    f"  {band_name}: constant value, set to target mean {target_mean[idx]:.1f}"
                )

            normalized[band_name] = normalized_band

        # Copy any other bands (if present) without normalization
        for band_name in band_arrays:
            if band_name not in normalized:
                normalized[band_name] = band_arrays[band_name]

        return normalized
