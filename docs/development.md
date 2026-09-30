# Development

To set up a development environment, run the following command:

```bash
uv sync --dev
```

The command installs the project and its development tools (`pytest`, `ruff`, `mypy`, and `mkdocs`).

To run the CLI from the working tree without installing it, use the following commands:

```bash
uv run calpdf --version
uv run python -m calpdf --version   # equivalent module entry point
```

To run tests and quality checks, use the following commands:

```bash
make check   # lint, type check, format check, docs build, and test
make test    # run tests only
make lint    # lint without modifying files
make format  # format Python and Markdown
```

`make check` runs `ruff`, `mypy`, `pytest`, `prettier --check` for `README.md` and the files in `docs/`, and a strict MkDocs build. You can also run the tools directly with `uv run`.

## Documentation

This site is built with [MkDocs](https://www.mkdocs.org/) and the [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) theme. The content lives in `docs/`, and the site configuration lives in `mkdocs.yml`.

To preview the site locally while you edit:

```bash
make docs-serve
```

To build the site once and fail on broken links or missing pages:

```bash
make docs
```

To publish a change, merge it to `main`. The `docs` workflow in `.github/workflows/docs.yml` builds the site and deploys it to GitHub Pages.

## Continuous integration

The _continuous integration (CI)_ workflow in `.github/workflows/ci.yml` runs the same checks:

- A lint job with `ruff check`, `ruff format --check`, and `mypy`.
- A test matrix on Python versions 3.11 through 3.13.

Dependencies are pinned in `uv.lock`. After you change `pyproject.toml`, run `uv lock` and commit the updated lockfile.
