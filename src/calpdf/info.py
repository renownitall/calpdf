"""Inspect a PDF and report its properties."""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import pikepdf
import typer

from calpdf.common import AppError, message, validate_input_file, validate_output_dir
from calpdf import output


class InfoFormat(str, Enum):
    text = "text"
    json = "json"


def _count_outline(pdf: pikepdf.Pdf) -> tuple[int, int]:
    """Return (top_level, total) bookmark counts for *pdf*."""
    try:
        with pdf.open_outline() as outline:
            top_level = len(outline.root)

            def count(items) -> int:
                total = 0
                for item in items:
                    total += 1
                    total += count(item.children)
                return total

            total = count(outline.root)
            return top_level, total
    except Exception:
        return 0, 0


def collect_info(input_pdf: Path) -> dict[str, Any]:
    """Collect properties of *input_pdf* for display or JSON output."""
    validate_input_file(input_pdf, label="Input PDF")

    with pikepdf.open(input_pdf) as pdf:
        total_pages = len(pdf.pages)
        if total_pages == 0:
            raise AppError("Input PDF has no pages.")

        version = str(pdf.pdf_version) if hasattr(pdf, "pdf_version") else "unknown"
        size_bytes = input_pdf.stat().st_size

        pages_detail: list[dict[str, Any]] = []
        for idx, page in enumerate(pdf.pages, start=1):
            box = page.MediaBox
            width = float(box[2]) - float(box[0])
            height = float(box[3]) - float(box[1])
            rotate = int(page.obj.get("/Rotate", 0)) % 360
            if rotate in (90, 270):
                width, height = height, width
            pages_detail.append(
                {
                    "number": idx,
                    "width": width,
                    "height": height,
                    "rotate": rotate,
                }
            )

        top_level, total = _count_outline(pdf)

        info: dict[str, Any] = {
            "file": str(input_pdf),
            "pages": total_pages,
            "version": version,
            "sizeBytes": size_bytes,
            "outline": {"topLevel": top_level, "total": total},
            "pagesDetail": pages_detail,
        }
        return info


def _render_text(info: dict[str, Any]) -> str:
    """Format *info* as human-readable text."""
    lines: list[str] = []
    lines.append(f"File: {info['file']}")
    lines.append(f"Pages: {info['pages']}")
    lines.append(f"Version: {info['version']}")
    size = info["sizeBytes"]
    if size < 1024:
        size_label = f"{size} bytes"
    elif size < 1024 * 1024:
        size_label = f"{size / 1024:.1f} KB"
    else:
        size_label = f"{size / (1024 * 1024):.1f} MB"
    lines.append(f"Size: {size_label}")
    outline = info["outline"]
    lines.append(
        f"Bookmarks: {outline['total']} total ({outline['topLevel']} top-level)"
    )
    lines.append("Page sizes:")
    for entry in info["pagesDetail"][:5]:
        lines.append(
            f"  Page {entry['number']}: {entry['width']:.1f}"
            f"x{entry['height']:.1f} pt, rotate {entry['rotate']}"
        )
    if info["pages"] > 5:
        lines.append(f"  ... and {info['pages'] - 5} more pages")
    return "\n".join(lines)


def main(
    input_pdf: Path = typer.Argument(..., help="Path to the input PDF file"),
    fmt: InfoFormat = typer.Option(
        InfoFormat.text,
        "--format",
        "-f",
        help="Output format: 'text' (human-readable) or 'json' (machine-readable)",
    ),
    output_file: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Write output to this file instead of standard output (JSON only)",
    ),
) -> None:
    """Show information about a PDF.

    The command reports the number of pages, the PDF version, the file
    size, the bookmark count, and the size of each page. Use --format json
    to produce machine-readable output that you can pipe to another program.
    """
    try:
        if output_file is not None and fmt == InfoFormat.text:
            output.warning(
                "--output is ignored with --format text (text is always "
                "printed to the terminal)."
            )

        info = collect_info(input_pdf)

        if fmt == InfoFormat.json:
            text = json.dumps(info, indent=2, ensure_ascii=False)
            if output_file is not None:
                validate_output_dir(output_file)
                output_file.write_text(text, encoding="utf-8")
                output.info(f"Wrote info to '{output_file}'.")
            else:
                output.raw(text)
        else:
            output.info(_render_text(info))

    except typer.Exit:
        raise
    except AppError as exc:
        output.error(str(exc))
        raise typer.Exit(1) from None
    except Exception as exc:
        output.error(message(exc))
        raise typer.Exit(1) from None
