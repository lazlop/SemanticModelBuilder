.PHONY: help install install-dev test lint format type-check clean docs build

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install the package
	pip install -e .

install-dev:  ## Install the package with development dependencies
	pip install -e .[dev,docs,jupyter]

test:  ## Run tests
	pytest

test-cov:  ## Run tests with coverage
	pytest --cov=src/semantic_mpc_interface --cov-report=html --cov-report=term-missing

lint:  ## Run linting
	flake8 src/ tests/
	black --check src/ tests/
	isort --check-only src/ tests/

format:  ## Format code
	black src/ tests/
	isort src/ tests/

type-check:  ## Run type checking
	mypy src/

clean:  ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

docs:  ## Build documentation
	cd docs && make html

docs-serve:  ## Serve documentation locally
	cd docs/_build/html && python -m http.server 8000

build:  ## Build the package
	python -m build

release:  ## Build and upload to PyPI (requires twine)
	python -m build
	twine upload dist/*

dev-setup:  ## Set up development environment
	pip install -e .[dev,docs]
	pre-commit install