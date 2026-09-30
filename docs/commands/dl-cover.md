# The `dl-cover` command

The `dl-cover` command downloads a cover image for a book. Pass an _Amazon Standard Identification Number (ASIN)_ or an _International Standard Book Number (ISBN)_:

```bash
# Download a cover by ASIN
calpdf dl-cover B08X92NRKV

# Download a cover by ISBN and save it with a specific name
calpdf dl-cover 9780140328721 -o mycover.jpg
```

Without `--output`, calpdf saves the image in the current directory as `BOOK_ID_cover.jpg`, where `BOOK_ID` is the identifier you passed. The identifier can only contain letters, digits, and dashes.

calpdf requests the cover from several sources and uses the first valid image it receives.

To download a cover and apply it to a PDF in one step, use [`set-cover`](set-cover.md).
