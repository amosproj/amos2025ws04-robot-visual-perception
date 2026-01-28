# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
"""HTTP API for orchestrator service registry."""

import asyncio
import json
import logging
import time
from typing import Any, Dict, Literal

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

logger = logging.getLogger("orchestrator")
router = APIRouter()


class RegisterRequest(BaseModel):
    """Payload for service registration."""

    service_type: Literal["streamer", "analyzer"]
    url: str
    metadata: Dict[str, Any] | None = None


class ServiceInfo(BaseModel):
    """Stored service entry."""

    url: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    last_seen: float


class AnalyzerAssignmentResponse(BaseModel):
    """Response when assigning an analyzer to a streamer."""

    analyzer_url: str | None
    streamer_url: str | None
    message: str


# Global state
_services: dict[str, dict[str, ServiceInfo]] = {"streamer": {}, "analyzer": {}}
# Tracks which analyzer is currently assigned to which streamer (analyzer_url -> streamer_url)
_assignments: dict[str, str] = {}
_services_lock = asyncio.Lock()
_ws_connections: set[WebSocket] = set()  # WebSocket clients watching for updates


@router.get("/health")
async def health() -> dict[str, object]:
    """Health check with counts per service type."""
    async with _services_lock:
        counts = {kind: len(entries) for kind, entries in _services.items()}
    return {"status": "ok", "service": "orchestrator", "counts": counts}


async def _broadcast_update(
    event_type: str, service_type: str, service_url: str
) -> None:
    """Broadcast service update to all connected WebSocket clients."""
    message = json.dumps(
        {
            "type": event_type,
            "service_type": service_type,
            "service_url": service_url,
        }
    )
    dead_connections = set()
    for ws in _ws_connections:
        try:
            await ws.send_text(message)
        except Exception:
            dead_connections.add(ws)
    _ws_connections.difference_update(dead_connections)


@router.post("/register")
async def register_service(payload: RegisterRequest) -> dict[str, object]:
    """Register or refresh a service instance."""
    entry = ServiceInfo(
        url=payload.url,
        metadata=payload.metadata or {},
        last_seen=time.time(),
    )

    async with _services_lock:
        _services[payload.service_type][payload.url] = entry

    logger.info(f"Registered service: {payload.service_type} at {payload.url}")

    # Broadcast update to all connected clients
    await _broadcast_update("registered", payload.service_type, payload.url)

    return {
        "status": "registered",
        "service_type": payload.service_type,
        "url": payload.url,
    }


@router.post("/unregister")
async def unregister_service(payload: RegisterRequest) -> dict[str, object]:
    """Remove a service instance from the registry."""
    async with _services_lock:
        _services[payload.service_type].pop(payload.url, None)

        # Clear assignments when a service goes away
        if payload.service_type == "analyzer":
            _assignments.pop(payload.url, None)
        elif payload.service_type == "streamer":
            # Free any analyzer assigned to this streamer
            busy_analyzers = [a for a, s in _assignments.items() if s == payload.url]
            for analyzer_url in busy_analyzers:
                _assignments.pop(analyzer_url, None)

    logger.info(f"Unregistered service: {payload.service_type} at {payload.url}")

    # Broadcast update to all connected clients
    await _broadcast_update("unregistered", payload.service_type, payload.url)

    return {
        "status": "unregistered",
        "service_type": payload.service_type,
        "url": payload.url,
    }


@router.get("/services")
async def list_services() -> dict[str, list[ServiceInfo]]:
    """List registered services grouped by type."""
    async with _services_lock:
        return {kind: list(entries.values()) for kind, entries in _services.items()}


@router.post("/assign-analyzer")
async def assign_analyzer(streamer_url: str) -> AnalyzerAssignmentResponse:
    """Assign a free analyzer to a streamer.

    Returns the URL of an available analyzer and the streamer URL, or None if no analyzers are available.
    """
    async with _services_lock:
        analyzers = _services.get("analyzer", {})
        free_analyzers = [url for url in analyzers.keys() if url not in _assignments]

        if not free_analyzers:
            return AnalyzerAssignmentResponse(
                analyzer_url=None,
                streamer_url=None,
                message="No analyzers available",
            )

        # Return first available analyzer (simple first-fit strategy)
        analyzer_url = free_analyzers[0]
        _assignments[analyzer_url] = streamer_url

    logger.info(f"Assigned analyzer {analyzer_url} to streamer {streamer_url}")
    return AnalyzerAssignmentResponse(
        analyzer_url=analyzer_url,
        streamer_url=streamer_url,
        message=f"Analyzer {analyzer_url} assigned to streamer {streamer_url}",
    )


@router.post("/unassign-analyzer")
async def unassign_analyzer(analyzer_url: str) -> dict[str, object]:
    """Mark an analyzer as free (unassign from any streamer)."""
    async with _services_lock:
        was_assigned = analyzer_url in _assignments
        _assignments.pop(analyzer_url, None)

    logger.info(f"Unassigned analyzer {analyzer_url}")
    return {
        "status": "unassigned",
        "analyzer_url": analyzer_url,
        "was_assigned": was_assigned,
    }


@router.websocket("/ws")
async def websocket_updates(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time service registry updates."""
    await websocket.accept()
    _ws_connections.add(websocket)

    try:
        # Send initial state
        async with _services_lock:
            current_state = {
                kind: [service.model_dump() for service in entries.values()]
                for kind, entries in _services.items()
            }
        await websocket.send_json(
            {
                "type": "sync",
                "services": current_state,
            }
        )

        # Keep connection alive and receive ping messages
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        _ws_connections.discard(websocket)
