# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any
from opentelemetry import trace, _logs
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes


_configured = False
_STANDARD_FIELDS: set[str] = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
}


class JsonFormatter(logging.Formatter):
    """Format log records as structured JSON."""

    def __init__(self, service_name: str, environment: str) -> None:
        super().__init__()
        self.service_name = service_name
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()
        span = trace.get_current_span()
        span_ctx = span.get_span_context()

        payload: dict[str, Any] = {
            "timestamp": ts,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
            "environment": self.environment,
        }

        if span_ctx and span_ctx.is_valid:
            payload["trace_id"] = format(span_ctx.trace_id, "032x")
            payload["span_id"] = format(span_ctx.span_id, "016x")

        # Attach any custom extra fields that were added to the record
        for key, value in record.__dict__.items():
            if key not in _STANDARD_FIELDS and key not in payload:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=True)


class PrettyFormatter(logging.Formatter):
    """Human-readable, single-line log formatter."""

    def __init__(self, service_name: str, environment: str) -> None:
        super().__init__()
        self.service_name = service_name
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()
        span = trace.get_current_span()
        span_ctx = span.get_span_context()

        parts = [
            ts,
            f"{record.levelname:<7}",
            f"[{record.name}]",
            record.getMessage(),
        ]

        extras: dict[str, Any] = {
            "service": self.service_name,
            "env": self.environment,
        }

        if span_ctx and span_ctx.is_valid:
            extras["trace_id"] = format(span_ctx.trace_id, "032x")
            extras["span_id"] = format(span_ctx.span_id, "016x")

        for key, value in record.__dict__.items():
            if key not in _STANDARD_FIELDS and key not in extras:
                extras[key] = value

        if record.exc_info:
            extras["exception"] = self.formatException(record.exc_info)

        extras_str = " ".join(f"{k}={v}" for k, v in extras.items())
        parts.append(extras_str)
        return " ".join(filter(None, parts))


def configure_logging(
    service_name: str,
    service_version: str | None = None,
    environment: str | None = None,
) -> None:
    """
    Configure application logging with OpenTelemetry and JSON console output.

    This sets up:
      - Root logger with JSON console output
      - OpenTelemetry logger provider with OTLP HTTP exporter (if available)
      - Respect for LOG_LEVEL / ENVIRONMENT / OTEL_EXPORTER_OTLP* env vars
    """
    global _configured
    if _configured:
        return

    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    env: str = (
        environment
        if environment is not None
        else os.getenv("ENVIRONMENT", "development")
    )
    log_format: str = os.getenv("LOG_FORMAT", "json").lower()

    resource = Resource.create(
        {
            ResourceAttributes.SERVICE_NAME: service_name,
            ResourceAttributes.SERVICE_VERSION: service_version or "unknown",
            ResourceAttributes.DEPLOYMENT_ENVIRONMENT: env,
        }
    )

    logger_provider = LoggerProvider(resource=resource)
    _logs.set_logger_provider(logger_provider)

    # Configure OTLP HTTP exporter (falls back to defaults if no endpoint provided)
    otlp_endpoint = (
        os.getenv("OTEL_EXPORTER_OTLP_LOGS_ENDPOINT")
        or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        or None
    )

    # Only enable OTLP export if an explicit endpoint is provided
    if otlp_endpoint:
        try:
            otlp_exporter = OTLPLogExporter(endpoint=otlp_endpoint)
            logger_provider.add_log_record_processor(
                BatchLogRecordProcessor(otlp_exporter)
            )
        except (
            Exception
        ) as err:  # pragma: no cover - exporter failures handled gracefully
            # If exporter setup fails, keep console logs and continue.
            logging.getLogger(__name__).warning(
                "OTLP exporter setup failed; console logging only",
                extra={"error": str(err)},
            )

    otel_handler = LoggingHandler(level=log_level, logger_provider=logger_provider)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    formatter = (
        PrettyFormatter(service_name, env)
        if log_format == "pretty"
        else JsonFormatter(service_name, env)
    )
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(log_level)
    root.handlers.clear()
    root.addHandler(console_handler)
    root.addHandler(otel_handler)
    root.propagate = False

    _configured = True
