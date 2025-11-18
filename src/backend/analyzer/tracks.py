import time
import asyncio
import cv2
from aiortc import VideoStreamTrack
from aiortc.mediastreams import MediaStreamTrack
from av import VideoFrame
from common.utils.video import numpy_to_video_frame
from common.core.detector import _get_detector
from common.utils.geometry import _get_estimator_instance, draw_detections, get_detections


class AnalyzedVideoTrack(VideoStreamTrack):
    kind = "video"

    def __init__(self, source: MediaStreamTrack, pc_id: int):
        super().__init__()
        self._source = source
        self._pc_id = pc_id

        # Cache
        self._latest_frame = None
        self._last_overlay = None
        self._last_detections = None
        self._last_distances = None

        # Frequenz-Limit für YOLO/Overlay
        self._infer_interval = 0.12
        self._last_infer_time = 0

        # Lock für parallele Inference
        self._lock = asyncio.Lock()

        # Hintergrundtask starten
        asyncio.create_task(self._inference_loop())

    async def _inference_loop(self):
        detector = _get_detector()
        estimator = _get_estimator_instance()

        while True:
            frame = self._latest_frame
            if frame is not None:
                now = time.time()
                if now - self._last_infer_time >= self._infer_interval:
                    async with self._lock:
                        try:
                            # predict() synchron → in Thread
                            detections = await asyncio.to_thread(detector._model.predict, frame, imgsz=640, conf=0.25, verbose=False)
                            # convert to detection tuples
                            detections = get_detections(detections)
                            distances = await asyncio.to_thread(estimator.estimate_distance_m, frame, detections)

                            self._last_detections = detections
                            self._last_distances = distances
                            self._last_infer_time = now
                        except Exception as e:
                            print("Inference error:", e)
            await asyncio.sleep(0.005)

    async def recv(self) -> VideoFrame:
        frame = await self._source.recv()
        base = frame.to_ndarray(format="bgr24")
        rgb = cv2.cvtColor(base, cv2.COLOR_BGR2RGB)

        # immer speichern für Hintergrundtask
        self._latest_frame = rgb

        # Overlay anwenden, wenn vorhanden
        overlay = rgb.copy()
        if self._last_detections is not None:
            overlay = draw_detections(overlay, self._last_detections, self._last_distances)

        return numpy_to_video_frame(overlay, frame.pts, frame.time_base)
