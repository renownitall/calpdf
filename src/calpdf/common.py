import shutil
from pathlib import Path
from typing import Optional


class AppError(Exception):
    pass


def message(exc: BaseException) -> str:
    text = str(exc).strip()
    return text if text else exc.__class__.__name__


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def same_path(a: Path, b: Path) -> bool:
    return a.expanduser().resolve(strict=False) == b.expanduser().resolve(strict=False)


def normalize_paths(input_path: Path) -> tuple[Path, Path]:
    """Normalize to (output_file, backup_file) pair.

    If *input_path* ends with ``.bak`` it is treated as the backup and the
    output is derived by stripping the suffix.  Otherwise *input_path* is the
    output and the backup is ``<name>.bak``.
    """
    if input_path.suffix == ".bak":
        backup_file = input_path
        output_file = input_path.with_suffix("")
    else:
        output_file = input_path
        backup_file = input_path.with_name(input_path.name + ".bak")
    return output_file, backup_file


def ensure_backup(output_file: Path, backup_file: Path) -> Path:
    """Make sure *backup_file* exists, creating it from *output_file* if needed.

    Returns the backup path.  Raises :class:`AppError` when neither file is
    present or the copy fails.
    """
    if backup_file.is_file():
        return backup_file
    if not output_file.is_file():
        raise AppError(f"Neither '{output_file}' nor '{backup_file}' found.")
    try:
        shutil.copy2(output_file, backup_file)
    except Exception as exc:
        raise AppError(
            f"Could not create backup '{backup_file}': {message(exc)}"
        ) from exc
    return backup_file


def validate_input_file(path: Path, label: str = "File") -> None:
    if not path.is_file():
        raise AppError(f"{label} '{path}' not found.")


def validate_in_place_input(path: Path) -> None:
    """Validate that at least one of the in-place pair exists.

    For in-place commands the PDF may be at *path* or at its ``.bak``
    sibling. Raise :class:`AppError` only when neither is present.
    """
    output_file, backup_file = normalize_paths(path)
    if not output_file.is_file() and not backup_file.is_file():
        raise AppError(f"Neither '{output_file}' nor '{backup_file}' found.")


def validate_output_dir(path: Path) -> None:
    if not path.parent.exists():
        raise AppError(f"Directory '{path.parent}' does not exist.")
    if path.exists() and path.is_dir():
        raise AppError(f"Output path '{path}' is a directory.")


# ---------------------------------------------------------------------------
# Argument-swap detection
# ---------------------------------------------------------------------------


def detect_swap(input_pdf: Path, image_path: Path) -> Optional[str]:
    pdf_exts = {".pdf"}
    img_exts = {".png", ".jpg", ".jpeg"}
    in_ext = input_pdf.suffix.lower()
    img_ext = image_path.suffix.lower()
    if in_ext in img_exts and img_ext in pdf_exts:
        return (
            f"It looks like the arguments may be swapped: "
            f"got an image ('{input_pdf}') as INPUT_PDF "
            f"and a PDF ('{image_path}') as IMAGE_PATH. "
            f"Try reversing the argument order."
        )
    if in_ext not in pdf_exts and img_ext in pdf_exts:
        return (
            f"Expected INPUT_PDF to be a PDF, but got '{input_pdf}'. "
            f"If the arguments are swapped, try reversing them."
        )
    return None
