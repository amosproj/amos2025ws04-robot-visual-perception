# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from contextlib import asynccontextmanager, suppress
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import AsyncContextManager, Optional
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from common import __version__
from common.config import config
from common.core.detector import get_detector
from common.core.depth import get_depth_estimator
from analyzer.routes import router, on_shutdown

# Configure logging for uvicorn execution
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def create_lifespan(
    yolo_model_path: Optional[Path] = None,
    midas_cache_directory: Optional[Path] = None,
) -> Callable[[FastAPI], AsyncContextManager[None]]:
    """Create lifespan context manager with model paths.

    Args:
        yolo_model_path: Path to YOLO model file.
        midas_cache_directory: Path to MiDaS model cache directory.
    """

    @asynccontextmanager
    async def lifespan_context(app: FastAPI) -> AsyncIterator[None]:
        # Warm up detector and depth estimator so initial /offer handling is instant.
        get_detector(yolo_model_path)
        get_depth_estimator(midas_cache_directory)
        yield
        with suppress(Exception):
            await on_shutdown()

    return lifespan_context


def create_app(
    yolo_model_path: Optional[Path] = None,
    midas_cache_directory: Optional[Path] = None,
) -> FastAPI:
    """App factory to avoid import-time side effects in tests.

    Args:
        yolo_model_path: Path to YOLO model file. If None, uses config default.
        midas_cache_directory: Path to MiDaS model cache directory. If None,
            uses config default (models/midas_cache).
    """
    if midas_cache_directory is None:
        midas_cache_directory = config.MIDAS_CACHE_DIR

    lifespan_context = create_lifespan(yolo_model_path, midas_cache_directory)

    app = FastAPI(
        title="Analyzer Service",
        version=__version__,
        description=(
            "WebRTC analysis service that receives video, runs YOLO detection, "
            "returns annotated stream. WebSocket protocol documentation available at /asyncapi.yaml"
        ),
        lifespan=lifespan_context,
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
