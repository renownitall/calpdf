import io
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

import pikepdf
import typer
from PIL import Image, ImageOps, UnidentifiedImageError

from calpdf.cli import app
from calpdf.common import (
    AppError,
    detect_swap,
    ensure_backup,
    message,
    normalize_paths,
    remove_targets_that_would_dangle,
    same_path,
    validate_input_file,
    validate_output_dir,
)
from calpdf import output


class Mode(str, Enum):
    replace = "replace"
    insert = "insert"


class FitMode(str, Enum):
    match_width = "match-width"
    fill = "fill"
    fit = "fit"


@dataclass(frozen=True)
class Job:
    input_pdf: Path
    image_path: Path
    output_pdf: Optional[Path]
    mode: Mode
    pages: int
    dpi: int
    fit_mode: FitMode

    @property
    def in_place(self) -> bool:
        return self.output_pdf is None or same_path(self.input_pdf, self.output_pdf)

    @property
    def target_pdf(self) -> Path:
        return self.input_pdf if self.in_place else self.output_pdf


@dataclass(frozen=True)
class PageGeometry:
    width: float
    height: float
    user_unit: float


def validate(job: Job) -> None:
    if not job.input_pdf.is_file():
        if job.in_place:
            output_file, backup_file = normalize_paths(job.input_pdf)
            if not backup_file.is_file() and not output_file.is_file():
                raise AppError(f"Neither '{output_file}' nor '{backup_file}' found.")
        else:
            raise AppError(f"File '{job.input_pdf}' not found.")

    validate_input_file(job.image_path, label="Image file")

    if job.mode == Mode.replace and job.pages < 1:
        raise AppError("--pages must be at least 1 in replace mode.")

    if job.dpi < 72 or job.dpi > 1200:
        raise AppError("--dpi must be between 72 and 1200.")

    target = job.target_pdf
    if target is None:
        raise AppError("No output target resolved.")

    validate_output_dir(target)


def _get_inheritable_page_value(page_obj, key: str):
    current = page_obj
    seen: set[tuple[int, int]] = set()

    while isinstance(current, pikepdf.Dictionary):
        objgen = getattr(current, "objgen", None)
        if objgen is not None:
            if objgen in seen:
                break
            seen.add(objgen)

        if key in current:
            return current[key]

        current = current.get("/Parent")

    return None


def load_image_rgb(image_path: Path) -> Image.Image:
    try:
        with Image.open(image_path) as img:
            fmt = (img.format or "").upper()
            if fmt not in {"PNG", "JPEG"}:
                raise AppError(
                    f"Unsupported image format '{fmt or 'unknown'}'. "
                    "Only PNG and JPEG are supported."
                )

            img = ImageOps.exif_transpose(img)

            has_alpha = "A" in img.getbands() or "transparency" in img.info
            if has_alpha:
                rgba = img.convert("RGBA")
                background = Image.new("RGB", rgba.size, (255, 255, 255))
                background.paste(rgba, mask=rgba.getchannel("A"))
                return background

            return img.convert("RGB")

    except UnidentifiedImageError as exc:
        raise AppError(f"Could not read image '{image_path}': {exc}") from exc
    except OSError as exc:
        raise AppError(f"Could not read image '{image_path}': {exc}") from exc


def target_page_geometry(pdf: pikepdf.Pdf, mode: Mode, pages: int) -> PageGeometry:
    if len(pdf.pages) == 0:
        raise AppError("Input PDF has no pages.")

    idx = pages if mode == Mode.replace else 0

    if idx >= len(pdf.pages):
        raise AppError(
            f"Cannot determine target page size: "
            f"PDF only has {len(pdf.pages)} page(s), but index {idx} was requested."
        )

    page = pdf.pages[idx]
    crop_box = _get_inheritable_page_value(page.obj, "/CropBox")
    media_box = _get_inheritable_page_value(page.obj, "/MediaBox")
    rotate = int(_get_inheritable_page_value(page.obj, "/Rotate") or 0) % 360
    user_unit = float(_get_inheritable_page_value(page.obj, "/UserUnit") or 1.0)

    box = crop_box if crop_box is not None else media_box
    if box is None:
        raise AppError("Could not determine page box from target page.")

    width = float(box[2]) - float(box[0])
    height = float(box[3]) - float(box[1])

    if width <= 0 or height <= 0:
        raise AppError("Could not determine a valid page size from the target page.")

    if rotate in (90, 270):
        width, height = height, width

    return PageGeometry(width=width, height=height, user_unit=user_unit)


