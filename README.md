# calpdf

Hi. This is a simple PDF toolkit to run alongside Calibre.

Calibre organizes your e-book library, but it's the wrong tool for editing an individual PDF. calpdf handles jobs that normally need a PDF editor, like downloading a cover, swapping it in, shrinking a PDF, or rewriting the bookmarks, each as a single command.

This document is for people who are comfortable using a terminal. You'll need Python 3.11 or later and the `uv` package manager. If you don't have `uv` yet, see the [uv installation guide](https://docs.astral.sh/uv/).

## Installation

To install calpdf, run the following command from the project directory:

```bash
uv pip install .
```

To set up a development environment instead, see [Development](#development).

### Arch Linux

If you run Arch Linux, you can install the signed `calpdf-git` package from my [Forge repository](https://github.com/renownitall/forge). For setup instructions, see the [Forge README](https://github.com/renownitall/forge#set-up-the-repository).

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

The `--quiet` and `--version` options have the short forms `-q` and `-v`. To see the help text and the list of commands, run `calpdf` without arguments. To view a command's options, run `calpdf COMMAND --help`.

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

By default, the command updates the PDF in place and keeps a backup of the original file. To write to a new file instead, use `--output` (short form `-o`). For more information, see [Backup behavior](#backup-behavior).

The `--pages` option controls how many pages the image replaces, and it only matters in replace mode. The `--dpi` option sets the resolution of the cover image, with a default of 300 dots per inch.

The `--fit` option controls how the image fits on the page:

- `match-width` is the default. The cover page keeps the width of the body pages, and its height follows the image's aspect ratio, so the image fills the page with no cropping and no empty space.
- `fill` scales the image to cover the exact body page size and crops the parts that overflow.
- `fit` scales the image to fit inside the exact body page size and centers it on a white background.

If you swap the arguments and pass the image as the first argument, calpdf detects the mix-up and prints a hint.

## The `dl-cover` command

The `dl-cover` command downloads a cover image for a book. Pass an _Amazon Standard Identification Number (ASIN)_ or an _International Standard Book Number (ISBN)_:

```bash
# Download a cover by ASIN
calpdf dl-cover B08X92NRKV

# Download a cover by ISBN and save it with a specific name
calpdf dl-cover 9780140328721 -o mycover.jpg
```

Without `--output`, calpdf saves the image in the current directory as `BOOK_ID_cover.jpg`, where `BOOK_ID` is the identifier you passed. The identifier can only contain letters, digits, and dashes.

calpdf requests the cover from several sources and uses the first valid image it receives.

## The `set-cover` command

The `set-cover` command downloads a cover and applies it to a PDF in one step, so you don't have to run `dl-cover` and then `replace-cover`.

```bash
calpdf set-cover book.pdf B08X92NRKV
calpdf set-cover book.pdf 9780140328721 --mode insert
```

The first example replaces the first page with the downloaded cover. The second inserts the cover as a new first page and keeps all the pages.

The command accepts the same options as `replace-cover`, except for the image argument. For more information about these options, see [The `replace-cover` command](#the-replace-cover-command).

## The `extract-cover` command

The `extract-cover` command extracts the cover image from a PDF page and saves it as a separate file. Use it to pull a cover out of a PDF so you can reuse it in Calibre or another tool.

```bash
# Save the cover from the first page as book_cover.jpg
calpdf extract-cover book.pdf

# Save the cover to a specific file
calpdf extract-cover book.pdf -o cover.jpg

# Extract the image from the second page without re-encoding
calpdf extract-cover book.pdf --page 2 --raw -o cover.jpg
```

Without `--output`, calpdf saves the image in the current directory as `BOOK_STEM_cover.jpg`, where `BOOK_STEM` is the PDF file name without its extension. The command picks the largest image on the selected page, so it skips small icons and returns the image that most likely is the cover. To write the original bytes without re-encoding, use `--raw`.

## The `optimize` command

The `optimize` command makes a PDF smaller. It uses `qpdf` to linearize the file so a viewer can load it faster, to compress objects and images, and to remove metadata such as the title and author.

The following examples show common ways to use it:

```bash
calpdf optimize book.pdf
calpdf optimize book.pdf --keep-metadata
calpdf optimize book.pdf --strip-color-profiles
calpdf optimize book.pdf -o optimized.pdf
```

The first example updates the PDF in place and keeps a backup. To keep the metadata, use `--keep-metadata`. To remove color profiles by converting colors to RGB with Ghostscript, use `--strip-color-profiles`. This option requires the `gs` program.

If `qpdf` fails, calpdf stops and reports an error. To continue anyway, use `--force`. When `qpdf` reports warnings, calpdf prints a warning and continues.

## The `info` command

The `info` command shows information about a PDF, such as the number of pages, the PDF version, the file size, the bookmark count, and the size of each page.

```bash
# Show a human-readable summary
calpdf info book.pdf

# Write machine-readable JSON to standard output
calpdf info book.pdf --format json

# Write JSON to a file
calpdf info book.pdf --format json -o info.json
```

By default, calpdf prints a summary to the terminal. To produce machine-readable output that you can pipe to another program, use `--format json`. With `--format json`, you can write the output to a file with `--output`. With `--format text`, the `--output` option has no effect and calpdf prints a warning if you pass it anyway.

## The `export-toc` command

The `export-toc` command reads the bookmarks of a PDF and exports them as a _table of contents (ToC)_. Page numbers are 1-indexed physical page positions.

By default, calpdf prints JSON to standard output, which is convenient for piping to other programs. To write the JSON to a file, use `--output`. To print a human-readable tree instead, use `--format tree`:

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

The command validates the file before applying it, and it reports an error for each invalid entry. It leaves the PDF's page labels, such as roman numerals for the front matter, as they are. For the JSON structure and field rules, see [The ToC JSON format](#the-toc-json-format).

## The ToC JSON format

A ToC file is a list of entries, and each entry has a `title`, a `pageNumber`, and a `children` list. The following sample shows the format:

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

For the field-by-field specification, run `calpdf apply-toc --help`.

## Backup behavior

Commands that modify a PDF in place (`replace-cover`, `set-cover`, `apply-toc`, and `optimize`) keep a backup of the original file with a `.bak` suffix. To restore the original, copy the `.bak` file back over the PDF. For the full behavior, run `calpdf --help`.

## Development

To set up a development environment, run the following command:

```bash
uv sync --dev
```

The command installs the project and its development tools (`pytest`, `ruff`, and `mypy`).

To run the CLI from the working tree without installing it, use the following commands:

```bash
uv run calpdf --version
uv run python -m calpdf --version   # equivalent module entry point
```

To run tests and quality checks, use the following commands:

```bash
make check   # lint, type check, format check, and test
make test    # run tests only
make lint    # lint without modifying files
make format  # format Python and Markdown
```

`make check` runs `ruff`, `mypy`, `pytest`, and `prettier --check` for `README.md`. You can also run the tools directly with `uv run`.

The _continuous integration (CI)_ workflow in `.github/workflows/ci.yml` runs the same checks:

- A lint job with `ruff check`, `ruff format --check`, and `mypy`.
- A test matrix on Python versions 3.11 through 3.13.

Dependencies are pinned in `uv.lock`. After you change `pyproject.toml`, run `uv lock` and commit the updated lockfile.
