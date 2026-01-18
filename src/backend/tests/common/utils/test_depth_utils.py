# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import numpy as np
import pytest
import torch

from common.typing import Detection
from common.utils.depth import (
    resize_to_frame,
    _calculate_region_bounds, 
    _inverse_depth_to_distance,
    calculate_distances,
)


@pytest.mark.parametrize(
    "input_shape,output_shape",
    [
        ((1, 1, 64, 64), (128, 128)),
        ((1, 1, 256, 256), (64, 64)),
        ((1, 1, 64, 64), (120, 160)),
        ((1, 1, 32, 32), (32, 32)), 
    ],
    ids=["upscale", "downscale", "non-square output", "same size"],
)
def test_resize_to_frame_numpy(input_shape, output_shape):
    """Test resizing numpy array inputs to various output shapes."""
    prediction = np.random.rand(*input_shape).astype(np.float32)
    result = resize_to_frame(prediction, output_shape)
    assert isinstance(result, np.ndarray)
    assert result.shape == output_shape


@pytest.mark.parametrize(
    "input_shape,output_shape",
    [
        ((1, 1, 64, 64), (128, 128)),
        ((1, 64, 64), (32, 32)),
    ],
    ids=["4d_tensor", "3d_tensor"],
)
def test_resize_to_frame_tensor(input_shape, output_shape):
    """Test resizing torch tensor inputs."""
    prediction = torch.rand(*input_shape)
    result = resize_to_frame(prediction, output_shape)
    assert isinstance(result, np.ndarray)
    assert result.shape == output_shape


@pytest.mark.parametrize(
    "center_x,center_y,region_size,frame_width,frame_height,expected",
    [
        (50, 50, 10, 100, 100, (45, 56, 45, 56)),
        (3, 50, 10, 100, 100, (0, 9, 45, 56)),
        (97, 50, 10, 100, 100, (92, 100, 45, 56)),
        (50, 3, 10, 100, 100, (45, 56, 0, 9)),
        (50, 97, 10, 100, 100, (45, 56, 92, 100)),
        (2, 2, 10, 100, 100, (0, 8, 0, 8)),
        (0, 0, 10, 100, 100, (0, 6, 0, 6)),
        (5, 5, 20, 10, 10, (0, 10, 0, 10)),
    ],
    ids=[
        "region_inside_frame",
        "clamped_left_edge",
        "clamped_right_edge",
        "clamped_top_edge",
        "clamped_bottom_edge",
        "clamped_corner",
        "center_at_origin",
        "region_larger_than_frame",
    ],
)
def test_calculate_region_bounds(
    center_x, center_y, region_size, frame_width, frame_height, expected
):
    """Test region bounds calculation with boundary clamping."""
    result = _calculate_region_bounds(
        center_x, center_y, region_size, frame_width, frame_height
    )
    assert result == expected


@pytest.mark.parametrize(
    "inverse_depth,scale_factor,min_depth,expected",
    [
        (10.0, 100.0, 1e-6, 10.0),
        (2.0, 100.0, 1e-6, 50.0),
        (0.5, 100.0, 1e-6, 200.0),
        (100.0, 100.0, 1e-6, 1.0),
        (0.0, 100.0, 1e-6, 100000000.0),
        (-5.0, 100.0, 1e-6, 100000000.0),
        (0.0, 100.0, 0.1, 1000.0),
    ],
    ids=[
        "normal_depth",
        "half_inverse_depth",
        "small_inverse_depth",
        "large_inverse_depth",
        "zero_uses_min_depth",
        "negative_uses_min_depth",
        "custom_min_depth",
    ],
)
def test_inverse_depth_to_distance(inverse_depth, scale_factor, min_depth, expected):
    """Test inverse depth to distance conversion."""
    result = _inverse_depth_to_distance(inverse_depth, scale_factor, min_depth)
    assert result == pytest.approx(expected)


@pytest.mark.parametrize(
    "depth_value,bbox,region_size,scale_factor,expected_distance",
    [
        (10.0, (40, 40, 60, 60), 5, 100.0, 10.0),
        (2.0, (0, 0, 20, 20), 5, 100.0, 50.0),
        (50.0, (80, 80, 100, 100), 10, 100.0, 2.0),
        (1.0, (45, 45, 55, 55), 3, 50.0, 50.0),
    ],
    ids=[
        "center_of_frame",
        "corner_detection",
        "edge_detection",
        "different_scale_factor",
    ],
)
def test_calculate_distances(
    depth_value, bbox, region_size, scale_factor, expected_distance
):
    """Test distance calculation from depth map for detections."""
    depth_map = np.full((100, 100), depth_value, dtype=np.float32)
    x1, y1, x2, y2 = bbox
    detection = Detection(x1=x1, y1=y1, x2=x2, y2=y2, cls_id=0, confidence=0.9)
    result = calculate_distances(depth_map, [detection], region_size, scale_factor)
    assert len(result) == 1
    assert result[0] == pytest.approx(expected_distance)


def test_calculate_distances_multiple_detections():
    """Test distance calculation with multiple detections."""
    depth_map = np.full((100, 100), 10.0, dtype=np.float32)
    detections = [
        Detection(x1=10, y1=10, x2=20, y2=20, cls_id=0, confidence=0.9),
        Detection(x1=50, y1=50, x2=60, y2=60, cls_id=1, confidence=0.8),
        Detection(x1=80, y1=80, x2=90, y2=90, cls_id=2, confidence=0.7),
    ]
    result = calculate_distances(depth_map, detections, region_size=5, scale_factor=100.0)
    assert len(result) == 3
    assert all(d == pytest.approx(10.0) for d in result)


def test_calculate_distances_empty_detections():
    """Test distance calculation with no detections."""
    depth_map = np.full((100, 100), 10.0, dtype=np.float32)
    result = calculate_distances(depth_map, [], region_size=5, scale_factor=100.0)
    assert result == []