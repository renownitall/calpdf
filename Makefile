# Run quality gates inside the project venv (requires `uv sync --dev`).
# The tools are invoked as modules. The venv's console-script shebangs can go
# stale when the venv moves, and `python -m` does not depend on them.
CHECK_PY := uv run
RUFF     := $(CHECK_PY) ruff
MYPY     := $(CHECK_PY) python -m mypy
PYTEST   := $(CHECK_PY) python -m pytest
MKDOCS   := $(CHECK_PY) mkdocs
PRETTIER := npx prettier

MD_FILES := README.md "docs/**/*.md"

.DEFAULT_GOAL := help

.PHONY: help check lint lint-py lint-md format format-py format-md docs docs-serve test

help:
	@echo "Available commands:"
	@echo "  check      - Lint, type check, format check, build docs, and test"
	@echo "  lint       - Lint without modifying files"
	@echo "  lint-py    - Lint Python (ruff check + format --check) and type check (mypy)"
	@echo "  lint-md    - Check Markdown formatting (prettier --check)"
	@echo "  format     - Format Python and Markdown"
	@echo "  format-py  - Format Python (ruff format)"
	@echo "  format-md  - Format Markdown (prettier --write)"
	@echo "  docs       - Build the documentation site (mkdocs build --strict)"
	@echo "  docs-serve - Serve the documentation site locally (mkdocs serve)"
	@echo "  test       - Run test suite (pytest)"

# --- Quality gate ---
check: lint docs test
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

docs:
	$(MKDOCS) build --strict

docs-serve:
	$(MKDOCS) serve

test:
	$(PYTEST)
