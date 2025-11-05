<!--
SPDX-FileCopyrightText: 2025 robot-visual-perception

SPDX-License-Identifier: CC-BY-4.0
-->

## Build, User and Technical Documentation

TODO

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

The choice of WebSocket for metadata streaming ensures low-latency, browser-native communication without the complexity of WebRTC DataChannels, which are faster in general but much harder to deal with in (future) cloud environments, since it uses UDP Peer-to-Peer connections. Load balancing in this case is also not trivial.

