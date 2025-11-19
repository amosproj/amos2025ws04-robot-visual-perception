# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from contextlib import asynccontextmanager, suppress
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from common import __version__
from common.config import config
from common.core.detector import _get_detector
from common.utils.geometry import _get_estimator_instance
from analyzer.routes import router, on_shutdown


def create_lifespan(
    yolo_model_path: Optional[Path] = None,
    midas_cache_directory: Optional[Path] = None,
):
    """Create lifespan context manager with model paths.

    Args:
        yolo_model_path: Path to YOLO model file.
        midas_cache_directory: Path to MiDaS model cache directory.
    """
    @asynccontextmanager
    async def lifespan_context(app: FastAPI) -> AsyncIterator[None]:
        # Warm up detector and depth estimator so initial /offer handling is instant.
        _get_detector(yolo_model_path)
        _get_estimator_instance(midas_cache_directory)
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
            uses PyTorch Hub default cache location.
    """
    lifespan_context = create_lifespan(yolo_model_path, midas_cache_directory)

    app = FastAPI(
        title="Analyzer Service",
        version=__version__,
        description="WebRTC analysis service that receives video, runs YOLO detection, returns annotated stream",
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
