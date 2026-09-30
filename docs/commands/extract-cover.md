# The `extract-cover` command

The `extract-cover` command extracts the cover image from a PDF page and saves it as a separate file. Use it to pull a cover out of a PDF so you can reuse the image in Calibre or another tool.

```bash
# Save the cover from the first page as book_cover.jpg
calpdf extract-cover book.pdf

# Save the cover to a specific file
calpdf extract-cover book.pdf -o cover.jpg

# Extract the image from the second page without re-encoding
calpdf extract-cover book.pdf --page 2 --raw -o cover.jpg
```

Without `--output`, calpdf saves the image in the current directory as `BOOK_STEM_cover.jpg`, where `BOOK_STEM` is the PDF file name without its extension. The command picks the largest image on the selected page, so it skips small icons and returns the image that most likely is the cover. To write the original bytes without re-encoding, use `--raw`.
