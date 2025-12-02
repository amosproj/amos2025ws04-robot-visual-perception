# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from __future__ import annotations
from pathlib import Path

import numpy as np
import torch
from typing import Callable, Literal, Optional

from common.config import config
from common.core.contracts import DepthEstimator

# Factories let us swap depth estimation backends without changing call sites.
DepthEstimatorFactory = Callable[[Optional[Path]], DepthEstimator]

_depth_estimator: Optional[DepthEstimator] = None


def register_depth_estimator(factory: DepthEstimatorFactory) -> None:
    """Register a factory used to build the singleton depth estimator."""
    global _depth_estimator_factory, _depth_estimator
    _depth_estimator_factory = factory
    _depth_estimator = None


def get_depth_estimator(midas_cache_directory: Optional[Path] = None) -> DepthEstimator:
    """Return the active depth estimator instance, creating it on first use."""
    global _depth_estimator
    if _depth_estimator is None:
        _depth_estimator = _depth_estimator_factory(midas_cache_directory)
    return _depth_estimator


class MiDasDepthEstimator(DepthEstimator):
    """Default depth estimator backed by MiDaS models."""

    def __init__(
        self,
        midas_cache_directory: Optional[Path] = None,
        model_type: Literal["MiDaS_small", "DPT_Hybrid", "DPT_Large"] = "MiDaS_small",
        midas_model: str = "intel-isl/MiDaS",
    ) -> None:
        """Initialize the distance estimator with MiDaS depth estimation model.

        Args:
            model_type: Type of MiDaS model to use.
            midas_model: Repository identifier for the MiDaS model.
            midas_cache_directory: Custom directory for PyTorch Hub cache.
                If None, uses PyTorch's default cache location.
        """
        self.region_size = (
            config.REGION_SIZE
        )  # size of region around bbox center to sample depth
        self.scale_factor = config.SCALE_FACTOR  # empirical calibration factor
        self.update_freq = config.UPDATE_FREQ  # frames between depth updates

        self.update_id = -1
        self.last_depths: list[float] = []
        self.model_type = model_type
        self.midas_model = midas_model
        self.device = (
            torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
        )

        if midas_cache_directory is not None:
            torch.hub.set_dir(str(midas_cache_directory))

        self.depth_estimation_model = (
            torch.hub.load(midas_model, model_type, trust_repo=True)
            .to(self.device)
            .eval()
        )
        # get MiDaS transforms
        midas_transforms = torch.hub.load(midas_model, "transforms", trust_repo=True)
        if model_type in {"DPT_Large", "DPT_Hybrid"}:
            self.transform = midas_transforms.dpt_transform
        else:
            self.transform = midas_transforms.small_transform

    def estimate_distance_m(
        self, frame_rgb: np.ndarray, dets: list[tuple[int, int, int, int, int, float]]
    ) -> list[float]:
        """Estimate distance in meters for each detection based on depth map.

        Returns list of distances in meters."""
        self.update_id += 1
        if self.update_id % self.update_freq != 0 and len(self.last_depths) == len(
            dets
        ):
            return self.last_depths
        h, w, _ = frame_rgb.shape

        input_batch = self.transform(frame_rgb).to(self.device)
        with torch.no_grad():
            prediction = self.depth_estimation_model(input_batch)
            prediction = torch.nn.functional.interpolate(
                prediction.unsqueeze(1),
                size=(h, w),
                mode="bicubic",
                align_corners=False,
            ).squeeze()
        depth_map = prediction.cpu().numpy()
        distances = []
        for x1, y1, x2, y2, _cls_id, _conf in dets:
            # extract 5x5 central region of bbox and clip to image bounds
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)
            # Define region size (odd for symmetry)
            half_size = self.region_size // 2
            x_start = max(cx - half_size, 0)
            x_end = min(cx + half_size + 1, w)
            y_start = max(cy - half_size, 0)
            y_end = min(cy + half_size + 1, h)

            region = depth_map[y_start:y_end, x_start:x_end]
            # Use mean depth value for robustness
            depth_value = max(np.mean(region), 1e-6)  # avoid div by zero

            distances.append(float(self.scale_factor / depth_value))
        self.last_depths = distances
        return distances


_depth_estimator_factory: DepthEstimatorFactory = MiDasDepthEstimator
