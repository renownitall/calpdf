import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Literal, Optional, overload

import typer

from calpdf.common import (
    AppError,
    ensure_backup,
    message,
    normalize_paths,
    same_path,
    validate_input_file,
    validate_output_dir,
)
from calpdf import output


@overload
def find_binary(name: str, required: Literal[True]) -> str: ...
@overload
def find_binary(name: str, required: Literal[False]) -> Optional[str]: ...
def find_binary(name: str, required: bool = True) -> Optional[str]:
    path = shutil.which(name)
    if path is None and required:
        raise AppError(f"'{name}' is required but not found on PATH.")
    return path


def qpdf_optimize(
    qpdf_bin: str, source: Path, output_path: Path, keep_metadata: bool = False
) -> int:
    cmd = [
        qpdf_bin,
        "--linearize",
        "--remove-structure",
        "--remove-unreferenced-resources=yes",
        "--object-streams=generate",
        "--optimize-images",
        "--recompress-flate",
        "--compression-level=9",
        "--coalesce-contents",
    ]

    if not keep_metadata:
        cmd += ["--remove-info", "--remove-metadata"]

    cmd += [str(source), str(output_path)]

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode


def strip_color_profiles(input_path: Path, output_path: Path) -> None:
    """Strip ICC color profiles without re-distilling the PDF.

    Unlike ``gs -sDEVICE=pdfwrite`` (which re-interprets the entire file
    through Ghostscript and rewrites fonts, content streams and the catalog),
    this surgically removes:

    * document-level ``/OutputIntents`` (where publisher ICC profiles live)
    * image-level ``/ICCBased`` color spaces (replaced by ``/DeviceRGB``)

    This preserves object counts, ``Producer``, ``StructTreeRoot`` and other
    objects (empirically ``gs`` drops 97 percent of objects on ``small2.pdf``,
    this drops one).
    """
    import pikepdf

    with pikepdf.open(input_path) as pdf:
        # Document-level OutputIntents (e.g. sRGB IEC61966, PDF/X)
        if "/OutputIntents" in pdf.Root:
            del pdf.Root["/OutputIntents"]

        # Image-level ICCBased → DeviceRGB
        # Iterate via raw objects: cheaper than decoding images, preserves bytes.
        for obj in pdf.objects:
            try:
                if obj.get("/Subtype") != pikepdf.Name("/Image"):
                    continue
                cs = obj.get("/ColorSpace")
                if cs is None:
                    continue
                # Direct ICCBased stream: /ColorSpace is the ICC stream itself
                # or Array [ /ICCBased <stream> ]
                is_iccbased = False
                alternate: object | None = None
                if isinstance(cs, pikepdf.Array) and len(cs) > 0:
                    if str(cs[0]) == "/ICCBased":
                        is_iccbased = True
                        # ICC stream may have /Alternate → prefer it
                        try:
                            icc_stream = cs[1]
                            alternate = icc_stream.get("/Alternate")
                        except Exception:
                            pass
                elif isinstance(cs, pikepdf.Stream) and cs.get("/N") is not None:
                    # Some producers write the ICC stream directly (has /N)
                    is_iccbased = True
                    alternate = cs.get("/Alternate")

                if is_iccbased:
                    # Prefer the ICC's Alternate, else fall back to DeviceRGB
                    if alternate is not None and str(alternate) in (
                        "/DeviceRGB",
                        "/DeviceGray",
                        "/DeviceCMYK",
                    ):
                        obj["/ColorSpace"] = alternate
                    else:
                        # Most ICC profiles in samples are RGB so DeviceRGB is safe.
                        # Pixel data is not re-encoded, the profile is just dropped.
                        obj["/ColorSpace"] = pikepdf.Name("/DeviceRGB")
            except Exception:
                # Not an image or unreadable ColorSpace. Skip it.
                continue

        pdf.save(output_path)


def main(
    input_pdf: Path = typer.Argument(..., help="Path to the input PDF file"),
    force: bool = typer.Option(
        False,
        "--force",
        help="Continue even if qpdf reports warnings or errors",
    ),
    strip_color: bool = typer.Option(
        False,
        "--strip-color-profiles",
        help="Strip ICC color profiles (OutputIntents and ICCBased images)",
    ),
    keep_metadata: bool = typer.Option(
        False,
        "--keep-metadata",
        help="Preserve PDF metadata (title, author, etc.) instead of stripping it.",
    ),
    output_pdf: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Write to this path instead of replacing the input file in place",
    ),
) -> None:
    """Optimize a PDF with qpdf (linearize, compress, strip metadata)."""
    if output_pdf is None or same_path(input_pdf, output_pdf):
        output_file, backup_file = normalize_paths(input_pdf)
        in_place = True
    else:
        output_file = output_pdf
        backup_file = None
        in_place = False
    try:
        validate_input_file(input_pdf, label="Input PDF")
        validate_output_dir(output_file)
        qpdf_bin = find_binary("qpdf", required=True)
        if in_place:
            assert backup_file is not None  # guaranteed by normalize_paths above
            ensure_backup(output_file, backup_file)
            source = backup_file
        else:
            source = input_pdf
        with tempfile.TemporaryDirectory(dir=str(output_file.parent)) as tmp:
            workdir = Path(tmp)
            qpdf_source = source
            if strip_color:
                stripped = workdir / "pre_optimize.pdf"
                output.info("Stripping color profiles...")
                strip_color_profiles(source, stripped)
                output.info("Color profiles removed.")
                qpdf_source = stripped
            output.info(f"Optimizing '{output_file}' with qpdf...")
            exit_code = qpdf_optimize(
                qpdf_bin, qpdf_source, output_file, keep_metadata=keep_metadata
            )
            if exit_code != 0:
                if exit_code == 3:
                    output.warning(
                        "qpdf completed with warnings. Inspect the output carefully."
                    )
                elif force:
                    output.warning(
                        f"qpdf failed (exit {exit_code}), "
                        "--force set, continuing anyway."
                    )
                else:
                    raise AppError(f"qpdf failed (exit {exit_code}).")
            if not output_file.is_file() or output_file.stat().st_size == 0:
                raise AppError(
                    f"qpdf produced no output file at '{output_file}' "
                    f"(qpdf exit code: {exit_code})."
                )

        backup_note = f" (backup: '{backup_file}')" if backup_file else ""
        output.success(f"Success: Optimized '{output_file}'{backup_note}.")

    except typer.Exit:
        raise
    except AppError as exc:
        output.error(str(exc))
        raise typer.Exit(1) from None
    except Exception as exc:
        output.error(message(exc))
        raise typer.Exit(1) from None
