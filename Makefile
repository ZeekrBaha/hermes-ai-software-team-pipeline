.PHONY: test lint type

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check src/ tests/

type:
	uv run mypy src/
