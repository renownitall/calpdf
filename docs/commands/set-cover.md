# The `set-cover` command

The `set-cover` command downloads a cover and applies it to a PDF in one step, so you don't have to run [`dl-cover`](dl-cover.md) and then [`replace-cover`](replace-cover.md).

```bash
calpdf set-cover book.pdf B08X92NRKV
calpdf set-cover book.pdf 9780140328721 --mode insert
```

The first example replaces the first page with the downloaded cover. The second inserts the cover as a new first page and keeps all the pages.

The command accepts the same options as `replace-cover`, except for the image argument. For more information about these options, see [The `replace-cover` command](replace-cover.md).
