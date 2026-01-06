# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from typing import Optional

from prometheus_client import (
    REGISTRY,
    CollectorRegistry,
    Counter,
    Histogram,
    start_http_server,
)

# Global metrics instances
_detection_duration: Optional[Histogram] = None
_depth_estimation_duration: Optional[Histogram] = None
_detections_count: Optional[Counter] = None


def configure_metrics() -> None:
    """
    Configure Prometheus metrics.
    """
    global _detection_duration, _depth_estimation_duration, _detections_count

    if _detection_duration is not None:
        return  # Already configured

    _detection_duration = Histogram(
        "analyzer_detection_duration_seconds",
        "Time taken for object detection inference",
        ["backend"],
    )

    _depth_estimation_duration = Histogram(
        "analyzer_depth_estimation_duration_seconds",
        "Time taken for depth estimation",
        ["model_type"],
    )

    _detections_count = Counter(
        "analyzer_detections_count",
        "Total number of detected objects",
        ["interpolated"],
    )

    start_http_server(9000)


def get_detection_duration() -> Histogram:
    """Get detection duration histogram metric."""
    if _detection_duration is None:
        raise RuntimeError("Metrics not configured. Call configure_metrics() first.")
    return _detection_duration


def get_depth_estimation_duration() -> Histogram:
    """Get depth estimation duration histogram metric."""
    if _depth_estimation_duration is None:
        raise RuntimeError("Metrics not configured. Call configure_metrics() first.")
    return _depth_estimation_duration


def get_detections_count() -> Counter:
    """Get detections count counter metric."""
    if _detections_count is None:
        raise RuntimeError("Metrics not configured. Call configure_metrics() first.")
    return _detections_count


def get_registry() -> CollectorRegistry:
    """Get Prometheus registry for /metrics endpoint."""
    return REGISTRY
