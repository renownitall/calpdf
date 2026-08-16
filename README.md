# calpdf

Hi.

This is a simple PDF toolkit I use to manage my Calibre library.

## Installation

```bash
uv pip install .
```

Or for development:

```bash
uv sync --dev
```

### External dependencies

- **qpdf**: required by the `optimize` command
- **Ghostscript** (`gs`): optional, only needed for `--strip-color-profiles`

## Global options

These flags can be placed before any subcommand:

```bash
calpdf --quiet <command> ...      # suppress all output except errors/warnings
calpdf --no-color <command> ...   # disable colored output
calpdf --version                  # show version and exit
```

## Commands

### `calpdf replace-cover`

Replace or prepend a cover image in a PDF.

```bash
# Replace the first page with a new cover image
calpdf replace-cover book.pdf cover.jpg

# Insert a cover without removing any pages
calpdf replace-cover book.pdf cover.jpg --mode insert

# Write to a new file instead of in-place
calpdf replace-cover book.pdf cover.jpg -o output.pdf

# Replace first 2 pages
calpdf replace-cover book.pdf cover.jpg --pages 2

# Control how the image fits the page
calpdf replace-cover book.pdf cover.jpg --fit fill
calpdf replace-cover book.pdf cover.jpg --fit fit
```

### `calpdf dl-cover`

Download a cover image by Amazon ASIN or ISBN.

```bash
calpdf dl-cover B08X92NRKV
calpdf dl-cover 9780140328721 -o mycover.jpg
```

### `calpdf set-cover`

Download a cover and apply it to a PDF in one step.

```bash
calpdf set-cover book.pdf B08X92NRKV
calpdf set-cover book.pdf 9780140328721 --mode insert
```

### `calpdf optimize`

Optimize a PDF with qpdf (linearize, compress, strip metadata).

```bash
calpdf optimize book.pdf
calpdf optimize book.pdf --keep-metadata
calpdf optimize book.pdf --strip-color-profiles
calpdf optimize book.pdf -o optimized.pdf
```

### `calpdf export-toc`

Export the PDF's table of contents (bookmarks).

```bash
# JSON to stdout (default, pipe-friendly)
calpdf export-toc book.pdf

# JSON to file
calpdf export-toc book.pdf -o toc.json

# Human-readable tree view
calpdf export-toc book.pdf --format tree
```

### `calpdf apply-toc`

Apply a JSON table of contents to a PDF.

```bash
calpdf apply-toc book.pdf toc.json
calpdf apply-toc book.pdf toc.json -o output.pdf
```

#### ToC JSON format

```json
[
  {
    "title": "Chapter 1",
    "pageNumber": 1,
    "children": [
      {
        "title": "Section 1.1",
        "pageNumber": 3,
        "children": []
      }
    ]
  }
]
```

Page numbers are 1-indexed physical page positions.

## Backup behavior

For in-place operations (`replace-cover`, `apply-toc`, `optimize` without `-o`),
the original file is preserved as `<filename>.bak` before modification. If a
`.bak` file already exists, it is used as the source and not overwritten.

## Development

Setup:

```bash
uv sync --dev   # installs the project plus dev tools (pytest, ruff, mypy)
```

Run the CLI from the working tree without installing it:

```bash
uv run calpdf --version
uv run python -m calpdf --version   # equivalent module entry point
```

Tests and code quality:

```bash
uv run pytest               # full test suite
uv run ruff check           # lint
uv run ruff check --fix     # lint with autofixes
uv run ruff format          # formatting
uv run mypy                 # type checking
```

CI runs the same checks: a lint job (ruff lint + format check + mypy) and a
test matrix on Python 3.11–3.13. Dependencies are pinned in `uv.lock`; after
changing `pyproject.toml`, run `uv lock` and commit the updated lockfile.
