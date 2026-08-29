"""Extract a cover image from a PDF."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import pikepdf
import typer
from PIL import Image
from pikepdf import PdfImage

from calpdf import output
from calpdf.common import AppError, message, validate_input_file, validate_output_dir


def _select_largest_image(page: Any) -> tuple[str, Any]:
    """Return the name and object of the largest image on *page*.

    The largest image is the one with the greatest pixel area. You need a
    single cover image, so choosing the largest image avoids small icons or
    inline graphics and returns the image that most likely is the cover.
    """
    images = page.get_images() if hasattr(page, "get_images") else page.images
    if not images:
        raise AppError("No images found on the selected page.")

    best_name: Optional[str] = None
    best_obj: Any = None
    best_area = -1

    for name, raw in images.items():
        try:
            pdf_image = PdfImage(raw)
            area = pdf_image.width * pdf_image.height
        except Exception:
            continue
        if area > best_area:
            best_area = area
            best_name = name
            best_obj = raw

    if best_name is None or best_obj is None:
        raise AppError("No readable images found on the selected page.")

    return best_name, best_obj


def extract_cover(
    input_pdf: Path,
    output_file: Optional[Path],
    page_number: int,
    use_raw: bool,
) -> Path:
    """Extract the cover image from *input_pdf* and write it to disk.

    Returns the path that was written.
    """
    validate_input_file(input_pdf, label="Input PDF")

    if page_number < 1:
        raise AppError("--page must be at least 1.")

    with pikepdf.open(input_pdf) as pdf:
        total = len(pdf.pages)
        if total == 0:
            raise AppError("Input PDF has no pages.")
        if page_number > total:
            raise AppError(
                f"PDF only has {total} page(s), can't extract page {page_number}."
            )

        page = pdf.pages[page_number - 1]
        _, raw_image = _select_largest_image(page)

        target: Path
        if output_file is not None:
            target = output_file
            validate_output_dir(target)
        else:
            candidate = Path(f"{input_pdf.stem}_cover.jpg")
            try:
                filters = raw_image.get("/Filter")
                if filters is not None and "/FlateDecode" in str(filters):
                    candidate = Path(f"{input_pdf.stem}_cover.png")
            except Exception:
                pass
            target = candidate
            validate_output_dir(target)

        if use_raw:
            pdf_image = PdfImage(raw_image)
            tmp_prefix = str(target.parent / f".calpdf_tmp_{target.stem}")
            written = pdf_image.extract_to(fileprefix=tmp_prefix)
            written_path = Path(written)
            if written_path.resolve() != target.resolve():
                written_path.replace(target)
            return target

        pdf_image = PdfImage(raw_image)
        pil_image = pdf_image.as_pil_image()
        if target.suffix.lower() in {".jpg", ".jpeg"} and pil_image.mode != "RGB":
            if pil_image.mode in ("RGBA", "LA"):
                background = Image.new("RGB", pil_image.size, (255, 255, 255))
                background.paste(pil_image, mask=pil_image.getchannel("A"))
                pil_image = background
            else:
                pil_image = pil_image.convert("RGB")
        pil_image.save(target)
        return target


def main(
    input_pdf: Path = typer.Argument(..., help="Path to the input PDF file"),
    output_file: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output image path (default: <PDF_stem>_cover.jpg)",
    ),
    page: int = typer.Option(
        1,
        "--page",
        "-p",
        help="Page number to extract the cover from (1-indexed, default: 1)",
    ),
    raw: bool = typer.Option(
        False,
        "--raw",
        help="Write the original image bytes without re-encoding",
    ),
) -> None:
    """Extract the cover image from a PDF page.

    The command finds the largest image on the selected page and saves it
    as a separate file. Use this to pull a cover out of a PDF so you can
    reuse it in Calibre or another tool.
    """
    try:
        written = extract_cover(input_pdf, output_file, page, raw)
        output.success(f"Success: Extracted cover to '{written}'.")
    except typer.Exit:
        raise
    except AppError as exc:
        output.error(str(exc))
        raise typer.Exit(1) from None
    except Exception as exc:
        output.error(message(exc))
        raise typer.Exit(1) from None
