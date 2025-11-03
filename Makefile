# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT

.PHONY: help lint lint-frontend lint-backend lint-licensing test test-frontend test-backend format format-frontend format-backend docker-build docker-build-frontend docker-build-backend docker-run-frontend docker-run-backend docker-stop docker-clean

help:
	@echo "make"
	@echo "		dev (or install)"
	@echo "			install all dependencies for development"
	@echo "		install-frontend"
	@echo "			install frontend dependencies (npm)"
	@echo "		install-backend"
	@echo "			install backend dependencies (uv)"
	@echo "		lint"
	@echo "			runs all linters and type checking (frontend, backend, licensing)"
	@echo "		lint-frontend"
	@echo "			lints frontend code with npm run lint"
	@echo "		lint-backend"
	@echo "			lints backend Python code with ruff"
	@echo "		lint-licensing"
	@echo "			lints licensing files with reuse"
	@echo "		type-check-backend"
	@echo "			type checks backend Python code with mypy"
	@echo "		format"
	@echo "			formats all code (frontend and backend)"
	@echo "		format-frontend"
	@echo "			formats frontend code with prettier"
	@echo "		format-backend"
	@echo "			formats backend Python code with ruff"
	@echo "		test"
	@echo "			runs all tests (frontend and backend)"
	@echo "		test-frontend"
	@echo "			runs frontend tests with vitest"
	@echo "		test-backend"
	@echo "			runs backend tests with pytest"
	@echo "		docker-build"
	@echo "			builds all Docker images (frontend and backend)"
	@echo "		docker-build-frontend"
	@echo "			builds frontend Docker image"
	@echo "		docker-build-backend"
	@echo "			builds backend Docker image"
	@echo "		docker-run-frontend"
	@echo "			runs frontend container on port 8080"
	@echo "		docker-run-backend"
	@echo "			runs backend container on port 8000"
	@echo "		docker-stop"
	@echo "			stops running containers"
	@echo "		docker-clean"
	@echo "			stops containers and removes Docker images"

dev: install

install: install-frontend install-backend

install-frontend:
	@echo "Installing frontend dependencies (Node.js 20 required, see .nvmrc)"
	cd src/frontend && npm install

install-backend:
	cd src/backend && uv python install   # Auto-uses .python-version (3.11)
	cd src/backend && uv venv             # Auto-uses .python-version (3.11)
	cd src/backend && uv pip install -r requirements.txt
	cd src/backend && uv pip install -r requirements-dev.txt

<<<<<<< HEAD
lint: lint-frontend lint-backend lint-licensing type-check-backend
=======
lint: lint-frontend lint-backend
>>>>>>> origin/main

lint-frontend:
	cd src/frontend && npm run lint

lint-backend:
	cd src/backend && uv run ruff check .
	cd src/backend && uv run mypy .

lint-licensing:
	reuse lint

format: format-frontend format-backend

format-frontend:
	cd src/frontend && npx prettier --write .

format-backend:
	cd src/backend && uv run ruff format .

test: test-frontend test-backend

test-frontend:
	cd src/frontend && npm test

test-backend:
	cd src/backend && uv run pytest

docker-build: docker-build-frontend docker-build-backend

docker-build-frontend:
	docker build -t robot-frontend:latest src/frontend

docker-build-backend:
	docker build -t robot-backend:latest src/backend

docker-run-frontend:
	@echo "Starting frontend container..."
	@docker run -d --rm -p 8080:80 --name robot-frontend-dev robot-frontend:latest
	@sleep 1
	@echo "Opening browser at http://localhost:8080"
	@open http://localhost:8080 || echo "Please open http://localhost:8080 in your browser"
	@echo "To stop: docker stop robot-frontend-dev"

docker-run-backend:
	@echo "Starting backend container..."
	@docker run -d --rm -p 8000:8000 --name robot-backend-dev robot-backend:latest
	@sleep 1
	@echo "Opening browser at http://localhost:8000"
	@open http://localhost:8000 || echo "Please open http://localhost:8000 in your browser"
	@echo "To stop: docker stop robot-backend-dev"

docker-stop:
	@docker stop robot-frontend-dev robot-backend-dev 2>/dev/null || true

docker-clean: docker-stop
	@docker rmi robot-frontend:latest robot-backend:latest || true

