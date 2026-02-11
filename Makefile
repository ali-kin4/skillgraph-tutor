.PHONY: setup test lint fmt demo

setup:
	python -m pip install -e . --no-build-isolation || true

fmt:
	PYTHONPATH=src ruff format .

lint:
	PYTHONPATH=src ruff check .
	PYTHONPATH=src ruff format --check .

test:
	PYTHONPATH=src pytest -q

demo:
	PYTHONPATH=src python -m skillgraph_tutor.cli demo
