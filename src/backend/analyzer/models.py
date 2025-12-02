# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Normalized bounding box (0-1 range)."""

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(ge=0, le=1)
    height: float = Field(ge=0, le=1)


class DetectionData(BaseModel):
    """Single object detection."""

    box: BoundingBox
    label: int = Field(description="COCO class ID (0-79)", ge=0, le=79)
    confidence: float = Field(description="Detection confidence", ge=0, le=1)
    distance: float = Field(description="Distance in meters", gt=0)


class MetadataMessage(BaseModel):
    """Detection metadata sent via WebSocket."""

    timestamp: float = Field(description="Timestamp in milliseconds")
    frame_id: int = Field(description="Frame number", ge=1)
    detections: list[DetectionData] = Field(description="Detected objects")
    fps: float | None = Field(default=None, description="Processing FPS")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
