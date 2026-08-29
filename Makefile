# Run quality gates inside the project venv (requires `uv sync --dev`).
CHECK_PY := uv run
RUFF     := $(CHECK_PY) ruff
MYPY     := $(CHECK_PY) mypy
PYTEST   := $(CHECK_PY) pytest
PRETTIER := npx prettier

MD_FILES := README.md

.DEFAULT_GOAL := help

.PHONY: help check lint lint-py lint-md format format-py format-md test

help:
	@echo "Available commands:"
	@echo "  check      - Lint, type check, format check, and test"
	@echo "  lint       - Lint without modifying files"
	@echo "  lint-py    - Lint Python (ruff check + format --check) and type check (mypy)"
	@echo "  lint-md    - Check Markdown formatting (prettier --check)"
	@echo "  format     - Format Python and Markdown"
	@echo "  format-py  - Format Python (ruff format)"
	@echo "  format-md  - Format Markdown (prettier --write)"
	@echo "  test       - Run test suite (pytest)"

# --- Quality gate ---
check: lint test
	@echo "all checks passed"

lint: lint-py lint-md
	@echo "lint passed"

lint-py:
	$(RUFF) check
	$(RUFF) format --check
	$(MYPY)

lint-md:
	$(PRETTIER) --check $(MD_FILES)

format: format-py format-md

format-py:
	$(RUFF) format

format-md:
	$(PRETTIER) --write $(MD_FILES)

test:
	$(PYTEST)
