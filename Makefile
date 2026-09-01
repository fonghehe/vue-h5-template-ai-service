SHELL := /bin/bash

IMAGE := vue-h5-template-ai-service

.DEFAULT_GOAL := help

.PHONY: help sync dev run test test-cov lint typecheck check format docker docker-run clean

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

sync: ## Install dependencies from the frozen lockfile
	uv sync --frozen

dev: ## Run the server with autoreload
	uv run uvicorn app.main:app --reload --port 8001

run: ## Run the server
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8001

test: ## Run the test suite
	uv run pytest

test-cov: ## Run the test suite with coverage
	uv run pytest --cov=app --cov-report=term-missing

lint: ## Run ruff check and format check
	uv run ruff check .
	uv run ruff format --check .

typecheck: ## Run mypy in strict mode
	uv run mypy app

format: ## Auto-format with ruff
	uv run ruff format .
	uv run ruff check --fix .

check: lint typecheck test ## Lint, typecheck and test in one pass

docker: ## Build the production image
	docker build -t $(IMAGE):latest .

docker-run: docker ## Run the image with the example environment
	docker run --rm -p 8001:8001 --env-file .env $(IMAGE):latest

clean: ## Remove caches and artifacts
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
