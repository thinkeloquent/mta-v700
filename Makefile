# MTA-v700 Makefile
# Development commands for the monorepo

# Default ports
FASTIFY_PORT ?= 51000
FASTAPI_PORT ?= 52000

# Build parameters (set by CI/CD or manually)
BUILD_ID ?= local
BUILD_VERSION ?= 0.0.0-dev
GIT_COMMIT ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")
SHARED_ID ?= placeholder-shared-id
GLOBAL_ID ?= placeholder-global-id

# Get the directory where Makefile is located (project root)
MAKEFILE_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

# ============================================================================
# PYTHONPATH Configuration
# ============================================================================
# Build PYTHONPATH with packages_py/*/src and fastapi_apps/*
PYTHON_PATHS := $(shell for pkg in $(MAKEFILE_DIR)packages_py/*/src; do [ -d "$$pkg" ] && printf "%s:" "$$pkg"; done)
PYTHON_PATHS := $(PYTHON_PATHS)$(shell for app in $(MAKEFILE_DIR)fastapi_apps/*/; do [ -d "$$app" ] && printf "%s:" "$$app"; done)
# Remove trailing colon and export
PYTHON_PATHS := $(PYTHON_PATHS:%:=%)
export PYTHONPATH := $(PYTHON_PATHS):$(PYTHONPATH)

# Use local .venv if it exists, otherwise use system Python
VENV_DIR := $(MAKEFILE_DIR).venv
PYTHON := $(if $(wildcard $(VENV_DIR)/bin/python),$(VENV_DIR)/bin/python,python)
UVICORN := $(if $(wildcard $(VENV_DIR)/bin/uvicorn),$(VENV_DIR)/bin/uvicorn,uvicorn)

.PHONY: help setup install dev dev-fastify dev-fastapi build test lint format clean clean-ports docker-up docker-down

help:
	@echo "MTA-v700 Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make setup         - Run setup scripts, then install dependencies"
	@echo "  make install       - Install all dependencies (pnpm + poetry)"
	@echo ""
	@echo "Development:"
	@echo "  make dev           - Run all backends in parallel (cleans ports first)"
	@echo "  make dev-fastify   - Run Fastify server only (port 51000)"
	@echo "  make dev-fastapi   - Run FastAPI server only (port 52000)"
	@echo "  make clean-ports   - Kill processes on dev ports (51000, 52000)"
	@echo ""
	@echo "Build:"
	@echo "  make build         - Build all projects (frontend + backends)"
	@echo "  make test          - Run all tests"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint          - Lint all code"
	@echo "  make format        - Format all code"
	@echo "  make check         - Run all checks"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up     - Start database services"
	@echo "  make docker-down   - Stop database services"
	@echo ""
	@echo "Clean:"
	@echo "  make clean         - Clean build artifacts"

# Setup
setup:
	@echo "Installing pnpm dependencies (includes nx)..."
	pnpm install
	@echo "Running clean..."
	pnpm clean || true
	@echo "Running setup scripts..."
	@bash .bin/pyproject-remove-readme-line.sh || true
	@bash .bin/git-hook-setup.sh || true
	@python .bin/fix_pytest_test_namespaces.py || true
	@python .bin/pyproject-sync-pkg-repo.py || true
	@bash .bin/ts-apply-noImplicitAny.sh || true
	@echo "Installing poetry dependencies..."
	rm -rf ./logs && mkdir ./logs
	poetry --verbose lock || true
	poetry --verbose install --no-root || true
	npm run build
	@echo "Setup complete!"

install:
	pnpm install
	poetry install --no-root

# Clean development ports before starting
clean-ports:
	@bash .bin/clean-ports.sh

# Development - run backends in parallel (cleans ports first)
dev_build: clean-ports build
	@echo "Starting development servers..."
	@echo "  Fastify:  http://localhost:$(FASTIFY_PORT)"
	@echo "  FastAPI:  http://localhost:$(FASTAPI_PORT)"
	@echo ""
	@$(MAKE) -j2 dev-fastify dev-fastapi

# Development - run backends in parallel (cleans ports first)
dev: clean-ports
	@echo "Starting development servers..."
	@echo "  Fastify:  http://localhost:$(FASTIFY_PORT)"
	@echo "  FastAPI:  http://localhost:$(FASTAPI_PORT)"
	@echo ""
	@$(MAKE) dev-fastify & FASTIFY_PID=$$!; \
	$(MAKE) dev-fastapi & FASTAPI_PID=$$!; \
	sleep 5; \
	.bin/healthz-check.sh || true; \
	wait

dev-no-cache: clean clean-ports
	@echo "Starting development servers..."
	@echo "  Fastify:  http://localhost:$(FASTIFY_PORT)"
	@echo "  FastAPI:  http://localhost:$(FASTAPI_PORT)"
	@echo ""
	@$(MAKE) -j2 dev-fastify dev-fastapi

# Run Fastify backend (fastify_server)
dev-fastify:
	cd fastify_server && \
		PORT=$(FASTIFY_PORT) \
		BUILD_ID=$(BUILD_ID) \
		BUILD_VERSION=$(BUILD_VERSION) \
		GIT_COMMIT=$(GIT_COMMIT) \
		node src/main.mjs

# Run FastAPI backend (fastapi_server)
dev-fastapi:
	cd fastapi_server && \
		BUILD_ID=$(BUILD_ID) \
		BUILD_VERSION=$(BUILD_VERSION) \
		GIT_COMMIT=$(GIT_COMMIT) \
		$(UVICORN) app.main:app --reload --host 0.0.0.0 --port $(FASTAPI_PORT)

# Build
build:
	make -f Makefile.fastapi build-log
	make -f Makefile.fastify build-log
	
test:
	rm -rf ./logs && mkdir ./logs
	npm run test:log
	make -f Makefile.pytest build-log
	make -f Makefile.pytest test-log

# Code Quality
lint:
	pnpm lint

format:
	pnpm format

check:
	pnpm check

# Docker
docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

# Clean
clean:
	@# Only run pnpm clean if nx is available (node_modules installed)
	@if [ -d "node_modules" ] && command -v pnpm >/dev/null 2>&1; then pnpm clean || true; fi
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