def _crop_to_fill(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    img_w, img_h = img.size
    scale = max(target_w / img_w, target_h / img_h)
    new_w, new_h = int(round(img_w * scale)), int(round(img_h * scale))
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    left, top = (new_w - target_w) // 2, (new_h - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def _fit_within(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    img_w, img_h = img.size
    scale = min(target_w / img_w, target_h / img_h)
    new_w, new_h = int(round(img_w * scale)), int(round(img_h * scale))
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    result = Image.new("RGB", (target_w, target_h), (255, 255, 255))
    left, top = (target_w - new_w) // 2, (target_h - new_h) // 2
    result.paste(resized, (left, top))
    return result


def _jpeg_bytes(img: Image.Image) -> bytes:
    buffer = io.BytesIO()
    img.save(buffer, "JPEG", quality=95, optimize=True)
    return buffer.getvalue()


def _cover_page_size(
    geometry: PageGeometry,
    img_w: int,
    img_h: int,
    fit_mode: FitMode,
) -> tuple[float, float]:
    body_w = geometry.width * geometry.user_unit
    body_h = geometry.height * geometry.user_unit

    if fit_mode == FitMode.match_width:
        page_w = body_w
        page_h = body_w * (img_h / img_w)
        return page_w, page_h

    return body_w, body_h


def build_cover_pdf(
    image_path: Path,
    geometry: PageGeometry,
    workdir: Path,
    dpi: int,
    fit_mode: FitMode,
) -> Path:
    img_rgb = load_image_rgb(image_path)
    img_w, img_h = img_rgb.size

    page_w, page_h = _cover_page_size(geometry, img_w, img_h, fit_mode)

    pixel_w = int(round(page_w * dpi / 72.0))
    pixel_h = int(round(page_h * dpi / 72.0))

    if pixel_w < 1 or pixel_h < 1:
        raise AppError(
            f"Computed invalid raster size {pixel_w}x{pixel_h} from "
            f"page size {(page_w, page_h)} and dpi {dpi}."
        )

    if fit_mode == FitMode.match_width:
        final_img = img_rgb.resize((pixel_w, pixel_h), Image.LANCZOS)
    elif fit_mode == FitMode.fill:
        final_img = _crop_to_fill(img_rgb, pixel_w, pixel_h)
    else:
        final_img = _fit_within(img_rgb, pixel_w, pixel_h)

    jpeg_data = _jpeg_bytes(final_img)

    cover_pdf = workdir / "cover.pdf"
    pdf = pikepdf.Pdf.new()

    page = pdf.add_blank_page(page_size=(page_w, page_h))

    media_box = pikepdf.Array([0, 0, page_w, page_h])
    page.obj["/MediaBox"] = media_box
    page.obj["/CropBox"] = pikepdf.Array(media_box)
    page.obj["/Rotate"] = 0

    if geometry.user_unit != 1.0:
        page.obj["/UserUnit"] = geometry.user_unit

    image_xobj = pdf.make_stream(jpeg_data)
    image_xobj["/Type"] = pikepdf.Name("/XObject")
    image_xobj["/Subtype"] = pikepdf.Name("/Image")
    image_xobj["/Width"] = pixel_w
    image_xobj["/Height"] = pixel_h
    image_xobj["/ColorSpace"] = pikepdf.Name("/DeviceRGB")
    image_xobj["/BitsPerComponent"] = 8
    image_xobj["/Filter"] = pikepdf.Name("/DCTDecode")

    xobjects = pikepdf.Dictionary()
    xobjects["/Im0"] = image_xobj

    resources = pikepdf.Dictionary()
    resources["/XObject"] = xobjects
    resources["/ProcSet"] = pikepdf.Array(
        [pikepdf.Name("/PDF"), pikepdf.Name("/ImageC")]
    )

    content = f"q\n{page_w:.6f} 0 0 {page_h:.6f} 0 0 cm\n/Im0 Do\nQ\n"
    content_stream = pdf.make_stream(content.encode("ascii"))

    page.obj["/Resources"] = resources
    page.obj["/Contents"] = content_stream

    pdf.save(cover_pdf)
    pdf.close()
    return cover_pdf


def apply_cover(pdf: pikepdf.Pdf, cover_pdf: Path, mode: Mode, pages: int) -> None:
    total_pages = len(pdf.pages)
    if total_pages == 0:
        raise AppError("Input PDF has no pages.")

    if mode == Mode.replace:
        if pages > total_pages:
            raise AppError(
                f"PDF only has {total_pages} page(s), can't replace {pages}."
            )
        remove_targets_that_would_dangle(pdf, pages)
        for _ in range(pages):
            del pdf.pages[0]

    with pikepdf.open(cover_pdf) as cover:
        pdf.pages.insert(0, cover.pages[0])

    cover_page = pdf.pages[0]
    media_box = pikepdf.Array(cover_page.MediaBox)
    cover_page.obj["/MediaBox"] = media_box
    cover_page.obj["/CropBox"] = pikepdf.Array(media_box)
    cover_page.obj["/Rotate"] = 0


def rewrite_pdf(
    source_pdf: Path,
    image_path: Path,
    target_pdf: Path,
    mode: Mode,
    pages: int,
    dpi: int,
    fit_mode: FitMode,
) -> None:
    with tempfile.TemporaryDirectory(dir=str(target_pdf.parent)) as tmp:
        workdir = Path(tmp)
        temp_output = workdir / target_pdf.name

        with pikepdf.open(source_pdf) as pdf:
            geometry = target_page_geometry(pdf, mode, pages)
            cover_pdf = build_cover_pdf(
                image_path=image_path,
                geometry=geometry,
                workdir=workdir,
                dpi=dpi,
                fit_mode=fit_mode,
            )
            apply_cover(pdf, cover_pdf, mode, pages)
            pdf.save(temp_output)

        temp_output.replace(target_pdf)
        with pikepdf.open(target_pdf) as verify:
            if len(verify.pages) == 0:
                raise AppError(f"Verification failed: '{target_pdf}' has no pages.")


def rewrite_in_place(job: Job) -> Path:
    output_file, backup_file = normalize_paths(job.input_pdf)
    ensure_backup(output_file, backup_file)
    rewrite_pdf(
        backup_file,
        job.image_path,
        output_file,
        job.mode,
        job.pages,
        job.dpi,
        job.fit_mode,
    )
    return backup_file


def rewrite_to_output(job: Job) -> None:
    rewrite_pdf(
        job.input_pdf,
        job.image_path,
        job.target_pdf,
        job.mode,
        job.pages,
        job.dpi,
        job.fit_mode,
    )


def success_text(job: Job, backup_file: Optional[Path] = None) -> str:
    action = (
        "inserted image as new first page"
        if job.mode == Mode.insert
        else f"replaced {job.pages} page(s) with image"
    )
    if job.in_place:
        output_file, _ = normalize_paths(job.input_pdf)
        verb, target = "Updated", output_file
    else:
        verb, target = "Created", job.target_pdf
    text = f"Success: {verb} '{target}' - {action}"
    if backup_file is not None:
        text += f" (backup: '{backup_file}')"
    return text


def run(job: Job) -> None:
    validate(job)
    if job.in_place:
        backup_file = rewrite_in_place(job)
        output.success(success_text(job, backup_file))
    else:
        rewrite_to_output(job)
        output.success(success_text(job))


@app.command(
    "replace-cover",
    help="Replace or prepend a cover image in a PDF.",
)
def main(
    input_pdf: Path = typer.Argument(..., help="Path to the input PDF file"),
    image_path: Path = typer.Argument(
        ..., help="Path to the replacement image (PNG or JPEG)"
    ),
    output_pdf: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Write to this path instead of replacing the input file in place",
    ),
    n_pages: int = typer.Option(
        1,
        "--pages",
        "-n",
        help="Number of pages to replace (only used in replace mode)",
    ),
    mode: Mode = typer.Option(
        Mode.replace,
        "--mode",
        "-m",
        help="'replace' removes first N pages; 'insert' keeps all pages",
    ),
    dpi: int = typer.Option(
        300,
        "--dpi",
        "-d",
        help="DPI for the cover image resolution (default: 300)",
    ),
    fit_mode: FitMode = typer.Option(
        FitMode.match_width,
        "--fit",
        help=(
            "'match-width' (default) scales to body page width, sets page "
            "height from image aspect ratio; full image, no crop, no bars. "
            "'fill' crops to fill the exact body page size. "
            "'fit' letterboxes to fit within the exact body page size."
        ),
    ),
) -> None:
    swap_msg = detect_swap(input_pdf, image_path)
    if swap_msg:
        output.error(swap_msg)
        raise typer.Exit(1)
    job = Job(
        input_pdf=input_pdf,
        image_path=image_path,
        output_pdf=output_pdf,
        mode=mode,
        pages=n_pages,
        dpi=dpi,
        fit_mode=fit_mode,
    )
    try:
        run(job)
    except typer.Exit:
        raise
    except AppError as exc:
        output.error(str(exc))
        raise typer.Exit(1)
    except Exception as exc:
        output.error(message(exc))
        raise typer.Exit(1)


