# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT

.PHONY: help \
	dev install install-frontend install-backend \
	lint lint-frontend lint-backend lint-licensing type-check-backend \
	format format-frontend format-backend \
	format-check format-check-frontend format-check-backend \
	test test-frontend test-backend \
	sbom sbom-check \
	run-backend-local run-frontend-local run-streamer-webcam run-streamer-file run-analyzer-local run-orchestrator-local \
	docker-build docker-build-frontend docker-build-backend docker-build-streamer \
	docker-build-analyzer docker-build-analyzer-cuda docker-build-analyzer-rocm \
	docker-compose-up docker-compose-down \
	download-models download-models-onnx export-onnx \
	download-yolo download-midas export-yolo-onnx export-midas-onnx

help:
	@echo "make"
	@echo "  dev (or install)"
	@echo "      install all dependencies for development"
	@echo "  install-frontend"
	@echo "      install frontend dependencies (npm)"
	@echo "  install-backend"
	@echo "      install backend dependencies (uv)"
	@echo "  lint"
	@echo "      runs all linters and type checking (frontend, backend, licensing)"
	@echo "  lint-frontend"
	@echo "      lints frontend code with npm run lint"
	@echo "  lint-backend"
	@echo "      lints backend Python code with ruff"
	@echo "  type-check-backend"
	@echo "      type checks backend Python code with mypy"
	@echo "  lint-licensing"
	@echo "      lints licensing files with reuse"
	@echo "  format"
	@echo "      formats all code (frontend and backend)"
	@echo "  format-frontend"
	@echo "      formats frontend code with prettier"
	@echo "  format-backend"
	@echo "      formats backend code with ruff"
	@echo "  format-check"
	@echo "      checks code formatting without modifying files (CI)"
	@echo "  format-check-frontend"
	@echo "      checks frontend formatting with prettier"
	@echo "  format-check-backend"
	@echo "      checks backend formatting with ruff"
	@echo "  test"
	@echo "      runs all tests (frontend and backend)"
	@echo "  test-frontend"
	@echo "      runs frontend tests with vitest"
	@echo "  test-backend"
	@echo "      runs backend tests with pytest"
	@echo "  sbom"
	@echo "      generates SBOM (sbom.json) and dependency CSV"
	@echo "  sbom-check"
	@echo "      checks if SBOM is up-to-date with dependencies"
	@echo "  run-orchestrator-local"
	@echo "      runs orchestrator service with dynamic port (starting from 8002)"
	@echo "  run-backend-local"
	@echo "      runs backend locally with uvicorn"
	@echo "  run-frontend-local"
	@echo "      runs frontend locally with Vite (uses VITE_BACKEND_URL)"
	@echo "  docker-build"
	@echo "      builds all Docker images (frontend and backend)"
	@echo "  docker-build-frontend"
	@echo "      builds frontend Docker image"
	@echo "  docker-build-backend"
	@echo "      builds backend Docker images (streamer + analyzer with CPU runtime)"
	@echo "  docker-build-streamer"
	@echo "      builds video source image (supports both webcam and file via VIDEO_SOURCE_TYPE)"
	@echo "  docker-build-analyzer"
	@echo "      builds analyzer image with ONNX CPU runtime (default)"
	@echo "  docker-build-analyzer-cuda"
	@echo "      builds analyzer image with ONNX CUDA runtime (nvidia GPU)"
	@echo "  docker-build-analyzer-rocm"
	@echo "      builds analyzer image with ONNX ROCm runtime (amd GPU)"
	@echo "  docker-compose-up"
	@echo "      starts all services with docker-compose (Linux only for camera access)"
	@echo "  docker-compose-down"
	@echo "      stops all docker-compose services"
	@echo "  export-onnx"
	@echo "      exports YOLO to ONNX (default opset 18; honors MODEL_PATH/ONNX_MODEL_PATH)"
	@echo "  export-midas-onnx"
	@echo "      exports MiDaS to ONNX (default opset 18; honors MIDAS_* env vars)"
	@echo "  download-models"
	@echo "      downloads YOLO and MiDaS models to src/backend/models/"
	@echo "  download-models-onnx"
	@echo "      downloads YOLO and MiDaS models, exports both to ONNX format"

dev: install

install: install-frontend install-backend

install-frontend:
	@echo "Installing frontend dependencies (Node.js 20 required, see .nvmrc)"
	cd src/frontend && npm install

install-backend:
# Auto-uses .python-version (3.11)
	cd src/backend && uv python install
# core + dev + inference + onnx-tools + onnx-cpu
	cd src/backend && uv sync --extra dev --extra inference --extra onnx-tools --extra onnx-cpu

lint: lint-frontend lint-backend lint-licensing

lint-frontend:
	cd src/frontend && npm run lint

lint-backend:
	cd src/backend && uv run ruff check .
	cd src/backend && uv run mypy .

lint-licensing:
	cd src/backend && uv run reuse lint

format: format-frontend format-backend

format-frontend:
	cd src/frontend && npx prettier --write .

format-backend:
	cd src/backend && uv run ruff format .

