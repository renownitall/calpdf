from pathlib import Path

import pikepdf
import pytest
from typer.testing import CliRunner

from calpdf.cli import app
from calpdf.replace import (
    AppError,
    FitMode,
    Job,
    Mode,
    PageGeometry,
    build_cover_pdf,
    load_image_rgb,
    target_page_geometry,
    validate,
    _cover_page_size,
)

runner = CliRunner()


class TestLoadImageRgb:
    def test_loads_jpeg(self, sample_jpeg: Path):
        img = load_image_rgb(sample_jpeg)
        assert img.mode == "RGB"
        assert img.size == (600, 800)

    def test_loads_png_with_alpha(self, sample_png: Path):
        img = load_image_rgb(sample_png)
        assert img.mode == "RGB"

    def test_rejects_unsupported_format(self, tmp_path: Path):
        bmp = tmp_path / "test.bmp"
        from PIL import Image

        Image.new("RGB", (10, 10)).save(bmp, "BMP")
        with pytest.raises(AppError, match="Unsupported"):
            load_image_rgb(bmp)

    def test_rejects_missing_file(self, tmp_path: Path):
        with pytest.raises(AppError, match="Could not read"):
            load_image_rgb(tmp_path / "nope.jpg")


class TestTargetPageGeometry:
    def test_basic(self, sample_pdf: Path):
        with pikepdf.open(sample_pdf) as pdf:
            geom = target_page_geometry(pdf, Mode.replace, 1)
            # Default US Letter
            assert abs(geom.width - 612) < 1
            assert abs(geom.height - 792) < 1
            assert geom.user_unit == 1.0

    def test_empty_pdf(self, tmp_path: Path):
        pdf_path = tmp_path / "empty.pdf"
        pdf = pikepdf.Pdf.new()
        pdf.save(pdf_path)
        pdf.close()
        with pikepdf.open(pdf_path) as pdf:
            with pytest.raises(AppError, match="no pages"):
                target_page_geometry(pdf, Mode.replace, 0)

    def test_index_out_of_range(self, sample_pdf: Path):
        with pikepdf.open(sample_pdf) as pdf:
            with pytest.raises(AppError, match="only has"):
                target_page_geometry(pdf, Mode.replace, 99)


class TestCoverPageSize:
    def test_match_width(self):
        geom = PageGeometry(width=612, height=792, user_unit=1.0)
        w, h = _cover_page_size(geom, 600, 800, FitMode.match_width)
        assert abs(w - 612) < 0.01
        # Height derived from image aspect ratio
        expected_h = 612 * (800 / 600)
        assert abs(h - expected_h) < 0.01

    def test_fill(self):
        geom = PageGeometry(width=612, height=792, user_unit=1.0)
        w, h = _cover_page_size(geom, 600, 800, FitMode.fill)
        assert w == 612
        assert h == 792

    def test_fit(self):
        geom = PageGeometry(width=612, height=792, user_unit=1.0)
        w, h = _cover_page_size(geom, 600, 800, FitMode.fit)
        assert w == 612
        assert h == 792


class TestBuildCoverPdf:
    def test_creates_single_page_pdf(self, sample_jpeg: Path, tmp_path: Path):
        geom = PageGeometry(width=612, height=792, user_unit=1.0)
        cover_path = build_cover_pdf(
            sample_jpeg, geom, tmp_path, dpi=150, fit_mode=FitMode.match_width
        )
        assert cover_path.exists()
        with pikepdf.open(cover_path) as pdf:
            assert len(pdf.pages) == 1


