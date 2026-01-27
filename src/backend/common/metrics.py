# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import logging
import os
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

# Service-specific Prometheus ports to avoid conflicts
PROMETHEUS_PORTS = {
    "analyzer": 9001,
    "streamer": 9002,
    "orchestrator": 9003,
}


def configure_metrics() -> None:
    """
    Configure Prometheus metrics.
    """
    global _detection_duration, _depth_estimation_duration, _detections_count

    logger = logging.getLogger(__name__)

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

    # Determine service-specific port
    service_type = os.getenv("SERVICE_TYPE", "unknown")
    port = PROMETHEUS_PORTS.get(service_type, 9000)

    # Start Prometheus HTTP server with error handling for --reload mode
    try:
        start_http_server(port)
        logger.info(f"Prometheus metrics server started on port {port} (service: {service_type})")
    except OSError as e:
        if "Address already in use" in str(e):
            logger.warning(
                f"Port {port} already in use (likely uvicorn --reload worker). "
                "Metrics endpoint will be available on the main process only."
            )
        else:
            raise


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