@app.command(
    "set-cover",
    help="Download a cover and apply it to a PDF in one step.",
)
def set_cover(
    input_pdf: Path = typer.Argument(..., help="Path to the input PDF file"),
    book_id: str = typer.Argument(
        ..., help="Amazon ASIN or ISBN to download (e.g. B08X92NRKV, 9780140328721)"
    ),
    output_pdf: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Write to this path instead of replacing the input file in place",
    ),
    n_pages: int = typer.Option(
        1,
        "--pages",
        "-n",
        help="Number of pages to replace (only used in replace mode)",
    ),
    mode: Mode = typer.Option(
        Mode.replace,
        "--mode",
        "-m",
        help="'replace' removes first N pages; 'insert' keeps all pages",
    ),
    dpi: int = typer.Option(
        300,
        "--dpi",
        "-d",
        help="DPI for the cover image resolution (default: 300)",
    ),
    fit_mode: FitMode = typer.Option(
        FitMode.match_width,
        "--fit",
        help=(
            "'match-width' (default) scales to body page width, sets page "
            "height from image aspect ratio; full image, no crop, no bars. "
            "'fill' crops to fill the exact body page size. "
            "'fit' letterboxes to fit within the exact body page size."
        ),
    ),
) -> None:
    from calpdf.dlcover import download_cover

    try:
        in_place = output_pdf is None or same_path(input_pdf, output_pdf)
        if in_place:
            output_file, backup_file = normalize_paths(input_pdf)
            if not output_file.is_file() and not backup_file.is_file():
                raise AppError(f"Neither '{output_file}' nor '{backup_file}' found.")
        else:
            validate_input_file(input_pdf, label="Input PDF")
            validate_output_dir(output_pdf)

        with tempfile.TemporaryDirectory() as tmp:
            cover_image = Path(tmp) / f"{book_id}_cover.jpg"
            download_cover(book_id, cover_image)
            job = Job(
                input_pdf=input_pdf,
                image_path=cover_image,
                output_pdf=output_pdf,
                mode=mode,
                pages=n_pages,
                dpi=dpi,
                fit_mode=fit_mode,
            )
            run(job)
    except typer.Exit:
        raise
    except AppError as exc:
        output.error(str(exc))
        raise typer.Exit(1)
    except Exception as exc:
        output.error(message(exc))
        raise typer.Exit(1)
