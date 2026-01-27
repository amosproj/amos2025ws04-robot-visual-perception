# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT

"""Orchestrator service main entrypoint."""

# Necessary for running stuff before other imports
# ruff: noqa: E402

import os

from common import __version__
from common.logging_config import configure_logging
from common.metrics import configure_metrics

# Set service type for Prometheus metrics port allocation
os.environ["SERVICE_TYPE"] = "orchestrator"

# Initialize logging early
configure_logging(service_name="orchestrator", service_version=__version__)

# Initialize metrics (kept for parity even if unused for now)
configure_metrics()

from contextlib import asynccontextmanager, suppress
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from common.config import config
from orchestrator.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Handle startup/shutdown hooks."""
    yield
    with suppress(Exception):
        pass


def create_app() -> FastAPI:
    """FastAPI factory for orchestrator service."""
    app = FastAPI(
        title="Orchestrator Service",
        version=__version__,
        description="Registry service tracking analyzer and streamer instances",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(router)
    return app


app = create_app()
