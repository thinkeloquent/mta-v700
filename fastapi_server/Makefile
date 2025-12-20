.PHONY: dev install test

VENV := .venv/bin

# Development server
dev:
	$(VENV)/uvicorn app.main:app --reload --host 0.0.0.0 --port 52000

# Install dependencies
install:
	poetry install

# Run tests
test:
	$(VENV)/pytest -v
