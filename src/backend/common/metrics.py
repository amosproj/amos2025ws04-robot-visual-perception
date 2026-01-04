# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from typing import Optional

import os
from opentelemetry import metrics

# from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    PeriodicExportingMetricReader,
    ConsoleMetricExporter,
)
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

    exporter = ConsoleMetricExporter()
    reader = PeriodicExportingMetricReader(exporter, export_interval_millis=1000)
    meter_provider = MeterProvider(resource=resource, metric_readers=[reader])

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
