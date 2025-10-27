.PHONY: help lint lint-frontend lint-backend lint-go

help:
	@echo "make"
	@echo "		dev (or install)"
	@echo "			install all dependencies for development"
	@echo "		install-frontend"
	@echo "			install frontend dependencies (npm)"
	@echo "		install-backend"
	@echo "			install backend dependencies (uv)"
	@echo "		install-go"
	@echo "			install Go dependencies"
	@echo "		lint"
	@echo "			runs all linters (frontend, backend, and Go)"
	@echo "		lint-frontend"
	@echo "			lints frontend code with npm run lint"
	@echo "		lint-backend"
	@echo "			lints backend Python code with ruff"
	@echo "		lint-go"
	@echo "			lints Go WebRTC signaling code with golangci-lint"
	@echo "		format-backend"
	@echo "			formats backend Python code with ruff"

dev: install

install: install-frontend install-backend install-go

install-frontend:
	cd frontend && npm install

install-backend:
	cd backend && uv venv
	cd backend && uv pip install -r requirements.txt
	cd backend && uv pip install -r requirements-dev.txt

install-go:
	cd webrtc-signaling && go mod download

lint: lint-frontend lint-backend lint-go

lint-frontend:
	cd frontend && npm run lint

lint-backend:
	cd backend && uv run ruff check .

lint-go:
	# Note: CI uses golangci-lint-action for better caching and PR annotations
	cd webrtc-signaling && golangci-lint run

format-backend:
	cd backend && uv run ruff format .

