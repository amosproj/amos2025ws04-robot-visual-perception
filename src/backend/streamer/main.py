# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from contextlib import asynccontextmanager, suppress
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from common import __version__
from common.config import config
from common.orchestrator import register_with_orchestrator, deregister_from_orchestrator
from streamer.routes import router, on_shutdown


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Register this streamer instance with orchestrator (best-effort)
    await register_with_orchestrator(
        service_type="streamer",
        service_url=config.STREAMER_PUBLIC_URL,
        orchestrator_url=config.ORCHESTRATOR_URL,
    )
    yield
    with suppress(Exception):
        await deregister_from_orchestrator(
            service_type="streamer",
            service_url=config.STREAMER_PUBLIC_URL,
            orchestrator_url=config.ORCHESTRATOR_URL,
        )
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
