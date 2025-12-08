# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from analyzer.manager import AnalyzerWebSocketManager


# Create a global instance of the WebSocket manager
websocket_manager = AnalyzerWebSocketManager()


router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "analyzer"}


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
