install:
	uv sync --all-extras

lint:
	uv run ruff check . && uv run mypy src

test:
	uv run pytest

run:
	uv run python -m dev_setup.main

docker:
	docker build -t $(shell basename $(CURDIR)) .
