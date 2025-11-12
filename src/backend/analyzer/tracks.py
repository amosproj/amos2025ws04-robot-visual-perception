# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from aiortc import VideoStreamTrack
from aiortc.mediastreams import MediaStreamTrack
from av import VideoFrame

from common.core.detector import _get_detector
from common.utils.video import numpy_to_video_frame
from common.utils.geometry import draw_detections
from common.config import config


class AnalyzedVideoTrack(VideoStreamTrack):
    """
    WebRTC video track that applies YOLO detection to an upstream video source.

    Receives frames from a remote WebRTC stream (e.g., webcam service), runs
    YOLO-based object detection, draws bounding boxes and distance labels, and
    outputs annotated frames for analyzer clients.
    """

    kind = "video"

    def __init__(self, source: MediaStreamTrack, pc_id: int) -> None:
        """Initialize a new analyzed video track.

        Args:
            source (MediaStreamTrack): The upstream video source to process.
            pc_id (int): Identifier for the peer connection using this track.
        """
        super().__init__()
        self._source = source
        self._pc_id = pc_id

    async def recv(self) -> VideoFrame:
        """Receive, process, and return the next upstream frame.

        Reads a frame from the upstream source, performs YOLO detection, draws
        bounding boxes and distance labels, and returns the annotated frame as
        a WebRTC VideoFrame.

        Returns:
            VideoFrame: The processed frame with detection overlays.

        Raises:
            TypeError: If the upstream source does not provide a VideoFrame.
        """
        frame = await self._source.recv()
        if not isinstance(frame, VideoFrame):
            raise TypeError("Expected VideoFrame from source track")

        # Convert to numpy array
        base = frame.to_ndarray(format="bgr24")

        # Run YOLO detection
        detections = await _get_detector().infer(base)

        # Draw detections on frame
        overlay = base.copy()
        overlay = draw_detections(
            overlay,
            detections,
            config.CAMERA_HFOV_DEG,
            config.OBJ_WIDTH_M,
            config.DIST_SCALE,
        )
        return numpy_to_video_frame(overlay, frame.pts, frame.time_base)
