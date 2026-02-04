<!--
SPDX-FileCopyrightText: 2025 robot-visual-perception

SPDX-License-Identifier: CC-BY-4.0
-->

## Build, User and Technical Documentation
### Build Documentation (Setup + Run)
___
____
#### Supported platforms
- Local development: Windows, macOS, Linux
- Docker Compose: Linux only for camera access

#### Prerequisites
- Git
- Python 3.11
- Node.js 20
- `uv` (Python package manager)
- `make`
- Optional: Docker + Docker Compose

#### Clone and enter the repository
```bash
git clone https://github.com/amosproj/amos2025ws04-robot-visual-perception.git
```

#### Quick Start (Windows)
1) Run the PowerShell as Administrator, then change to the project root and run:
   ```powershell
   PowerShell -ExecutionPolicy Bypass -File .\start-optibot.ps1
   ```
2) The script installs dependencies, builds the project, starts services, and opens http://localhost:3000.

#### Manual Setup (All Platforms)
1) Install dependencies:
   ```bash
   make dev
   ```
2) Download models (default YOLO + MiDaS):
   ```bash
   make download-models
   ```
   Optional (export to ONNX too):
   ```bash
   make download-models-onnx
   ```
3) Start the video source service (Terminal 1):
   ```bash
   make run-streamer-webcam
   ```
   Or use a file source:
   ```bash
   VIDEO_FILE_PATH=video.mp4 make run-streamer-file
   ```
4) Start the analyzer service (Terminal 2):
   ```bash
   make run-analyzer-local
   ```
5) Start the frontend (Terminal 3):
   ```bash
   make run-frontend-local
   ```
