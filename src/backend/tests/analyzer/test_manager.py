# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import pytest
from unittest.mock import AsyncMock, MagicMock

from analyzer.manager import AnalyzerWebSocketManager, ProcessingState
from common.core.contracts import Detection


@pytest.fixture
def manager() -> AnalyzerWebSocketManager:
    """Create AnalyzerWebSocketManager for testing."""
    return AnalyzerWebSocketManager()


@pytest.fixture
def processing_state() -> ProcessingState:
    """Create ProcessingState for testing."""
    return ProcessingState(
        frame_id=4,
        current_fps=12.0,
        last_fps_time=1.0,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "frame_id, sample_rate, should_detect",
    [
        (4, 2, True),
        (5, 2, False),
        (8, 4, True),
        (9, 4, False),
    ],
    ids=[
        "detect_frame_even",
        "skip_frame_odd",
        "detect_frame_div4",
        "skip_frame_not_div4",
    ],
)
async def test_run_inference_pipeline_skips_non_detection_frames(
    manager: AnalyzerWebSocketManager,
    frame_id: int,
    sample_rate: int,
    should_detect: bool,
) -> None:
    """Test that _run_inference_pipeline skips frames based on sample_rate."""
    state = ProcessingState(
        frame_id=frame_id,
        current_fps=12.0 if sample_rate == 2 else 20.0,  # below/above threshold
        last_fps_time=1.0,
    )
    manager.active_connections.add(MagicMock())
    manager._send_frame_metadata = AsyncMock()  # type: ignore

    detector = AsyncMock()
    # If called, return empty detections to stop further processing but confirm call
    detector.infer.return_value = []

    estimator = MagicMock()
    frame = MagicMock()
    current_time = 2.0

    await manager._run_inference_pipeline(
        frame, state, detector, estimator, current_time
    )

    if should_detect:
        detector.infer.assert_called_once()
    else:
        detector.infer.assert_not_called()
        manager._send_frame_metadata.assert_not_called()


@pytest.mark.asyncio
async def test_run_inference_pipeline_returns_early_when_no_active_connections(
    manager: AnalyzerWebSocketManager,
    processing_state: ProcessingState,
) -> None:
    """Test that _run_inference_pipeline returns early when no active connections."""
    manager.active_connections.clear()
    manager._send_frame_metadata = AsyncMock()  # type: ignore

    detector = AsyncMock()
    estimator = MagicMock()
    frame = MagicMock()
    current_time = 2.0

    await manager._run_inference_pipeline(
        frame, processing_state, detector, estimator, current_time
    )

    detector.infer.assert_not_called()
    manager._send_frame_metadata.assert_not_called()


@pytest.mark.asyncio
async def test_run_inference_pipeline_combines_detected_and_interpolated(
    manager: AnalyzerWebSocketManager,
    processing_state: ProcessingState,
) -> None:
    """Test that _run_inference_pipeline combines detected and interpolated detections."""
    manager.active_connections.add(MagicMock())
    manager._send_frame_metadata = AsyncMock()  # type: ignore

    # pseudo detector and estimator
    detected = [Detection(x1=10, y1=20, x2=50, y2=60, cls_id=0, confidence=0.9)]
    detector = AsyncMock()
    detector.infer = AsyncMock(return_value=detected)
    estimator = MagicMock()
    estimator.estimate_distance_m = MagicMock(return_value=[2.5])

    manager._tracking_manager.match_detections_to_tracks = MagicMock(return_value={0})
    manager._tracking_manager.get_interpolated_detections_and_distances = MagicMock(
        return_value=(
            [Detection(x1=100, y1=100, x2=150, y2=160, cls_id=1, confidence=0.8)],
            [3.0],
        )
    )
    manager._tracking_manager._remove_stale_tracks = MagicMock()

    current_time = 2.0
    await manager._run_inference_pipeline(
        MagicMock(), processing_state, detector, estimator, current_time
    )

    manager._send_frame_metadata.assert_called_once()
    # Check arguments: frame_small, detections, distances, current_time, state
    args = manager._send_frame_metadata.call_args
    # args[0] are positional args
    # detections are at index 1, distances at index 2
    passed_detections = args[0][1]
    passed_distances = args[0][2]

    # should have both detected and interpolated
    assert len(passed_detections) == 2
    assert len(passed_distances) == 2
    assert passed_detections[0].cls_id == 0  # detected
    assert passed_detections[1].cls_id == 1  # interpolated
    assert passed_distances == [2.5, 3.0]


@pytest.mark.asyncio
async def test_run_inference_pipeline_excludes_updated_tracks_from_interpolation(
    manager: AnalyzerWebSocketManager,
    processing_state: ProcessingState,
) -> None:
    """Test that updated tracks are excluded from interpolation."""
    manager.active_connections.add(MagicMock())
    manager._send_frame_metadata = AsyncMock()  # type: ignore

    detected = [Detection(x1=10, y1=20, x2=50, y2=60, cls_id=0, confidence=0.9)]
    detector = AsyncMock()
    detector.infer.return_value = detected
    estimator = MagicMock()
    estimator.estimate_distance_m.return_value = [2.5]

    # track 0 was updated, track 1 exists but wasn't updated
    manager._tracking_manager.match_detections_to_tracks = MagicMock(return_value={0})
    manager._tracking_manager.get_interpolated_detections_and_distances = MagicMock(
        return_value=(
            [Detection(x1=100, y1=100, x2=150, y2=160, cls_id=1, confidence=0.8)],
            [3.0],
        )
    )
    manager._tracking_manager._remove_stale_tracks = MagicMock()

    current_time = 2.0
    await manager._run_inference_pipeline(
        MagicMock(), processing_state, detector, estimator, current_time
    )

    # make sure interpolation was called with excluded track IDs
    # the exclusion itself is tested separately
    manager._tracking_manager.get_interpolated_detections_and_distances.assert_called_once()
    call_args = (
        manager._tracking_manager.get_interpolated_detections_and_distances.call_args
    )
    assert call_args[1]["track_ids_to_exclude"] == {0}
