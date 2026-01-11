# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from common import __version__
from common.config import config
from common.core.camera import _shared_cam
from common.core.sfu_client import IonSfuClient, IonSfuSettings
from streamer.routes import router, on_shutdown
from streamer.tracks import CameraVideoTrack, VideoFileTrack

_sfu_client: IonSfuClient | None = None
_sfu_track = None
_sfu_logger = logging.getLogger("streamer.sfu")
_camera_acquired = False


async def _start_sfu_publisher() -> None:
    """Publish the local video source to ion-sfu when enabled."""
    global _sfu_client, _sfu_track, _camera_acquired
    if config.WEBRTC_MODE != "ion-sfu":
        return
    settings = IonSfuSettings(
        signaling_url=config.SFU_SIGNALING_URL,
        session_id=config.SFU_SESSION_ID,
        client_id=config.SFU_PUBLISHER_ID,
        ice_servers=config.SFU_ICE_SERVERS,
        no_subscribe=True,
        no_auto_subscribe=True,
    )
    client = IonSfuClient(settings=settings, logger=_sfu_logger)
    try:
        if config.VIDEO_SOURCE_TYPE == "file":
            _sfu_track = VideoFileTrack(config.VIDEO_FILE_PATH)
        else:
            await _shared_cam.acquire()
            _camera_acquired = True
            _sfu_track = CameraVideoTrack()
        client.add_publisher_track(_sfu_track)
        await client.connect()
        _sfu_client = client
        _sfu_logger.info(
            "Published stream via ion-sfu",
            extra={
                "signaling_url": config.SFU_SIGNALING_URL,
                "session": config.SFU_SESSION_ID,
            },
        )
    except Exception as exc:
        _sfu_logger.error(
            "Failed to publish stream to ion-sfu", extra={"error": str(exc)}
        )
        with suppress(Exception):
            await client.close()


async def _stop_sfu_publisher() -> None:
    """Tear down SFU publication and release shared camera."""
    global _sfu_client, _sfu_track, _camera_acquired
    if _sfu_client is not None:
        with suppress(Exception):
            await _sfu_client.close()
    if _camera_acquired:
        _camera_acquired = False
        with suppress(Exception):
            await _shared_cam.release()
    _sfu_client = None
    _sfu_track = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    sfu_task: asyncio.Task[None] | None = None
    if config.WEBRTC_MODE == "ion-sfu":
        sfu_task = asyncio.create_task(_start_sfu_publisher())
    yield
    if sfu_task is not None:
        with suppress(Exception):
            await sfu_task
    with suppress(Exception):
        await _stop_sfu_publisher()
    with suppress(Exception):
        await on_shutdown()


def create_app() -> FastAPI:
    """App factory to avoid import-time side effects in tests."""
    app = FastAPI(
        title="Streamer Mock Service",
        version=__version__,
        description="Streamer service for development that streams local video over WebRTC",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    # Mount routes
    app.include_router(router)
    return app


app = create_app()
