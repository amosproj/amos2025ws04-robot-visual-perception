# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT

.PHONY: help \
	dev install install-frontend install-backend \
	lint lint-frontend lint-backend lint-licensing type-check-backend \
	format format-frontend format-backend \
	test test-frontend test-backend \
	sbom sbom-check \
	run-backend-local run-frontend-local \
	docker-build docker-build-frontend docker-build-backend \
	docker-compose-up docker-compose-down

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
	@echo "  run-backend-local"
	@echo "      runs backend locally with uvicorn"
	@echo "  run-frontend-local"
	@echo "      runs frontend locally with Vite (uses VITE_BACKEND_URL)"
	@echo "  docker-build"
	@echo "      builds all Docker images (frontend and backend)"
	@echo "  docker-build-frontend"
	@echo "      builds frontend Docker image"
	@echo "  docker-build-backend"
	@echo "      builds backend Docker image"
	@echo "  docker-compose-up"
	@echo "      starts all services with docker-compose (Linux only for camera access)"
	@echo "  docker-compose-down"
	@echo "      stops all docker-compose services"

dev: install

install: install-frontend install-backend

install-frontend:
	@echo "Installing frontend dependencies (Node.js 20 required, see .nvmrc)"
	cd src/frontend && npm install

install-backend:
# Auto-uses .python-version (3.11)
	cd src/backend && uv python install
# Auto-uses .python-version (3.11)
	cd src/backend && uv venv             
	cd src/backend && uv pip install -r requirements.txt
	cd src/backend && uv pip install -r requirements-dev.txt

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

test: test-frontend test-backend

test-frontend:
	cd src/frontend && npm test

test-backend:
	cd src/backend && uv run pytest -s

run-webcam-local:
	@echo "Starting webcam service on port 8000..."
	cd src/backend && uv run uvicorn webcam.main:app --host 0.0.0.0 --port 8000 --reload

run-analyzer-local:
	@echo "Starting analyzer service on port 8001..."
	cd src/backend && uv run uvicorn analyzer.main:app --host 0.0.0.0 --port 8001 --reload

run-backend-local: run-webcam-local
	@echo "Note: To run analyzer, use 'make run-analyzer-local' in another terminal"

run-frontend-local:
	cd src/frontend && VITE_BACKEND_URL=http://localhost:8001 npm run dev

docker-build: docker-build-frontend docker-build-backend

docker-build-frontend:
	docker build \
		--build-arg VITE_BACKEND_URL=http://localhost:8001 \
		-t robot-frontend:latest src/frontend

docker-build-backend: docker-build-webcam docker-build-analyzer

docker-build-webcam:
	docker build -f src/backend/Dockerfile.webcam -t robot-webcam:latest src/backend

docker-build-analyzer:
	docker build -f src/backend/Dockerfile.analyzer -t robot-analyzer:latest src/backend

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

