<!--
SPDX-FileCopyrightText: 2025 robot-visual-perception

SPDX-License-Identifier: CC-BY-4.0
-->

* This is a minimal instruction guide to run the current project and will be adjusted over time. The descriptions here are based on the current state of the project and not the final state!

# OptiBot

Minimal object and distance detection via YOLO on a WebRTC video stream.

## What’s included
- FastAPI + aiortc backend streaming webcam frames
- YOLOv8n inference (Ultralytics) on the server
- Rough monocular distance estimate per detection
- WebRTC DataChannel sending metadata to the client
- React + Vite frontend showing the remote stream and detection stats

## Run backend (WebRTC)

1) Install deps
```
pip install -r src/backend/requirements.txt
```
or for just the WebRTC part
```
pip install -r src/backend/webrtc/requirements.txt
```

2) Start the server
```
uvicorn src.backend.webrtc.server:app --host 0.0.0.0 --port 8000
```
The first run will download `yolov8n.pt` automatically (so will take some time)

Optional environment variables:
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
VITE_BACKEND_URL=http://localhost:8000 npm run dev
```
Open the shown URL. You should see the remote video with green boxes and a small metadata panel.

## Notes
- The backend throttles inference to ~10 Hz to keep latency low.
- Overlay drawing is done server‑side to avoid extra client work.
- Metadata is sent best‑effort on a data channel; the UI shows a short summary and up to 5 entries.
