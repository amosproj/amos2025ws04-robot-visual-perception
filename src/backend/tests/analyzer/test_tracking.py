# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import pytest
from collections import deque

from analyzer.tracker import TrackingManager
from analyzer.tracking_models import TrackedObject, TrackedDetection
from common.core.contracts import Detection


@pytest.fixture
def tracking_manager_factory():
    """Factory function to create TrackingManager with custom parameters."""

    def _create_manager(
        iou_threshold: float = 0.3,
        max_frames_without_detection: int = 5,
        early_termination_iou: float = 0.9,
        confidence_decay: float = 0.1,
        max_history_size: int = 5,
        detection_threshold: int = 1,
    ) -> TrackingManager:
        return TrackingManager(
            iou_threshold=iou_threshold,
            max_frames_without_detection=max_frames_without_detection,
            early_termination_iou=early_termination_iou,
            confidence_decay=confidence_decay,
            max_history_size=max_history_size,
            detection_threshold=detection_threshold,
        )

    return _create_manager


@pytest.fixture
def tracking_manager(tracking_manager_factory):
    """Default TrackingManager instance for testing."""
    return tracking_manager_factory()


@pytest.fixture
def tracked_object() -> TrackedObject:
    """Create a TrackedObject for testing."""
    return TrackedObject(
        track_id=0,
        cls_id=1,
        history=deque(maxlen=5),
    )


def create_detection(
    x1: int = 10,
    y1: int = 20,
    x2: int = 50,
    y2: int = 60,
    cls_id: int = 0,
    confidence: float = 0.9,
    tracked: bool = False,
    distance: float = 2.5,
    frame_id: int = 1,
    timestamp: float = 1.0,
) -> Detection | TrackedDetection:
    """Create a Detection or TrackedDetection for testing.

    Args:
        tracked: If True, returns TrackedDetection; otherwise returns Detection.
    """
    if tracked:
        return TrackedDetection(
            x1=x1,
            y1=y1,
            x2=x2,
            y2=y2,
            cls_id=cls_id,
            confidence=confidence,
            distance=distance,
            frame_id=frame_id,
            timestamp=timestamp,
        )
    return Detection(x1=x1, y1=y1, x2=x2, y2=y2, cls_id=cls_id, confidence=confidence)


def create_track_with_detections(
    track_id: int = 0,
    cls_id: int = 1,
    num_detections: int = 2,
    start_frame: int = 1,
) -> TrackedObject:
    """Create a TrackedObject with detections in history."""
    track = TrackedObject(
        track_id=track_id,
        cls_id=cls_id,
        history=deque(maxlen=5),
    )
    for i in range(num_detections):
        det = create_detection(
            x1=10 + i * 10,
            y1=20 + i * 10,
            x2=50 + i * 10,
            y2=60 + i * 10,
            cls_id=cls_id,
            distance=2.5 + i,
            frame_id=start_frame + i,
            timestamp=float(start_frame + i),
            tracked=True,
        )
        track.add_detection(det)
    return track


def test_match_detections_to_tracks_creates_new_tracks(tracking_manager) -> None:
    """Test that new tracks are created for unmatched detections and that
    detections are matched to existing tracks by IoU."""
    detections = [create_detection()]
    updated_ids, _ = tracking_manager.match_detections_to_tracks(
        detections, [2.5], frame_id=1, timestamp=1.0
    )
    assert len(updated_ids) == 1
    assert len(tracking_manager._tracked_objects) == 1
    assert list(updated_ids)[0] in tracking_manager._tracked_objects

    # overlapping detection should match
    det2 = [create_detection(x1=12, y1=22, x2=52, y2=62, confidence=0.8)]
    updated_ids, _ = tracking_manager.match_detections_to_tracks(
        det2, [2.6], frame_id=2, timestamp=2.0
    )
    assert len(updated_ids) == 1
    assert len(tracking_manager._tracked_objects) == 1


