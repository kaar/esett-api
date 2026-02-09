.PHONY: lint format check test all db-up db-down

lint:
	uv run ruff check --fix .

format:
	uv run ruff format .

check:
	uv run ruff check .
	uv run pyright

test:
	uv run pytest -v

all: format lint check test
