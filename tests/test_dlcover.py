import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import typer

from calpdf.cli import app
from calpdf.common import (
    AppError,
    ensure_backup,
    message,
    normalize_paths,
    same_path,
    validate_input_file,
    validate_output_dir,
)
from calpdf.dlcover import download_cover, _looks_like_image


def find_binary(name: str, required: bool = True) -> Optional[str]:
    path = shutil.which(name)
    if path is None and required:
        raise AppError(f"'{name}' is required but not found on PATH.")
    return path


def qpdf_optimize(
    qpdf_bin: str, source: Path, output: Path, keep_metadata: bool = False
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

    cmd += [str(source), str(output)]

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode


def strip_color_profiles(gs_bin: str, input_path: Path, output_path: Path) -> None:
    cmd = [
        gs_bin,
        "-q",
        "-dNOPAUSE",
        "-dBATCH",
        "-sDEVICE=pdfwrite",
        "-dPDFSETTINGS=/default",
        "-dColorConversionStrategy=/sRGB",
        "-dProcessColorModel=/DeviceRGB",
        "-dCompatibilityLevel=1.7",
        "-dCompressFonts=true",
        "-dSubsetFonts=true",
        "-dDetectDuplicateImages=true",
        f"-sOutputFile={output_path}",
        str(input_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise AppError(
            f"Ghostscript failed (exit {result.returncode}): {result.stderr.strip()}"
        )


@app.command(
    "optimize",
    help="Optimize a PDF with qpdf (linearize, compress, strip metadata).",
)
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
        help="Strip color profiles using Ghostscript (requires gs)",
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
    in_place = output_pdf is None or same_path(input_pdf, output_pdf)

    if in_place:
        output_file, backup_file = normalize_paths(input_pdf)
    else:
        output_file = output_pdf
        backup_file = None

    try:
        validate_input_file(input_pdf, label="Input PDF")
        validate_output_dir(output_file)

        qpdf_bin = find_binary("qpdf", required=True)
        gs_bin = find_binary("gs", required=strip_color) if strip_color else None

        if in_place:
            ensure_backup(output_file, backup_file)
            source = backup_file
        else:
            source = input_pdf

        with tempfile.TemporaryDirectory(dir=str(output_file.parent)) as tmp:
            workdir = Path(tmp)

            qpdf_source = source

            if strip_color and gs_bin:
                gs_output = workdir / "pre_optimize.pdf"
                typer.echo("Stripping color profiles with Ghostscript...")
                strip_color_profiles(gs_bin, source, gs_output)
                typer.echo("Color profiles removed.")
                qpdf_source = gs_output

            typer.echo(f"Optimizing '{output_file}' with qpdf...")
            exit_code = qpdf_optimize(
                qpdf_bin, qpdf_source, output_file, keep_metadata=keep_metadata
            )

            if exit_code != 0:
                if exit_code == 3:
                    typer.echo(
                        "Warning: qpdf completed with warnings."
                        "Inspect the output carefully.",
                        err=True,
                    )
                elif force:
                    typer.echo(
                        f"Warning: qpdf failed (exit {exit_code}), "
                        f"--force set, continuing anyway.",
                        err=True,
                    )
                else:
                    raise AppError(f"qpdf failed (exit {exit_code}).")

        backup_note = f" (backup: '{backup_file}')" if backup_file else ""
        typer.echo(f"Success: Optimized '{output_file}'{backup_note}.")

    except typer.Exit:
        raise
    except AppError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)
    except Exception as exc:
        typer.echo(f"Error: {message(exc)}", err=True)
        raise typer.Exit(1)
