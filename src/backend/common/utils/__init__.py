# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from common.utils.camera import (
    compute_camera_intrinsics,
    open_camera,
    read_frame,
)

from common.utils.depth import (
    calculate_distances,
    inverse_depth_to_distance,
    resize_to_frame,
)

from common.utils.detection import (
    bbox_center,
    calculate_iou,
    calculate_region_bounds,
    get_detections,
    non_maximum_supression,
    normalize_bbox_coordinates,
    unproject_bbox_center_to_camera,
    xywh_to_xyxy,
)

from common.utils.model_downloader import (
    DEFAULT_MIDAS_MODEL,
    DEFAULT_MIDAS_REPO,
    PYTORCH_HUB_CACHE,
    ensure_depth_anything_model_available,
    ensure_midas_model_available,
    ensure_yolo_model_downloaded,
    export_midas_to_onnx,
    export_yolo_to_onnx,
    get_midas_cache_dir,
    get_midas_onnx_config,
)

from common.utils.transforms import (
    calculate_adaptive_scale,
    calculate_interpolation_factor,
    letterbox,
    lerp,
    lerp_int,
    resize_frame,
    scale_boxes,
)

__all__ = [
    "open_camera",
    "read_frame",
    "compute_camera_intrinsics",
    "resize_to_frame",
    "inverse_depth_to_distance",
    "calculate_distances",
    "get_detections",
    "unproject_bbox_center_to_camera",
    "calculate_iou",
    "normalize_bbox_coordinates",
    "xywh_to_xyxy",
    "non_maximum_supression",
    "bbox_center",
    "calculate_region_bounds",
    "ensure_yolo_model_downloaded",
    "export_yolo_to_onnx",
    "get_midas_cache_dir",
    "ensure_midas_model_available",
    "get_midas_onnx_config",
    "export_midas_to_onnx",
    "ensure_depth_anything_model_available",
    "DEFAULT_MIDAS_MODEL",
    "DEFAULT_MIDAS_REPO",
    "PYTORCH_HUB_CACHE",
    "letterbox",
    "scale_boxes",
    "resize_frame",
    "calculate_adaptive_scale",
    "lerp",
    "lerp_int",
    "calculate_interpolation_factor",
]
