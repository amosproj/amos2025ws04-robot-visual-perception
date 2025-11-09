# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import contextlib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router, on_shutdown  # keeps original on_shutdown name

app = FastAPI(title="WebRTC Webcam Streamer", version="1.0.1")

# Proper CORS (no credentials with wildcard)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Mount all endpoints
app.include_router(router)


# Wire shutdown using the existing function name
@app.on_event("shutdown")
async def _app_shutdown() -> None:
    with contextlib.suppress(Exception):
        await on_shutdown()
