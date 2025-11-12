# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import os
from typing import Optional
from pathlib import Path


class Config:
    """Application configuration."""

    # Camera settings
    CAMERA_INDEX: int = int(os.getenv("CAMERA_INDEX", "0"))

    # Depth estimation settings
    REGION_SIZE = int(os.getenv("REGION_SIZE", "5"))
    SCALE_FACTOR = float(os.getenv("SCALE_FACTOR", "432.0"))

    # WebRTC settings
    STUN_SERVER: str = os.getenv("STUN_SERVER", "stun:stun.l.google.com:19302")
    ICE_GATHERING_TIMEOUT: float = float(os.getenv("ICE_GATHERING_TIMEOUT", "5.0"))

    # Analyzer mode (for analyzer.py)
    WEBCAM_OFFER_URL: str = os.getenv("WEBCAM_OFFER_URL", "http://localhost:8000/offer")

    # CORS settings
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")

    # Model settings
    MODEL_PATH: Path = Path(os.getenv("MODEL_PATH", "models/yolov8n.pt")).resolve()

    @classmethod
    def get(cls, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a configuration value."""
        return os.getenv(key, default)


config = Config()
