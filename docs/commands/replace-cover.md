# The `replace-cover` command

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

By default, the command updates the PDF in place and keeps a backup of the original file. To write to a new file instead, use `--output` (short form `-o`). For more information, see [Backup behavior](../reference/backup-behavior.md).

The `--pages` option controls how many pages the image replaces, and it only matters in replace mode. The `--dpi` option sets the resolution of the cover image, with a default of 300 dots per inch.

The `--fit` option controls how the image fits on the page:

- `match-width` is the default. The cover page keeps the width of the body pages, and its height follows the image's aspect ratio, so the image fills the page with no cropping and no empty space.
- `fill` scales the image to cover the exact body page size and crops the parts that overflow.
- `fit` scales the image to fit inside the exact body page size and centers it on a white background.

If you swap the arguments and pass the image as the first argument, calpdf detects the mix-up and prints a hint.

The [`set-cover`](set-cover.md) command accepts the same options, except for the image argument.
