.PHONY: test test-js test-py install install-js install-py build clean lint help

# =============================================================================
# DIRECTORIES
# =============================================================================
JS_DIR := packages_mjs/db_connection_redis
PY_DIR := packages_py/db_connection_redis

# =============================================================================
# DEFAULT TARGET
# =============================================================================
.DEFAULT_GOAL := help

# =============================================================================
# HELP
# =============================================================================
help:
	@echo "Available targets:"
	@echo "  install     - Install all dependencies (JS + Python)"
	@echo "  install-js  - Install JavaScript dependencies"
	@echo "  install-py  - Install Python dependencies"
	@echo "  build       - Build all packages"
	@echo "  build-js    - Build JavaScript package"
	@echo "  test        - Run all tests (JS + Python)"
	@echo "  test-js     - Run JavaScript tests"
	@echo "  test-py     - Run Python tests"
	@echo "  lint        - Run linters"
	@echo "  clean       - Remove build artifacts"

# =============================================================================
# INSTALL
# =============================================================================
install: install-js install-py

install-js:
	@echo "Installing JavaScript dependencies..."
	cd $(JS_DIR) && npm install

install-py:
	@echo "Installing Python dependencies..."
	cd $(PY_DIR) && poetry install

# =============================================================================
# BUILD
# =============================================================================
build: build-js

build-js:
	@echo "Building JavaScript package..."
#	cd $(JS_DIR) && npm run build

# =============================================================================
# TEST
# =============================================================================
test: test-js test-py

test-js:
	@echo "Running JavaScript tests..."
	cd $(JS_DIR) && npm test

test-py:
	@echo "Running Python tests..."
	cd $(PY_DIR) && poetry run pytest -v

# =============================================================================
# LINT
# =============================================================================
lint: lint-js lint-py

lint-js:
	@echo "Linting JavaScript..."
	cd $(JS_DIR) && npm run lint || true

lint-py:
	@echo "Linting Python..."
	cd $(PY_DIR) && poetry run ruff check src tests || true

# =============================================================================
# CLEAN
# =============================================================================
clean:
	@echo "Cleaning artifacts..."
	rm -rf $(JS_DIR)/dist
	rm -rf $(JS_DIR)/node_modules
	rm -rf $(JS_DIR)/coverage
	rm -rf $(PY_DIR)/.pytest_cache
	rm -rf $(PY_DIR)/.venv
	rm -rf $(PY_DIR)/dist
	rm -rf $(PY_DIR)/*.egg-info
	rm -rf $(PY_DIR)/htmlcov
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
