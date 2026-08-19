# calpdf

Hi. This is a simple PDF toolkit for managing your Calibre library. You use the `calpdf` command from a terminal to download and replace book covers, optimize PDFs, and export or apply tables of contents.

This document is for people who are comfortable using a terminal. You'll need Python 3.11 or later and the `uv` package manager. If you don't have `uv` yet, see the [uv installation guide](https://docs.astral.sh/uv/).

## Installation

Run the following command from the project directory to install calpdf:

```bash
uv pip install .
```

To set up a development environment instead, see [Development](#development).

### External dependencies

calpdf uses two programs that it does not install for you:

- `qpdf`: The `optimize` command requires it. You must install it before you can optimize a PDF.
- Ghostscript (`gs`): The `--strip-color-profiles` option uses it. You only need it when you use that option.

## Global options

You can place the following options before any subcommand:

```bash
calpdf --quiet COMMAND ...      # suppress all output except errors and warnings
calpdf --no-color COMMAND ...   # disable colored output
calpdf --version                # show the version and exit
```

The `--quiet` and `--version` options have the short forms `-q` and `-v`. Run `calpdf` without arguments to see the help text and the list of commands. Run `calpdf COMMAND --help` to see a command's options.

## The `replace-cover` command

The `replace-cover` command replaces the first page of a PDF with a cover image, or inserts the image as a new first page. The image must be a PNG or JPEG file.

The following examples show the most common ways to use it:

```bash
# Replace the first page with a new cover image
calpdf replace-cover book.pdf cover.jpg

# Insert the image as a new first page without removing any pages
calpdf replace-cover book.pdf cover.jpg --mode insert

# Write to a new file instead of updating the input file
calpdf replace-cover book.pdf cover.jpg -o output.pdf

# Replace the first two pages
calpdf replace-cover book.pdf cover.jpg --pages 2
```

By default, the command updates the PDF in place and keeps a backup of the original file. Use `--output` (short form `-o`) to write to a new file instead. For more information, see [Backup behavior](#backup-behavior).

The `--pages` option controls how many pages the image replaces, and it only matters in replace mode. The `--dpi` option sets the resolution of the cover image, with a default of 300 dots per inch.

The `--fit` option controls how the image fits on the page:

- `match-width` is the default. The cover page keeps the width of the body pages, and its height follows the image's aspect ratio, so the image fills the page with no cropping and no empty space.
- `fill` scales the image to cover the exact body page size and crops the parts that overflow.
- `fit` scales the image to fit inside the exact body page size and centers it on a white background.

If you swap the arguments and pass the image as the first argument, calpdf detects the mix-up and prints a hint.

## The `dl-cover` command

The `dl-cover` command downloads a cover image for a book. Pass an *Amazon Standard Identification Number (ASIN)* or an *International Standard Book Number (ISBN)*:

```bash
# Download a cover by ASIN
calpdf dl-cover B08X92NRKV

# Download a cover by ISBN and save it with a specific name
calpdf dl-cover 9780140328721 -o mycover.jpg
```

Without `--output`, calpdf saves the image in the current directory as `BOOK_ID_cover.jpg`, where `BOOK_ID` is the identifier you passed. The identifier may only contain letters, digits, and dashes.

calpdf requests the cover from several sources in order, starting with Amazon and moving on to Open Library. It uses the first valid image it receives, and it skips responses that are too small or that don't look like an image.

## The `set-cover` command

The `set-cover` command downloads a cover and applies it to a PDF in one step, so you don't have to run `dl-cover` and then `replace-cover`.

```bash
calpdf set-cover book.pdf B08X92NRKV
calpdf set-cover book.pdf 9780140328721 --mode insert
```

The first example replaces the first page with the downloaded cover. The second inserts the cover as a new first page and keeps all the pages.

The command accepts the same options as `replace-cover`, except for the image argument. For more information about these options, see [The `replace-cover` command](#the-replace-cover-command).

## The `optimize` command

The `optimize` command makes a PDF smaller. It uses `qpdf` to linearize the file so a viewer can load it faster, to compress objects and images, and to remove metadata such as the title and author.

The following examples show common ways to use it:

```bash
calpdf optimize book.pdf
calpdf optimize book.pdf --keep-metadata
calpdf optimize book.pdf --strip-color-profiles
calpdf optimize book.pdf -o optimized.pdf
```

The first example updates the PDF in place and keeps a backup. Use `--keep-metadata` to keep the metadata, and use `--strip-color-profiles` to remove color profiles by converting colors to RGB with Ghostscript. This option requires the `gs` program.

If `qpdf` fails, calpdf stops and reports an error. Use `--force` to continue anyway. When `qpdf` reports warnings, calpdf prints a warning and continues.

## The `export-toc` command

The `export-toc` command reads the bookmarks of a PDF and exports them as a *table of contents (ToC)*. Page numbers are 1-indexed physical page positions.

By default, calpdf prints JSON to standard output, which is convenient for piping to other programs. Use `--output` to write the JSON to a file, or `--format tree` for a human-readable tree instead:

```bash
calpdf export-toc book.pdf
calpdf export-toc book.pdf -o toc.json
calpdf export-toc book.pdf --format tree
```

With `--format tree`, calpdf prints the tree to the terminal, so the `--output` option has no effect, and calpdf prints a warning if you pass it anyway.

The JSON output matches the format described in [The ToC JSON format](#the-toc-json-format). A bookmark without a page target gets a `null` `pageNumber`.

## The `apply-toc` command

The `apply-toc` command replaces the bookmarks of a PDF with the table of contents from a JSON file. It removes the existing bookmarks first, then writes the entries from the file.

```bash
calpdf apply-toc book.pdf toc.json
calpdf apply-toc book.pdf toc.json -o output.pdf
```

The first example updates the PDF in place and keeps a backup. The second example writes the result to a new file.

The command validates the file before applying it, and it reports an error for each invalid entry. A `title` must be a non-empty string, a `pageNumber` must be an integer between 1 and the number of pages, and `children` must be a list.

The command leaves the PDF's page labels, such as roman numerals for the front matter, as they are. For the JSON structure and page numbering rules, see [The ToC JSON format](#the-toc-json-format).

## The ToC JSON format

The JSON file is a list of entries, and each entry has three fields:

- `title`: The bookmark text. It must be a non-empty string.
- `pageNumber`: The physical page the bookmark points to, counting from 1. It must be between 1 and the total number of pages.
- `children`: A list of nested entries. Use an empty list for a bookmark without children.

The following sample shows the format:

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

Page numbers are 1-indexed physical page positions, so page 1 is the first page of the file, not the number printed on the page.

## Backup behavior

Commands that modify a PDF in place keep the original file. This applies to `replace-cover`, `set-cover`, `apply-toc`, and `optimize` without the `--output` option.

Before changing the file, calpdf copies the original to a file with the same name plus a `.bak` suffix, such as `book.pdf.bak`. If a `.bak` file already exists, calpdf uses it as the source and does not overwrite it. To restore the original, copy the `.bak` file back over the PDF.

## Development

Set up a development environment with the following command:

```bash
uv sync --dev
```

The command installs the project and its development tools (`pytest`, `ruff`, and `mypy`).

You can run the CLI from the working tree without installing it:

```bash
uv run calpdf --version
uv run python -m calpdf --version   # equivalent module entry point
```

Run tests and quality checks with the following commands:

```bash
uv run pytest             # full test suite
uv run ruff check         # lint
uv run ruff check --fix   # lint with autofixes
uv run ruff format        # formatting
uv run mypy               # type checking
```

The continuous integration (CI) workflow in `.github/workflows/ci.yml` runs the same checks:

- A lint job with `ruff check`, `ruff format --check`, and `mypy`.
- A test matrix on Python versions 3.11 through 3.13.

Dependencies are pinned in `uv.lock`. After you change `pyproject.toml`, run `uv lock` and commit the updated lockfile.
