.PHONY: help setup fmt lint test cov demo dashboard screenshots check clean

help: ## List available targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-12s %s\n", $$1, $$2}'

setup: ## Install the package in editable mode with dev tools
	python -m pip install -e ".[dev]"

fmt: ## Format and autofix with ruff
	ruff format .
	ruff check --fix .

lint: ## Lint and check formatting
	ruff check .
	ruff format --check .

test: ## Run the test suite
	pytest -q

cov: ## Run tests with a coverage report
	pytest -q --cov --cov-report=term

demo: ## Run the end-to-end CLI demo
	python -m skillgraph_tutor.cli demo

dashboard: ## Serve the dashboard on the synthetic demo cohort
	python -m skillgraph_tutor.cli dashboard --demo

screenshots: ## Regenerate README screenshots (needs local Chrome/Edge)
	python scripts/capture_screenshots.py

check: lint test demo ## Everything CI runs on Python

clean: ## Remove build, cache and coverage output
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache .coverage coverage.xml htmlcov screenshots
