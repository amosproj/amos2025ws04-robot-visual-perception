# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from collections import deque
from typing import Optional

from analyzer.tracking_models import TrackedObject, TrackedDetection
from common.utils.geometry import calculate_iou
from common.core.contracts import Detection


class TrackingManager:
    """Manages object tracking across frames for interpolation."""

    def __init__(
        self,
        iou_threshold: float,
        max_frames_without_detection: int,
        early_termination_iou: float,
        confidence_decay: float,
        max_history_size: int,
    ) -> None:
        """Initialize tracking manager.

        Args:
            iou_threshold: Minimum IoU to match detection to track
            max_frames_without_detection: Frames before removing stale tracks
            early_termination_iou: IoU threshold for early termination during matching
            confidence_decay: Confidence decay factor per unit interpolation factor
            max_history_size: Maximum number of detections to keep in track history
        """
        self.iou_threshold = iou_threshold
        self.max_frames_without_detection = max_frames_without_detection
        self.early_termination_iou = early_termination_iou
        self.confidence_decay = confidence_decay
        self.max_history_size = max_history_size
        self._tracked_objects: dict[int, TrackedObject] = {}
        self._next_track_id = 0

    def match_detections_to_tracks(
        self,
        detections: list[Detection],
        distances: list[float],
        frame_id: int,
        timestamp: float,
    ) -> None:
        """Match new detections to existing tracks or create new tracks.

        Args:
            detections: List of detections
            distances: List of distance estimates in meters
            frame_id: Current frame identifier
            timestamp: Current timestamp

        Returns:
            None
        """
        used_track_ids: set[int] = set()

        new_detections = [
            TrackedDetection(
                x1=det.x1,
                y1=det.y1,
                x2=det.x2,
                y2=det.y2,
                cls_id=det.cls_id,
                confidence=det.confidence,
                distance=dist,
                frame_id=frame_id,
                timestamp=timestamp,
            )
            for det, dist in zip(detections, distances)
        ]

        # try to match each new detection to an existing track
        for det in new_detections:
            best_match: Optional[tuple[int, float]] = None
            best_iou = 0.0

            # find best matching track (same class, highest iou)
            for track_id, track in self._tracked_objects.items():
                if track.cls_id != det.cls_id:
                    continue
                if track_id in used_track_ids:
                    continue
                if not track.history:
                    continue

                last_det = track.history[-1]
                iou = calculate_iou(
                    (last_det.x1, last_det.y1, last_det.x2, last_det.y2),
                    (det.x1, det.y1, det.x2, det.y2),
                )

                if iou > best_iou and iou >= self.iou_threshold:
                    best_iou = iou
                    best_match = (track_id, iou)
                    if (
                        best_iou >= self.early_termination_iou
                    ):  # near perfect match, stop
                        break

            # assign to existing track or create new one
            if best_match:
                track_id, _ = best_match
            else:
                track_id = self._next_track_id
                self._next_track_id += 1
                new_track = TrackedObject(
                    track_id=track_id,
                    cls_id=det.cls_id,
                    history=deque(maxlen=self.max_history_size),
                )
                self._tracked_objects[track_id] = new_track

            self._tracked_objects[track_id].add_detection(det)
            used_track_ids.add(track_id)

    def get_interpolated_detections(
        self,
        frame_id: int,
        timestamp: float,
    ) -> list[TrackedDetection]:
        """Get interpolated detections for frames without actual detection.

        Args:
            frame_id: Target frame identifier
            timestamp: Target timestamp

        Returns:
            List of interpolated TrackedDetection objects.
        """
        interpolated: list[TrackedDetection] = []

        for track in self._tracked_objects.values():
            interp_det = track.get_interpolated(
                frame_id, timestamp, self.confidence_decay
            )
            if interp_det:
                interpolated.append(interp_det)

        return interpolated

    def clear(self) -> None:
        """Clear all tracks and reset tracking state."""
        self._tracked_objects.clear()
        self._next_track_id = 0

    def _remove_stale_tracks(self, frame_id: int) -> None:
        """Remove tracks that haven't been seen recently."""
        tracks_to_remove = [
            track_id
            for track_id, track in self._tracked_objects.items()
            if self._is_track_stale(track, frame_id)
        ]
        for track_id in tracks_to_remove:
            del self._tracked_objects[track_id]

    def _is_track_stale(self, track: TrackedObject, frame_id: int) -> bool:
        """Check if a track should be removed due to inactivity.

        Args:
            track: The track to check
            frame_id: Current frame identifier

        Returns:
            True if track should be removed, False otherwise
        """
        if track.last_seen_frame is None:
            return True
        return frame_id - track.last_seen_frame > self.max_frames_without_detection
