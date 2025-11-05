<!--
SPDX-FileCopyrightText: 2025 robot-visual-perception

SPDX-License-Identifier: CC-BY-4.0
-->

# OptiBot

Minimal real-time object and distance detection via YOLO on a WebRTC video stream.

## What’s included
- FastAPI + aiortc backend streaming webcam frames
- YOLOv8n inference (Ultralytics) on the server
- Rough monocular distance estimate per detection
- WebRTC DataChannel sending metadata to the client
- React + Vite frontend showing the remote stream and detection stats

## Run backend (WebRTC)
Prereqs: Python 3.11+

1) Install dependencies (Mac)
```
cd src/backend
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

2) Start the webcam service
```
uv run uvicorn server:app --host 0.0.0.0 --port 8000
```
3) Start the analyzer service (separate terminal)
```
uv run uvicorn analyzer:app --host 0.0.0.0 --port 8001
```
The first analyzer start will download `yolov8n.pt` automatically (this will take some time)

Optional environment variables (more relevant later):
- `CAMERA_INDEX` (default 0) – select webcam device
- `CAMERA_HFOV_DEG` (default 60) – horizontal field of view used for distance estimate
- `OBJ_WIDTH_M` (default 0.5) – nominal object width used in distance estimate

## Run frontend
Prereqs: Node 18+.

1) Install deps
```
cd src/frontend
npm install
```

2) Start dev server
```
VITE_BACKEND_URL=http://localhost:8001 npm run dev
```
Open the shown URL in your console.

## Notes
- The webcam service mirrors and streams raw frames only; the analyzer handles YOLO inference and overlays.
- Analyzer inference is throttled to ~10 Hz to keep latency low.
