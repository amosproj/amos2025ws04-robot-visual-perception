# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from pydantic import BaseModel

from analyzer.manager import AnalyzerWebSocketManager


class ConfigureAnalyzerRequest(BaseModel):
    """Request to configure analyzer with streamer URL."""

    streamer_url: str


# Create a global instance of the WebSocket manager
websocket_manager = AnalyzerWebSocketManager()


router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "analyzer"}


@router.post("/configure")
async def configure_analyzer(request: ConfigureAnalyzerRequest) -> dict[str, str]:
    """Configure analyzer to use a specific streamer.

    This endpoint is called by the orchestrator/frontend after analyzer assignment
    to tell this analyzer which streamer service to connect to.
    """
    # Append /offer endpoint path to the streamer base URL
    streamer_offer_url = f"{request.streamer_url.rstrip('/')}/offer"
    await websocket_manager.set_streamer_url(streamer_offer_url)
    return {
        "status": "configured",
        "streamer_url": streamer_offer_url,
    }


@router.get("/metrics")
def metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for metadata streaming.

    Connects to webcam service, processes frames with ML,
    and sends metadata to clients like the frontend.
    """
    await websocket_manager.connect(websocket)

    try:
        # Keep connection alive
        while True:
            # Wait for client messages (ping/pong or control)
            message = await websocket.receive_text()
            await websocket_manager.handle_message(websocket, message)

    except WebSocketDisconnect:
        pass
    finally:
        await websocket_manager.disconnect(websocket)


async def on_shutdown() -> None:
    """Cleanup on service shutdown."""
    await websocket_manager.shutdown()


@router.get("/asyncapi.yaml", include_in_schema=False)
async def get_asyncapi_spec() -> FileResponse:
    """Return AsyncAPI specification for WebSocket endpoint."""
    spec_path = Path(__file__).parent / "asyncapi.yaml"
    return FileResponse(spec_path, media_type="text/yaml")
