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

For the field-by-field specification, run `calpdf apply-toc --help`.

Use this format with [`export-toc`](../commands/export-toc.md), which writes it, and [`apply-toc`](../commands/apply-toc.md), which reads it.
