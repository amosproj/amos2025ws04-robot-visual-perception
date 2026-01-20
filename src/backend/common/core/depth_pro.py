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
from common.core.contracts import DepthEstimator, Detection
from common.core.depth_utils import resize_to_frame

import depth_pro  # type: ignore

logger = logging.getLogger(__name__)


class DepthProEstimator(DepthEstimator):
    """Depth estimator backed by Apple's ML Depth Pro."""

    def __init__(
        self,
        cache_directory: Optional[Path] = None,
        model_name: str = config.DEPTH_PRO_MODEL,
    ) -> None:
        # depth_pro import is now strict at module level.

        self.region_size = config.REGION_SIZE
        self.scale_factor = config.SCALE_FACTOR
        self.update_freq = config.UPDATE_FREQ

        self.update_id = -1
        self.last_depths: list[float] = []

        self.cache_directory = cache_directory or config.DEPTH_PRO_CACHE_DIR
        self.model_name = model_name

        logger.info("Loading Depth Pro model...")

        self.device = (
            torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
        )

        try:
            self.model, self.transform = depth_pro.create_model_and_transforms(
                device=self.device, aspect_ratio=1.0
            )
            self.model.eval()
        except Exception as e:
            logger.error(f"Failed to initialize Depth Pro: {e}")
            raise

    def estimate_distance_m(
        self, frame_rgb: np.ndarray, dets: list[Detection]
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
        image_pil = Image.fromarray(frame_rgb)
        image_tensor = self.transform(image_pil)

        with torch.no_grad():
            prediction = self.model.infer(image_tensor, f_px=None)

        depth = prediction["depth"]

        if isinstance(depth, torch.Tensor):
            depth = depth.cpu().numpy()

        return resize_to_frame(depth, output_shape)

    def _distances_from_depth_map(
        self,
        depth_map: np.ndarray,
        dets: list[Detection],
    ) -> list[float]:
        dists = []
        h, w = depth_map.shape[:2]

        for det in dets:
            x1 = max(0, int(det.x1))
            y1 = max(0, int(det.y1))
            x2 = min(w, int(det.x2))
            y2 = min(h, int(det.y2))

            if x2 <= x1 or y2 <= y1:
                dists.append(0.0)
                continue

            region = depth_map[y1:y2, x1:x2]

            # Use median depth in the box as the object distance
            dist_m = float(np.median(region))
            dists.append(dist_m)

        return dists
