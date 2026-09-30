# The ToC JSON format

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

[`export-toc`](../commands/export-toc.md) produces files in this format, and [`apply-toc`](../commands/apply-toc.md) reads them to replace a PDF's bookmarks.

For the field-by-field specification, run `calpdf apply-toc --help`.
