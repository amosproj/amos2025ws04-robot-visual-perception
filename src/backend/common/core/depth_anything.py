# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import torch
from PIL import Image

from common.config import config
from common.core.contracts import DepthEstimator
from common.core.depth_utils import calculate_distances, resize_to_frame

try:
    from transformers import (  # type: ignore[import-untyped]
        AutoImageProcessor,
        AutoModelForDepthEstimation,
    )
except ImportError:
    AutoImageProcessor = None  # type: ignore
    AutoModelForDepthEstimation = None  # type: ignore

logger = logging.getLogger(__name__)


class DepthAnythingV2Estimator(DepthEstimator):
    """Depth estimator backed by Depth Anything V2 via Hugging Face Transformers."""

    def __init__(
        self,
        cache_directory: Optional[Path] = None,
        model_name: str = config.DEPTH_ANYTHING_MODEL,
    ) -> None:
        if AutoImageProcessor is None or AutoModelForDepthEstimation is None:
            raise ImportError(
                "transformers not installed. "
                "Please run `uv sync --extra inference` or install `transformers`."
            )

        self.region_size = config.REGION_SIZE
        self.scale_factor = config.DEPTH_ANYTHING_SCALE_FACTOR
        self.update_freq = config.UPDATE_FREQ

        self.update_id = -1
        self.last_depths: list[float] = []

        self.cache_directory = cache_directory or config.DEPTH_ANYTHING_CACHE_DIR
        self.model_name = model_name

        logger.info(f"Loading Depth Anything V2 model: {model_name}")
        logger.info(f"Cache directory: {self.cache_directory}")

        self.device = (
            torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
        )

        # Load processor and model
        self.processor = AutoImageProcessor.from_pretrained(
            model_name,
            cache_dir=self.cache_directory,
        )
        self.model = (
            AutoModelForDepthEstimation.from_pretrained(
                model_name,
                cache_dir=self.cache_directory,
            )
            .to(self.device)
            .eval()
        )

    def estimate_distance_m(
        self, frame_rgb: np.ndarray, dets: list[tuple[int, int, int, int, int, float]]
    ) -> list[float]:
        """Estimate distance in meters for each detection based on depth map."""
        self.update_id += 1
        if self.update_id % self.update_freq != 0 and len(self.last_depths) == len(
            dets
        ):
            return self.last_depths

        h, w, _ = frame_rgb.shape
        depth_map = self._predict_depth_map(frame_rgb, (h, w))
        distances = self._distances_from_depth_map(depth_map, dets)
        self.last_depths = distances
        return distances

    def _predict_depth_map(
        self, frame_rgb: np.ndarray, output_shape: tuple[int, int]
    ) -> np.ndarray:
        # Convert numpy array to PIL Image
        image = Image.fromarray(frame_rgb)

        # Prepare inputs
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)
            predicted_depth = outputs.predicted_depth

        # prediction is usually (B, H, W) -> we have batch size 1
        return resize_to_frame(predicted_depth, output_shape)

    def _distances_from_depth_map(
        self,
        depth_map: np.ndarray,
        dets: list[tuple[int, int, int, int, int, float]],
    ) -> list[float]:
        return calculate_distances(depth_map, dets, self.region_size, self.scale_factor)