format-check: format-check-frontend format-check-backend

format-check-frontend:
	cd src/frontend && npx prettier --check .

format-check-backend:
	cd src/backend && uv run ruff format --check .

test: test-frontend test-backend

test-frontend:
	cd src/frontend && npm test

test-backend:
	cd src/backend && uv run pytest -s

run-streamer-webcam:
	@echo "Starting video source service (webcam) with dynamic port..."
	cd src/backend && VIDEO_SOURCE_TYPE=webcam uv run python -m streamer

run-streamer-file:
	@echo "Starting video source service (file) with dynamic port..."
	@echo "Set VIDEO_FILE_PATH env var to specify file (default: video.mp4)"
	cd src/backend && VIDEO_SOURCE_TYPE=file uv run python -m streamer

run-analyzer-local:
	@echo "Starting analyzer service with dynamic port..."
	cd src/backend && uv run python -m analyzer

run-orchestrator-local:
	@echo "Starting orchestrator service with dynamic port..."
	cd src/backend && uv run python -m orchestrator

run-backend-local: run-streamer-webcam
	@echo "Note: To run analyzer, use 'make run-analyzer-local' in another terminal"
	@echo "Note: To use file source instead, run 'make run-streamer-file'"

run-frontend-local:
	cd src/frontend && VITE_BACKEND_URL=http://localhost:8001 npm run dev

docker-build: docker-build-frontend docker-build-backend

docker-build-frontend:
	docker build \
		--build-arg VITE_BACKEND_URL=http://localhost:8001 \
		-t robot-frontend:latest src/frontend

docker-build-backend: docker-build-streamer docker-build-analyzer

docker-build-streamer:
	docker build -f src/backend/Dockerfile.streamer -t robot-streamer:latest src/backend

docker-build-analyzer:
	docker build -f src/backend/Dockerfile.analyzer --build-arg ONNX_RUNTIME=onnx-cpu -t robot-analyzer:latest src/backend

docker-build-analyzer-cuda:
	docker build -f src/backend/Dockerfile.analyzer --build-arg ONNX_RUNTIME=onnx-cuda -t robot-analyzer:cuda src/backend

docker-build-analyzer-rocm:
	docker build -f src/backend/Dockerfile.analyzer --build-arg ONNX_RUNTIME=onnx-rocm -t robot-analyzer:rocm src/backend

docker-compose-up:
	@echo "Note: Camera access requires Linux. On macOS/Windows, run things locally."
	docker compose up --build

docker-compose-down:
	docker compose down

# SBOM generation targets
sbom:
	@echo "Generating SBOM and dependency CSV..."
	@uv run python scripts/generate_sbom.py

sbom-check:
	@echo "Checking if SBOM is up-to-date..."
	@uv run python scripts/generate_sbom.py --check

# Model management targets
MODELS_DIR = models
MIDAS_CACHE = $(MODELS_DIR)/midas_cache
MIDAS_MODEL = MiDaS_small

# Get the absolute path to the project root
PROJECT_ROOT := $(shell pwd)

# Export models to ONNX
export-onnx: export-yolo-onnx export-midas-onnx

export-yolo-onnx:
	@echo "Exporting YOLO model to ONNX..."
	@mkdir -p $(MODELS_DIR)
	cd src/backend && uv run python ../../scripts/download_models.py \
	  --models yolo \
	  --yolo-model $(MODELS_DIR)/yolo11n.pt \
	  --export-onnx \
	  --output-dir $(MODELS_DIR)

export-midas-onnx:
	@echo "Exporting MiDaS model to ONNX..."
	@mkdir -p $(MIDAS_CACHE)
	cd src/backend && uv run python ../../scripts/download_models.py \
	  --models midas \
	  --midas-model-type $(MIDAS_MODEL) \
	  --midas-cache $(MIDAS_CACHE) \
	  --export-onnx \
	  --output-dir $(MODELS_DIR)

# Download models
download-models: download-yolo download-midas

download-yolo:
	@echo "Downloading YOLO model..."
	@mkdir -p $(MODELS_DIR)
	cd src/backend && uv run python ../../scripts/download_models.py \
	  --models yolo \
	  --yolo-model $(MODELS_DIR)/yolo11n.pt \
	  --output-dir $(MODELS_DIR)

download-midas:
	@echo "Downloading MiDaS model..."
	@echo "Available model types: MiDaS_small (default), DPT_Hybrid, DPT_Large"
	@mkdir -p $(MIDAS_CACHE)
	cd src/backend && uv run python ../../scripts/download_models.py \
	  --models midas \
	  --midas-model-type $(MIDAS_MODEL) \
	  --midas-cache $(MIDAS_CACHE) \
	  --output-dir $(MODELS_DIR)

# Combined download and export
# Export implies download, so we just need export
download-models-onnx: export-onnx

download-depth-anything:
	@echo "Downloading Depth Anything V2 model..."
	@mkdir -p $(MODELS_DIR)
	cd src/backend && uv run python ../../scripts/download_models.py \
	  --models depth-anything \
	  --output-dir $(MODELS_DIR)
