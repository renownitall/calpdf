# The `optimize` command

The `optimize` command makes a PDF smaller. It uses `qpdf` to linearize the file so a viewer can load it faster, to compress objects and images, and to remove metadata such as the title and author.

The following examples show common ways to use it:

```bash
calpdf optimize book.pdf
calpdf optimize book.pdf --keep-metadata
calpdf optimize book.pdf --strip-color-profiles
calpdf optimize book.pdf -o optimized.pdf
```

The first example updates the PDF in place and keeps a backup. To keep the metadata, use `--keep-metadata`. To remove ICC color profiles (document OutputIntents and image ICCBased spaces), use `--strip-color-profiles`.

For more information about backups, see [Backup behavior](../reference/backup-behavior.md).

If `qpdf` fails, calpdf stops and reports an error. To continue anyway, use `--force`. When `qpdf` reports warnings, calpdf prints a warning and continues.

The `optimize` command requires `qpdf`, which calpdf does not install for you. For more information, see [External dependencies](../installation.md#external-dependencies).
