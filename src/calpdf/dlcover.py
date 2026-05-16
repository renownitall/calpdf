from pathlib import Path
from typing import Optional

import requests
import typer

from calpdf.cli import app
from calpdf.common import AppError, message, validate_output_dir

URL_CHAIN: list[tuple[str, str]] = [
    ("Amazon SCRM", "https://m.media-amazon.com/images/P/{id}.01.MAIN._SCRM_.jpg"),
    ("Amazon SCLZZ", "https://m.media-amazon.com/images/P/{id}.01._SCLZZZZZZZ_.jpg"),
    ("OL ISBN", "https://covers.openlibrary.org/b/isbn/{id}-L.jpg?default=false"),
    ("OL OLID", "https://covers.openlibrary.org/b/olid/{id}-L.jpg?default=false"),
]

MIN_SIZE = 1024  # bytes; anything smaller is likely a placeholder

# JPEG files start with FF D8 FF; PNG files start with 89 50 4E 47
_IMAGE_SIGNATURES: list[tuple[str, bytes]] = [
    ("JPEG", b"\xff\xd8\xff"),
    ("PNG", b"\x89PNG"),
]


def _looks_like_image(data: bytes) -> bool:
    """Return True if *data* starts with a known image file signature."""
    return any(data.startswith(sig) for _, sig in _IMAGE_SIGNATURES)


def _detected_format(data: bytes) -> Optional[str]:
    """Return the format name if *data* starts with a known signature."""
    for name, sig in _IMAGE_SIGNATURES:
        if data.startswith(sig):
            return name
    return None


def download_cover(book_id: str, output_path: Path) -> Path:
    """Download a cover image for *book_id*, trying each source in order.

    Returns the output path on success.  Raises :class:`AppError` if no source
    yields a valid cover.
    """
    for label, url_template in URL_CHAIN:
        url = url_template.format(id=book_id)
        typer.echo(f"Trying {label}: {url}")

        try:
            response = requests.get(url, timeout=15, allow_redirects=True)
        except requests.RequestException as exc:
            typer.echo(f"  [-] Request failed: {exc}")
            continue

        if response.status_code != 200:
            typer.echo(f"  [-] Not found (HTTP {response.status_code}).")
            continue

        content = response.content
        content_length = len(content)

        if content_length < MIN_SIZE:
            typer.echo(
                f"  [-] Response too small ({content_length} bytes). "
                "Likely a placeholder. Skipping..."
            )
            continue

        if not _looks_like_image(content):
            detected = _detected_format(content)
            preview = content[:80].decode("utf-8", errors="replace")
            typer.echo(
                f"  [-] Response does not look like an image"
                f" (format: {detected or 'unknown'}, "
                f"starts with: {preview!r}). Skipping..."
            )
            continue

        output_path.write_bytes(content)
        fmt = _detected_format(content) or "unknown"
        typer.echo(f"  [+] Downloaded {fmt} cover ({content_length:,} bytes).")
        typer.echo(f"  [+] Saved as: {output_path}")
        return output_path

    raise AppError(f"Failed to find a valid cover for '{book_id}' across all sources.")


@app.command("dl-cover", help="Download a cover image for a book by ASIN or ISBN.")
def main(
    book_id: str = typer.Argument(
        ...,
        help="Amazon ASIN or ISBN identifier (e.g. B08X92NRKV, 9780140328721)",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (default: <BOOK_ID>_cover.jpg)",
    ),
) -> None:
    output_path = output or Path(f"{book_id}_cover.jpg")
    validate_output_dir(output_path)

    try:
        download_cover(book_id, output_path)
    except typer.Exit:
        raise
    except AppError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)
    except Exception as exc:
        typer.echo(f"Error: {message(exc)}", err=True)
        raise typer.Exit(1)
