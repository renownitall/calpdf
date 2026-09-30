# The `info` command

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
