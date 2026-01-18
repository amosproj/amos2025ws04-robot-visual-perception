# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from collections import deque
from dataclasses import dataclass
from typing import Optional

from common.typing import Detection
from common.utils import calculate_interpolation_factor, lerp_int, lerp


@dataclass
class TrackedDetection(Detection):
    """Detection with tracking metadata."""

    distance: float
    frame_id: int
    timestamp: float


@dataclass
class TrackedObject:
    """Tracks an object across multiple frames."""

    track_id: int
    cls_id: int
    history: deque[TrackedDetection]
    last_seen_frame: Optional[int] = None
    detection_count: int = 0

    def add_detection(self, detection: TrackedDetection) -> None:
        """Add a new detection to history."""
        self.history.append(detection)
        self.last_seen_frame = detection.frame_id
        self.detection_count += 1

    def is_active(self, detection_threshold: int) -> bool:
        """Return True if track has met the activation threshold."""
        return self.detection_count >= detection_threshold

    def get_interpolated(
        self, target_frame_id: int, target_timestamp: float, confidence_decay: float
    ) -> Optional[TrackedDetection]:
        """
        Interpolate the object's detection for a target frame.

        Uses the last two detections to linearly interpolate bounding box coordinates
        and distance. Confidence decays with interpolation factor `t` scaled by
        `confidence_decay`. Allows limited extrapolation (t ∈ [0.0, 1.5]).

        Args:
            target_frame_id: Frame ID to interpolate for.
            target_timestamp: Timestamp of the target frame.
            confidence_decay: Rate at which confidence decreases with t.

        Returns:
            Interpolated detection, the single existing detection, or None.
        """
        # Not enough history
        if len(self.history) < 2:
            return self.history[0] if len(self.history) == 1 else None

        tracked1 = self.history[-2]
        tracked2 = self.history[-1]

        t = calculate_interpolation_factor(
            tracked1.frame_id, tracked2.frame_id, target_frame_id, clamp_max=1.5
        )

        x1 = lerp_int(tracked1.x1, tracked2.x1, t)
        y1 = lerp_int(tracked1.y1, tracked2.y1, t)
        x2 = lerp_int(tracked1.x2, tracked2.x2, t)
        y2 = lerp_int(tracked1.y2, tracked2.y2, t)

        distance = lerp(tracked1.distance, tracked2.distance, t)
        confidence = tracked1.confidence * (1 - t * confidence_decay)

        return TrackedDetection(
            x1=x1,
            y1=y1,
            x2=x2,
            y2=y2,
            cls_id=self.cls_id,
            confidence=confidence,
            distance=distance,
            frame_id=target_frame_id,
            timestamp=target_timestamp,
        )
