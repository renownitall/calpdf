# The `export-toc` command

The `export-toc` command reads the bookmarks of a PDF and exports them as a _table of contents (ToC)_. Page numbers are 1-indexed physical page positions.

By default, calpdf prints JSON to standard output, which is convenient for piping to other programs. To write the JSON to a file, use `--output`. To print a human-readable tree instead, use `--format tree`:

```bash
calpdf export-toc book.pdf
calpdf export-toc book.pdf -o toc.json
calpdf export-toc book.pdf --format tree
```

With `--format tree`, calpdf prints the tree to the terminal, so the `--output` option has no effect, and calpdf prints a warning if you pass it anyway.

The JSON output matches the format described in [The ToC JSON format](../reference/toc-json-format.md). A bookmark without a page target gets a `null` `pageNumber`.

To write the exported bookmarks back into a PDF, use [`apply-toc`](apply-toc.md).
