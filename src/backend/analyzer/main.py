# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from contextlib import asynccontextmanager, suppress
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from common import __version__
from common.config import config
from common.core.detector import _get_detector
from common.utils.geometry import _get_estimator_distance
from analyzer.routes import router, on_shutdown


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Warm up detector and depth estimator so initial /offer handling is instant.
    _get_detector()
    _get_estimator_distance()
    yield
    with suppress(Exception):
        await on_shutdown()


def create_app() -> FastAPI:
    """App factory to avoid import-time side effects in tests."""
    app = FastAPI(
        title="Analyzer Service",
        version=__version__,
        description="WebRTC analysis service that receives video, runs YOLO detection, returns annotated stream",
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
