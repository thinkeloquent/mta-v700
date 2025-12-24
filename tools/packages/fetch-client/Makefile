.PHONY: test test-js test-py install install-js install-py clean lint formattcheck

# Directories
JS_DIR := packages_mjs/fetch-client
PY_DIR := packages_py/fetch_client

# Default target
.DEFAULT_GOAL := help

help:
	@echo "Available targets:"
	@echo "  install     - Install all dependencies (JS + Python)"
	@echo "  test        - Run all tests"
	@echo "  lint        - Run linters"
	@echo "  clean       - Clean artifacts"

# Test
test: test-js test-py

test-js:
	@echo "Running JavaScript tests..."
	cd $(JS_DIR) && npm test

test-py:
	@echo "Running Python tests..."
	cd $(PY_DIR) && poetry run pytest

# Install
install: install-js install-py

install-js:
	@echo "Installing JavaScript dependencies..."
	cd $(JS_DIR) && npm install

install-py:
	@echo "Installing Python dependencies..."
	cd $(PY_DIR) && poetry install

# Lint
lint: lint-js lint-py

lint-js:
	@echo "Linting JavaScript..."
	cd $(JS_DIR) && npm run lint

lint-py:
	@echo "Linting Python..."
	cd $(PY_DIR) && poetry run ruff check src tests

# Clean
clean:
	@echo "Cleaning artifacts..."
	rm -rf $(JS_DIR)/dist
	rm -rf $(JS_DIR)/node_modules
	rm -rf $(JS_DIR)/coverage
	rm -rf $(PY_DIR)/.pytest_cache
	rm -rf $(PY_DIR)/dist
	rm -rf $(PY_DIR)/*.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
