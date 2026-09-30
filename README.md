# calpdf

Hi. This is a simple PDF toolkit to run alongside Calibre.

Calibre organizes your e-book library, but it's the wrong tool for editing an individual PDF. calpdf handles jobs that normally need a PDF editor, like downloading a cover, swapping it in, shrinking a PDF, or rewriting the bookmarks, each as a single command.

## Installation

To install calpdf, run the following command from the project directory:

```bash
uv pip install .
```

You need Python 3.11 or later and the [`uv`](https://docs.astral.sh/uv/) package manager. If you run Arch Linux, you can install the signed `calpdf-git` package from my [Forge repository](https://github.com/renownitall/forge) instead.

## Documentation

For the full documentation, see [calpdf documentation](https://renownitall.github.io/calpdf/). It covers [installation](https://renownitall.github.io/calpdf/installation/), [global options](https://renownitall.github.io/calpdf/global-options/), one page per command, and [the ToC JSON format](https://renownitall.github.io/calpdf/reference/toc-json-format/).

To preview the documentation while you edit it, run `make docs-serve`. For development setup, see [`docs/development.md`](docs/development.md).
