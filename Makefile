.PHONY: help lint lint-frontend lint-backend lint-go

help:
	@echo "make"
	@echo "		dev (or install)"
	@echo "			install all dependencies for development"
	@echo "		install-frontend"
	@echo "			install frontend dependencies (npm)"
	@echo "		install-backend"
	@echo "			install backend dependencies (uv)"
	@echo "		lint"
	@echo "			runs all linters (frontend, backend, and Go)"
	@echo "		lint-frontend"
	@echo "			lints frontend code with npm run lint"
	@echo "		lint-backend"
	@echo "			lints backend Python code with ruff"
	@echo "		format-backend"
	@echo "			formats backend Python code with ruff"

dev: install

install: install-frontend install-backend install-go

install-frontend:
	cd src/frontend && npm install

install-backend:
	cd src/backend && uv venv
	cd src/backend && uv pip install -r requirements.txt
	cd src/backend && uv pip install -r requirements-dev.txt

lint: lint-frontend lint-backend lint-go

lint-frontend:
	cd src/frontend && npm run lint

lint-backend:
	cd src/backend && uv run ruff check .

format-backend:
	cd src/backend && uv run ruff format .