@pytest.mark.parametrize(
    "box1, box2, should_match",
    [
        ((10, 20, 50, 60), (12, 22, 52, 62), True),
        ((10, 20, 50, 60), (200, 200, 250, 260), False),
    ],
    ids=["high_overlap", "no_overlap"],
)
def test_match_detections_to_tracks_respects_iou_threshold(
    tracking_manager,
    box1: tuple[int, int, int, int],
    box2: tuple[int, int, int, int],
    should_match: bool,
) -> None:
    """Test that detections below IoU threshold create new tracks."""
    det1 = [create_detection(x1=box1[0], y1=box1[1], x2=box1[2], y2=box1[3])]
    tracking_manager.match_detections_to_tracks(det1, [2.5], frame_id=1, timestamp=1.0)

    det2 = [
        create_detection(x1=box2[0], y1=box2[1], x2=box2[2], y2=box2[3], confidence=0.8)
    ]
    tracking_manager.match_detections_to_tracks(det2, [2.6], frame_id=2, timestamp=2.0)

    if should_match:
        assert len(tracking_manager._tracked_objects) == 1
    else:
        assert len(tracking_manager._tracked_objects) == 2


def test_match_detections_to_tracks_matches_same_class_only(tracking_manager) -> None:
    """Test that detections only match tracks of the same class."""
    det1 = [create_detection()]
    tracking_manager.match_detections_to_tracks(det1, [2.5], frame_id=1, timestamp=1.0)

    # same position, different class
    det2 = [create_detection(cls_id=1, confidence=0.8)]
    tracking_manager.match_detections_to_tracks(det2, [2.6], frame_id=2, timestamp=2.0)

    assert len(tracking_manager._tracked_objects) == 2


def test_get_interpolated_detections_returns_empty_when_no_tracks(
    tracking_manager,
) -> None:
    """Test that interpolation returns empty when no tracks exist."""
    detections, distances = tracking_manager.get_interpolated_detections_and_distances(
        frame_id=1, timestamp=1.0, track_ids_to_exclude=set()
    )
    assert detections == []
    assert distances == []


def test_get_interpolated_detections_excludes_specified_tracks(
    tracking_manager,
) -> None:
    """Test that excluded track IDs are not interpolated."""
    # create two tracks
    det1 = [create_detection()]
    updated_ids1, _ = tracking_manager.match_detections_to_tracks(
        det1, [2.5], frame_id=1, timestamp=1.0
    )
    det2 = [create_detection(x1=100, y1=100, x2=150, y2=160, cls_id=1, confidence=0.8)]
    tracking_manager.match_detections_to_tracks(det2, [3.0], frame_id=1, timestamp=1.0)

    # add second detection to both tracks (to interpolate later)
    tracking_manager.match_detections_to_tracks(
        [create_detection(x1=12, y1=22, x2=52, y2=62, confidence=0.8)],
        [2.6],
        frame_id=2,
        timestamp=2.0,
    )
    tracking_manager.match_detections_to_tracks(
        [create_detection(x1=102, y1=102, x2=152, y2=162, cls_id=1, confidence=0.7)],
        [3.1],
        frame_id=2,
        timestamp=2.0,
    )

    # exclude first track
    exclude_id = list(updated_ids1)[0]
    detections, _ = tracking_manager.get_interpolated_detections_and_distances(
        frame_id=3, timestamp=3.0, track_ids_to_exclude={exclude_id}
    )

    # should only return interpolation for the non-excluded track
    assert len(detections) == 1
    assert detections[0].cls_id == 1  # 2nd track's class


@pytest.mark.parametrize(
    "max_frames, frames_elapsed, should_remove",
    [
        (5, 6, True),
        (5, 5, False),
        (5, 4, False),
    ],
    ids=["exceeds_max", "at_boundary", "within_limit"],
)
def test_remove_stale_tracks(
    tracking_manager_factory,
    max_frames: int,
    frames_elapsed: int,
    should_remove: bool,
) -> None:
    """Test that tracks beyond max_frames_without_detection are removed."""
    manager = tracking_manager_factory(max_frames_without_detection=max_frames)
    det = [create_detection()]
    manager.match_detections_to_tracks(det, [2.5], frame_id=1, timestamp=1.0)

    manager._remove_stale_tracks(frame_id=1 + frames_elapsed)

    assert (len(manager._tracked_objects) == 0) == should_remove


