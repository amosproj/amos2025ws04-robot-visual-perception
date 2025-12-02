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

    REGION_SIZE = int(
        os.getenv("REGION_SIZE", "5")
    )  # size of square region for depth median
    SCALE_FACTOR = float(
        os.getenv("SCALE_FACTOR", "432.0")
    )  # empirical calibration factor
    UPDATE_FREQ = int(
        os.getenv("UPDATE_FREQ", "2")
    )  # number of frames between depth updates

    # adaptive downsampling settings
    TARGET_SCALE_INIT: float = float(
        os.getenv("TARGET_SCALE_INIT", "0.8")
    )  # initial downscale factor for images
    SMOOTH_FACTOR: float = float(
        os.getenv("SMOOTH_FACTOR", "0.15")
    )  # smoothing factor for scale updates
    MIN_SCALE: float = float(os.getenv("MIN_SCALE", "0.2"))  # minimum allowed scale
    MAX_SCALE: float = float(os.getenv("MAX_SCALE", "1.0"))  # maximum allowed scale

    # adaptive frame dropping
    FPS_THRESHOLD: float = float(
        os.getenv("FPS_THRESHOLD", "15.0")
    )  # threshold FPS for skipping more frames

    # Depth estimation settings
    REGION_SIZE = int(os.getenv("REGION_SIZE", "5"))
    SCALE_FACTOR = float(os.getenv("SCALE_FACTOR", "432.0"))
    CAMERA_FOV_X_DEG = float(os.getenv("CAMERA_FOV_X_DEG", "78.0"))
    CAMERA_FOV_Y_DEG = float(os.getenv("CAMERA_FOV_Y_DEG", "65.0"))
    CAMERA_FX = float(os.getenv("CAMERA_FX", "0"))
    CAMERA_FY = float(os.getenv("CAMERA_FY", "0"))
    CAMERA_CX = float(os.getenv("CAMERA_CX", "0"))
    CAMERA_CY = float(os.getenv("CAMERA_CY", "0"))
    LOG_INTRINSICS: bool = os.getenv("LOG_INTRINSICS", "false").lower() in (
        "1",
        "true",
        "yes",
    )

    # WebRTC settings
    STUN_SERVER: str = os.getenv("STUN_SERVER", "stun:stun.l.google.com:19302")
    ICE_GATHERING_TIMEOUT: float = float(os.getenv("ICE_GATHERING_TIMEOUT", "5.0"))

    # Analyzer mode (for analyzer.py)
    WEBCAM_OFFER_URL: str = os.getenv("WEBCAM_OFFER_URL", "http://localhost:8000/offer")

    # CORS settings
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")

    # Model settings
    MODEL_PATH: Path = Path(os.getenv("MODEL_PATH", "models/yolov8n.pt")).resolve()
    ONNX_MODEL_PATH: Path = Path(
        os.getenv("ONNX_MODEL_PATH", str(MODEL_PATH.with_suffix(".onnx")))
    ).resolve()
    DETECTOR_BACKEND: str = os.getenv("DETECTOR_BACKEND", "torch").lower()
    DETECTOR_IMAGE_SIZE: int = int(os.getenv("DETECTOR_IMAGE_SIZE", "640"))
    DETECTOR_CONF_THRESHOLD: float = float(os.getenv("DETECTOR_CONF_THRESHOLD", "0.25"))
    DETECTOR_IOU_THRESHOLD: float = float(os.getenv("DETECTOR_IOU_THRESHOLD", "0.7"))
    DETECTOR_MAX_DETECTIONS: int = int(os.getenv("DETECTOR_MAX_DETECTIONS", "100"))
    DETECTOR_NUM_CLASSES: int = int(os.getenv("DETECTOR_NUM_CLASSES", "80"))
    TORCH_DEVICE: Optional[str] = os.getenv("TORCH_DEVICE")
    TORCH_HALF_PRECISION: str = os.getenv("TORCH_HALF_PRECISION", "auto")
    ONNX_PROVIDERS: list[str] = [
        provider.strip()
        for provider in os.getenv("ONNX_PROVIDERS", "").split(",")
        if provider.strip()
    ]

    @classmethod
    def get(cls, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a configuration value."""
        return os.getenv(key, default)


config = Config()
