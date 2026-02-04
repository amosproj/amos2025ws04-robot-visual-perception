# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
"""Lightweight client helper for orchestrator registration."""

import asyncio
import json
import logging
import socket
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger("orchestrator-client")


async def register_with_orchestrator(
    service_type: str,
    service_url: str,
    orchestrator_url: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Register the current service instance with the orchestrator.

    Uses stdlib networking to avoid extra dependencies; failures are logged but ignored.
    """
    register_url = orchestrator_url.rstrip("/") + "/register"
    payload = {
        "service_type": service_type,
        "url": service_url,
        "metadata": {
            "hostname": socket.gethostname(),
            **(metadata or {}),
        },
    }

    def _post() -> None:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            register_url,
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=3):
            pass

    try:
        await asyncio.to_thread(_post)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        logger.warning(
            "Failed to register service with orchestrator",
            extra={
                "service_type": service_type,
                "service_url": service_url,
                "register_url": register_url,
                "error": str(exc),
            },
        )


async def deregister_from_orchestrator(
    service_type: str,
    service_url: str,
    orchestrator_url: str,
) -> None:
    """Deregister the current service instance (best-effort)."""
    unregister_url = orchestrator_url.rstrip("/") + "/unregister"
    payload = {
        "service_type": service_type,
        "url": service_url,
    }

    def _post() -> None:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            unregister_url,
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=3):
            pass

    try:
        await asyncio.to_thread(_post)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        logger.warning(
            "Failed to deregister service with orchestrator",
            extra={
                "service_type": service_type,
                "service_url": service_url,
                "unregister_url": unregister_url,
                "error": str(exc),
            },
        )
