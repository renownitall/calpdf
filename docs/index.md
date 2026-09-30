# calpdf

Hi. This is a simple PDF toolkit to run alongside Calibre.

Calibre organizes your e-book library, but it's the wrong tool for editing an individual PDF. calpdf handles jobs that normally need a PDF editor, like downloading a cover, swapping it in, shrinking a PDF, or rewriting the bookmarks, each as a single command.

This documentation is for people who are comfortable using a terminal. Start with [Installation](installation.md).

## Commands

Each command has its own page with its options and examples:

- The [`replace-cover`](commands/replace-cover.md) command replaces the first page of a PDF with a cover image, or inserts the image as a new first page.
- The [`dl-cover`](commands/dl-cover.md) command downloads a cover image for a book.
- The [`set-cover`](commands/set-cover.md) command downloads a cover and applies it to a PDF in one step.
- The [`extract-cover`](commands/extract-cover.md) command extracts the cover image from a PDF page and saves it as a separate file.
- The [`optimize`](commands/optimize.md) command makes a PDF smaller with `qpdf`.
- The [`info`](commands/info.md) command shows information about a PDF, such as its page count and file size.
- The [`export-toc`](commands/export-toc.md) command exports the bookmarks, or _table of contents (ToC)_, of a PDF.
- The [`apply-toc`](commands/apply-toc.md) command replaces the bookmarks of a PDF from a JSON file.

## Options and reference

You can place a few options before any subcommand. For the list, see [Global options](global-options.md).

The rest of the reference covers [the ToC JSON format](reference/toc-json-format.md) and [backup behavior](reference/backup-behavior.md).

To set up a development environment, see [Development](development.md).