6) Open the URL shown in the frontend terminal (typically http://localhost:3000).

#### Docker Compose (Linux only)
```bash
make docker-compose-up
```
Stop services:
```bash
make docker-compose-down
```

#### Build Docker Images (Optional)
```bash
make docker-build
```
Build individual images:
```bash
make docker-build-frontend
make docker-build-streamer
make docker-build-analyzer
make docker-build-analyzer-cuda
make docker-build-analyzer-rocm
```

#### Model Management (Optional)
```bash
make download-yolo
make download-midas
make download-depth-anything
make export-yolo-onnx
make export-midas-onnx
make export-onnx
```

### Configuration Options

All runtime configuration is controlled via environment variables (see `src/backend/common/config.py`). The analyzer can also load a JSON settings file; if present, those values override the current config values.

#### Analyzer settings file (JSON)
- `ANALYZER_SETTINGS_FILE` (default `config/analyzer.json`): path to a JSON file with key/value pairs matching the config names.

Example:
```json
{
  "MODEL_PATH": "models/yolo11n.pt",
  "DETECTOR_BACKEND": "onnx",
  "DEPTH_BACKEND": "depth_anything_v2",
  "DETECTOR_CONF_THRESHOLD": 0.35,
  "TRACKING_IOU_THRESHOLD": 0.2
}
```

#### Camera + Depth
- `CAMERA_INDEX` (default `0`): webcam device index.
- `REGION_SIZE` (default `5`): square region size for depth median/mean (odd recommended).
- `SCALE_FACTOR` (default `432.0`): empirical scale for depth estimation.
- `UPDATE_FREQ` (default `2`): frames between depth updates.
- `TARGET_SCALE_INIT` (default `0.8`): initial downscale for inference frames.
- `SMOOTH_FACTOR` (default `0.15`): smoothing factor for adaptive scaling.
- `MIN_SCALE` (default `0.2`): minimum allowed scale.
- `MAX_SCALE` (default `1.0`): maximum allowed scale.
- `FPS_THRESHOLD` (default `15.0`): FPS threshold to skip frames.
- `DEPTH_BACKEND` (default `torch`): `torch`, `onnx`, or `depth_anything_v2`.
- `DEPTH_ANYTHING_SCALE_FACTOR` (default `0.5`): scale factor for Depth Anything V2 outputs.
- `MIDAS_MODEL_TYPE` (default `MiDaS_small`): MiDaS variant to load.
- `MIDAS_MODEL_REPO` (default `intel-isl/MiDaS`): torch.hub repo for MiDaS.
- `MIDAS_CACHE_DIR` (default `models/midas_cache`): cache directory for MiDaS.
- `DEPTH_ANYTHING_MODEL` (default `depth-anything/Depth-Anything-V2-Small-hf`): Hugging Face model ID.
- `DEPTH_ANYTHING_CACHE_DIR` (default `models/depth_anything_cache`): cache directory for Depth Anything.
- `MIDAS_ONNX_MODEL_PATH` (default `models/midas_small.onnx`): MiDaS ONNX path.
- `MIDAS_ONNX_INPUT_SIZE` (default `384`): MiDaS ONNX input size.
- `MIDAS_ONNX_PROVIDERS` (default empty): comma-separated ONNX Runtime providers.
- `CAMERA_FOV_X_DEG` (default `78.0`): fallback horizontal FOV in degrees.
- `CAMERA_FOV_Y_DEG` (default `65.0`): fallback vertical FOV in degrees.
- `CAMERA_FX`, `CAMERA_FY`, `CAMERA_CX`, `CAMERA_CY` (default `0`): camera intrinsics (pixels). When set, overrides FOV-based intrinsics.
- `LOG_INTRINSICS` (default `false`): logs resolved intrinsics at runtime.

#### WebRTC + Networking
- `STUN_SERVER` (default `stun:stun.l.google.com:19302`): STUN server for ICE.
- `ICE_GATHERING_TIMEOUT` (default `5.0`): ICE gathering timeout (seconds).
- `STREAMER_OFFER_URL` (default `http://localhost:8000/offer`): upstream offer URL for analyzer.
- `CORS_ORIGINS` (default `*`): comma-separated allowed origins.

#### Video source
- `VIDEO_FILE_PATH` (default `video.mp4`): file used when `VIDEO_SOURCE_TYPE=file`.
- `VIDEO_SOURCE_TYPE` (default `webcam`): `webcam` or `file`.

#### Models + Inference
- `MODEL_PATH` (default `models/yolo11n-seg.pt`): YOLO model path. If you download `yolo11n.pt`, set this to match.
- `ONNX_MODEL_PATH` (default `<MODEL_PATH>.onnx`): YOLO ONNX model path.
- `DETECTOR_BACKEND` (default `torch`): `torch` or `onnx`.
- `DETECTOR_IMAGE_SIZE` (default `384`): detector input size.
- `DETECTOR_CONF_THRESHOLD` (default `0.25`): detection confidence threshold.
- `DETECTOR_IOU_THRESHOLD` (default `0.7`): detection IoU threshold.
- `DETECTOR_MAX_DETECTIONS` (default `100`): maximum detections per frame.
- `DETECTOR_NUM_CLASSES` (default `80`): number of classes.
- `TORCH_DEVICE` (default unset): force `cpu`, `cuda:0`, etc.
- `TORCH_HALF_PRECISION` (default `auto`): `auto`, `true`, or `false`.
- `ONNX_HALF_PRECISION` (default `false`): use FP16 for ONNX export.
- `ONNX_PROVIDERS` (default empty): comma-separated ONNX Runtime providers.
- `ONNX_SHARED_PREPROCESSING` (default `true`): reuse shared resize step for ONNX.
- `ONNX_IO_BINDING` (default `false`): enable ONNX IO binding.

#### Tracking
- `TRACKING_IOU_THRESHOLD` (default `0.1`): minimum IoU to match detection to track.
- `TRACKING_MAX_FRAMES_WITHOUT_DETECTION` (default `10`): frames before removing stale tracks.
- `TRACKING_EARLY_TERMINATION_IOU` (default `0.9`): early termination threshold.
- `TRACKING_CONFIDENCE_DECAY` (default `0.1`): confidence decay per interpolation factor.
- `TRACKING_MAX_HISTORY_SIZE` (default `5`): history size per track.
- `DETECTION_THRESHOLD` (default `2`): minimum detections before a track is active.

## Software architecture description

### Frontend (React + TypeScript)

- Displays the live video feed received through WebRTC.
- Connects to the backend via WebSocket to receive image.analysis results as metadata.
- Renders bounding boxes and distance overlays in real time.

### Backend (Python + FastAPI)

- Handles WebRTC video streaming using the aiortc library.
- Manages WebRTC signaling process.

#### Image Analysis Service (Python + Pytorch + OpenCV)

- Processes video frames to detect and locate objects in 3D space using ultralytics' YOLO models.
- Uses monocular depth estimation utilizing AI-Models like MiDas for distance calculation.
- Outputs object metadata (bounding boxes, labels, confidence, distance).
- Sends results to Frontend via Websocket.

### Infrastructure

- All components are containerized with Docker and will be orchestrated with Kubernets.
- Horizontal scaling is supported based on GPU availability and number of concurrent WebSocket clients.
- Logging and monitoring are provided through Prometheus and Grafana integrations.

### Design Rationale

The choice of WebSocket for metadata streaming ensures low-latency, browser-native communication [1] without the complexity of WebRTC DataChannels, which are faster in general but much harder to deal with in (future) cloud environments like Kubernetes, since it uses UDP Peer-to-Peer connections [2][3]. Load balancing in this case is also not trivial [4].

### References

1. Ably, "WebSockets explained: What they are and how they work", [link](https://ably.com/topic/websockets)

2. VideoSDK, "WebSockets vs WebRTC: Key Differences and Best Use Cases Explained", [link](https://www.videosdk.live/developer-hub/developer-hub/webrtc/websockets-vs-webrtc-differences)

3. Medium, "Kubernetes: The next step for WebRTC", [link](https://medium.com/l7mp-technologies/kubernetes-the-next-step-for-webrtc-fb8d8a33f24e)

4. ossrs, "Load Balancing Streaming Servers", [link](https://ossrs.net/lts/en-us/blog/load-balancing-streaming-servers)

