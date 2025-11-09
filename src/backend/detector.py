# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import asyncio
import os
from typing import Optional

import cv2
import numpy as np
from ultralytics import YOLO  # type: ignore[import-untyped]


class _Detector:
    def __init__(self) -> None:
        self._model = YOLO("yolov8n.pt")
        self._last_det: Optional[list[tuple[int, int, int, int, int, float]]] = None
        self._last_time: float = 0.0
        self._lock = asyncio.Lock()
        self._fov_deg: float = float(os.getenv("CAMERA_HFOV_DEG", "60"))

    async def infer(
        self, frame_bgr: np.ndarray
    ) -> list[tuple[int, int, int, int, int, float]]:
        now = asyncio.get_running_loop().time()
        if self._last_det is not None and (now - self._last_time) < 0.10:
            return self._last_det

        async with self._lock:
            now = asyncio.get_running_loop().time()
            if self._last_det is not None and (now - self._last_time) < 0.10:
                return self._last_det

            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            results = self._model.predict(rgb, imgsz=640, conf=0.25, verbose=False)
            dets: list[tuple[int, int, int, int, int, float]] = []
            if results:
                r = results[0]
                if r.boxes is not None and len(r.boxes) > 0:
                    xyxy = r.boxes.xyxy.cpu().numpy().astype(int)
                    cls = r.boxes.cls.cpu().numpy().astype(int)
                    conf = r.boxes.conf.cpu().numpy()
                    for (x1, y1, x2, y2), c, p in zip(xyxy, cls, conf):
                        dets.append(
                            (int(x1), int(y1), int(x2), int(y2), int(c), float(p))
                        )

            self._last_det = dets
            self._last_time = now
            return dets

    def estimate_distance_m(
        self, bbox: tuple[int, int, int, int], frame_width: int
    ) -> float:
        x1, y1, x2, y2 = bbox
        pix_w = max(1, x2 - x1)
        obj_w_m = float(os.getenv("OBJ_WIDTH_M", "0.5"))
        fov_rad = np.deg2rad(self._fov_deg)
        focal_px = (frame_width / 2.0) / np.tan(fov_rad / 2.0)
        dist_m = (obj_w_m * focal_px) / pix_w
        scale = float(os.getenv("DIST_SCALE", "1.5"))
        return float(dist_m * scale)


_detector = _Detector()