def test_clear_removes_all_tracks(tracking_manager) -> None:
    """Test that clear removes all tracks and resets state."""
    det = [create_detection()]
    tracking_manager.match_detections_to_tracks(det, [2.5], frame_id=1, timestamp=1.0)

    assert len(tracking_manager._tracked_objects) > 0

    tracking_manager.clear()

    assert len(tracking_manager._tracked_objects) == 0
    assert tracking_manager._next_track_id == 0


def test_add_detection_updates_history(tracked_object) -> None:
    """Test that add_detection adds to history and updates last_seen_frame."""
    det = create_detection(frame_id=5, timestamp=5.0, tracked=True)

    tracked_object.add_detection(det)

    assert len(tracked_object.history) == 1
    assert tracked_object.history[0] == det
    assert tracked_object.last_seen_frame == 5


@pytest.mark.parametrize(
    "history_size, expected_result",
    [
        (0, None),
        (1, "single_detection"),
        (2, "interpolated"),
    ],
    ids=["no_history", "single_detection", "interpolated"],
)
def test_get_interpolated_history_cases(
    history_size: int,
    expected_result: str | None,
) -> None:
    """Test get_interpolated with different history sizes."""
    track = create_track_with_detections(num_detections=history_size)

    result = track.get_interpolated(
        target_frame_id=3, target_timestamp=3.0, confidence_decay=0.1
    )

    if expected_result is None:
        assert result is None
    elif expected_result == "single_detection":
        assert result is not None
        assert result.frame_id == 1
    else:  # interpolated
        assert result is not None
        assert result.frame_id == 3


@pytest.mark.parametrize(
    "frame1, frame2, target_frame, expected_t",
    [
        (1, 3, 2, 0.5),
        (1, 3, 1, 0.0),
        (1, 3, 3, 1.0),
        (1, 3, 4, 1.5),
    ],
    ids=["midpoint", "at_frame1", "at_frame2", "extrapolation"],
)
def test_get_interpolated_interpolation_factor(
    frame1: int,
    frame2: int,
    target_frame: int,
    expected_t: float,
) -> None:
    """Test that interpolation factor is calculated correctly."""
    track = TrackedObject(
        track_id=0,
        cls_id=1,
        history=deque(maxlen=5),
    )

    # add two dets
    det1 = create_detection(
        x1=10,
        y1=20,
        x2=50,
        y2=60,
        confidence=0.9,
        distance=2.0,
        frame_id=frame1,
        timestamp=float(frame1),
        tracked=True,
    )
    det2 = create_detection(
        x1=20,
        y1=30,
        x2=60,
        y2=70,
        confidence=0.8,
        distance=3.0,
        frame_id=frame2,
        timestamp=float(frame2),
        tracked=True,
    )
    track.add_detection(det1)
    track.add_detection(det2)

    result = track.get_interpolated(
        target_frame_id=target_frame,
        target_timestamp=float(target_frame),
        confidence_decay=0.1,
    )

    assert result is not None
    # verify interpolation, at t=0.5, should be midpoint
    if expected_t == 0.5:
        assert result.x1 == 15  # (10 + 20) / 2
        assert result.y1 == 25  # (20 + 30) / 2
        assert result.distance == pytest.approx(2.5)  # (2.0 + 3.0) / 2


def test_get_interpolated_confidence_decay(tracked_object) -> None:
    """Test that confidence decays with interpolation factor."""
    det1 = create_detection(
        confidence=1.0, distance=2.0, frame_id=1, timestamp=1.0, tracked=True
    )
    det2 = create_detection(
        x1=20,
        y1=30,
        x2=60,
        y2=70,
        confidence=1.0,
        distance=3.0,
        frame_id=3,
        timestamp=3.0,
        tracked=True,
    )
    tracked_object.add_detection(det1)
    tracked_object.add_detection(det2)

    # interpolate at midpoint (t=0.5) with confidence_decay=0.2
    result = tracked_object.get_interpolated(
        target_frame_id=2, target_timestamp=2.0, confidence_decay=0.2
    )

    assert result is not None
    # confidence = 1.0 * (1 - 0.5 * 0.2) = 1.0 * 0.9 = 0.9
    assert result.confidence == pytest.approx(0.9, abs=0.01)
