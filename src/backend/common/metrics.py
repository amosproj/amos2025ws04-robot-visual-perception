# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import logging
from typing import Optional

import os
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes


_configured = False
_meter: Optional[metrics.Meter] = None


def configure_metrics(
    service_name: str,
    service_version: str,
    environment: str | None = None,
) -> metrics.Meter:
    """
    Configure OpenTelemetry metrics and return a Meter instance.

    This sets up:
      - MeterProvider with OTLP HTTP exporter (if available)
      - Respect for ENVIRONMENT / OTEL_EXPORTER_OTLP* env vars
      - Returns a Meter for creating metrics

    Args:
        service_name: Name of the service (e.g., "analyzer")
        service_version: Version of the service
        environment: Deployment environment (e.g., "development", "production")

    Returns:
        Meter instance for creating metrics
    """
    global _configured, _meter
    if _configured and _meter is not None:
        return _meter

    env = (
        os.getenv("ENVIRONMENT", "development") if environment is None else environment
    )

    resource = Resource.create(
        {
            ResourceAttributes.SERVICE_NAME: service_name,
            ResourceAttributes.SERVICE_VERSION: service_version,
            ResourceAttributes.DEPLOYMENT_ENVIRONMENT: env,
        }
    )

    # Configure OTLP HTTP exporter (falls back to defaults if no endpoint provided)
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT") or os.getenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT"
    )

    # Only enable OTLP export if an explicit endpoint is provided
    if otlp_endpoint:
        try:
            otlp_exporter = OTLPMetricExporter(endpoint=otlp_endpoint)
            reader = PeriodicExportingMetricReader(
                otlp_exporter, export_interval_millis=5000
            )
            meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
        except Exception as err:  # pragma: no cover
            # If exporter setup fails, use a no-op provider and continue
            logging.getLogger(__name__).warning(
                "OTLP metrics exporter setup failed; metrics disabled",
                extra={"error": str(err)},
            )
            meter_provider = MeterProvider(resource=resource)
    else:
        # No endpoint provided, use default provider (no-op)
        meter_provider = MeterProvider(resource=resource)

    metrics.set_meter_provider(meter_provider)
    _meter = metrics.get_meter(service_name, service_version)
    _configured = True

    return _meter


def get_meter() -> metrics.Meter:
    """Get the configured Meter instance.

    Returns:
        Meter instance for creating metrics

    Raises:
        RuntimeError: If metrics have not been configured yet
    """
    if _meter is None:
        raise RuntimeError("Metrics not configured. Call configure_metrics() first.")
    return _meter