class TestValidate:
    def test_missing_input_pdf(self, tmp_path: Path, sample_jpeg: Path):
        job = Job(
            input_pdf=tmp_path / "nope.pdf",
            image_path=sample_jpeg,
            output_pdf=tmp_path / "out.pdf",
            mode=Mode.replace,
            pages=1,
            dpi=300,
            fit_mode=FitMode.match_width,
        )
        with pytest.raises(AppError, match="not found"):
            validate(job)

    def test_missing_image(self, sample_pdf: Path, tmp_path: Path):
        job = Job(
            input_pdf=sample_pdf,
            image_path=tmp_path / "nope.jpg",
            output_pdf=tmp_path / "out.pdf",
            mode=Mode.replace,
            pages=1,
            dpi=300,
            fit_mode=FitMode.match_width,
        )
        with pytest.raises(AppError, match="not found"):
            validate(job)

    def test_invalid_pages(self, sample_pdf: Path, sample_jpeg: Path, tmp_path: Path):
        job = Job(
            input_pdf=sample_pdf,
            image_path=sample_jpeg,
            output_pdf=tmp_path / "out.pdf",
            mode=Mode.replace,
            pages=0,
            dpi=300,
            fit_mode=FitMode.match_width,
        )
        with pytest.raises(AppError, match="at least 1"):
            validate(job)

    def test_invalid_dpi(self, sample_pdf: Path, sample_jpeg: Path, tmp_path: Path):
        job = Job(
            input_pdf=sample_pdf,
            image_path=sample_jpeg,
            output_pdf=tmp_path / "out.pdf",
            mode=Mode.replace,
            pages=1,
            dpi=50,
            fit_mode=FitMode.match_width,
        )
        with pytest.raises(AppError, match="dpi"):
            validate(job)


class TestReplaceCoverCLI:
    def test_replace_to_output(
        self, sample_pdf: Path, sample_jpeg: Path, tmp_path: Path
    ):
        out = tmp_path / "output.pdf"
        result = runner.invoke(
            app,
            [
                "replace-cover",
                str(sample_pdf),
                str(sample_jpeg),
                "-o",
                str(out),
            ],
        )
        assert result.exit_code == 0, result.stdout
        assert out.exists()
        with pikepdf.open(out) as pdf:
            assert len(pdf.pages) == 3  # replaced 1 of 3

    def test_insert_mode(self, sample_pdf: Path, sample_jpeg: Path, tmp_path: Path):
        out = tmp_path / "output.pdf"
        result = runner.invoke(
            app,
            [
                "replace-cover",
                str(sample_pdf),
                str(sample_jpeg),
                "-o",
                str(out),
                "--mode",
                "insert",
            ],
        )
        assert result.exit_code == 0, result.stdout
        with pikepdf.open(out) as pdf:
            assert len(pdf.pages) == 4  # inserted 1 into 3

    def test_in_place(self, sample_pdf: Path, sample_jpeg: Path):
        original_size = sample_pdf.stat().st_size
        result = runner.invoke(
            app,
            ["replace-cover", str(sample_pdf), str(sample_jpeg)],
        )
        assert result.exit_code == 0, result.stdout
        assert sample_pdf.exists()
        bak = sample_pdf.with_name(sample_pdf.name + ".bak")
        assert bak.exists()

    def test_swapped_arguments(
        self, sample_pdf: Path, sample_jpeg: Path, tmp_path: Path
    ):
        result = runner.invoke(
            app,
            [
                "replace-cover",
                str(sample_jpeg),  # wrong: image as first arg
                str(sample_pdf),  # wrong: pdf as second arg
            ],
        )
        assert result.exit_code == 1
        assert (
            "swap" in result.stdout.lower() or "swap" in (result.stderr or "").lower()
        )

    def test_missing_pdf(self, sample_jpeg: Path, tmp_path: Path):
        result = runner.invoke(
            app,
            [
                "replace-cover",
                str(tmp_path / "nope.pdf"),
                str(sample_jpeg),
                "-o",
                str(tmp_path / "out.pdf"),
            ],
        )
        assert result.exit_code == 1

    def test_replace_multiple_pages(
        self, sample_pdf: Path, sample_jpeg: Path, tmp_path: Path
    ):
        out = tmp_path / "output.pdf"
        result = runner.invoke(
            app,
            [
                "replace-cover",
                str(sample_pdf),
                str(sample_jpeg),
                "-o",
                str(out),
                "--pages",
                "2",
            ],
        )
        assert result.exit_code == 0
        with pikepdf.open(out) as pdf:
            assert len(pdf.pages) == 2  # replaced 2 of 3, added 1

    def test_fit_modes(self, sample_pdf: Path, sample_jpeg: Path, tmp_path: Path):
        for fit in ("match-width", "fill", "fit"):
            out = tmp_path / f"output_{fit}.pdf"
            result = runner.invoke(
                app,
                [
                    "replace-cover",
                    str(sample_pdf),
                    str(sample_jpeg),
                    "-o",
                    str(out),
                    "--fit",
                    fit,
                ],
            )
            assert result.exit_code == 0, f"fit={fit}: {result.stdout}"
            assert out.exists()
