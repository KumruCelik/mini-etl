install:
	uv sync --all-extras

lint:
	uv run ruff check . && uv run ruff format --check . && uv run mypy src

test:
	uv run pytest

run:
	uv run python -m mini_etl.cli

docker:
	docker build -t $(shell basename $(CURDIR)) .
