# The `apply-toc` command

The `apply-toc` command replaces the bookmarks of a PDF with the table of contents from a JSON file. It removes the existing bookmarks first, then writes the entries from the file.

```bash
calpdf apply-toc book.pdf toc.json
calpdf apply-toc book.pdf toc.json -o output.pdf
```

The first example updates the PDF in place and keeps a backup. The second example writes the result to a new file.

The command validates the file before applying it, and it reports an error for each invalid entry. It leaves the PDF's page labels, such as roman numerals for the front matter, as they are. For the JSON structure and field rules, see [The ToC JSON format](../reference/toc-json-format.md).

To read the bookmarks of a PDF as JSON first, use [`export-toc`](export-toc.md).
