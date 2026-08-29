from pathlib import Path

import pikepdf
from PIL import Image
from typer.testing import CliRunner

from calpdf.cli import app

runner = CliRunner()


def _make_pdf_with_image(pdf_path: Path, image_path: Path) -> None:
    """Create a single-page PDF containing *image_path* as its cover."""
    from calpdf.replace import PageGeometry, build_cover_pdf

    geom = PageGeometry(width=612, height=792, user_unit=1.0)
    cover_pdf = build_cover_pdf(
        image_path, geom, pdf_path.parent, dpi=150, fit_mode="match-width"
    )
    # Use the cover PDF as the test file
    with pikepdf.open(cover_pdf) as pdf:
        pdf.save(pdf_path)


class TestExtractCoverCLI:
    def test_extract_to_output(self, sample_jpeg: Path, tmp_path: Path):
        pdf = tmp_path / "book.pdf"
        _make_pdf_with_image(pdf, sample_jpeg)
        out = tmp_path / "cover.jpg"
        result = runner.invoke(app, ["extract-cover", str(pdf), "-o", str(out)])
        assert result.exit_code == 0, result.output
        assert out.exists()
        assert "success:" in result.output.lower()

    def test_extract_default_path(self, sample_jpeg: Path, tmp_path: Path, monkeypatch):
        pdf = tmp_path / "book.pdf"
        _make_pdf_with_image(pdf, sample_jpeg)
        # Default writes to <stem>_cover.jpg in cwd
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["extract-cover", str(pdf)])
        assert result.exit_code == 0, result.output
        assert (tmp_path / "book_cover.jpg").exists()

    def test_extract_raw(self, sample_jpeg: Path, tmp_path: Path):
        pdf = tmp_path / "book.pdf"
        _make_pdf_with_image(pdf, sample_jpeg)
        out = tmp_path / "raw.jpg"
        result = runner.invoke(
            app, ["extract-cover", str(pdf), "-o", str(out), "--raw"]
        )
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_extract_no_image(self, sample_pdf: Path, tmp_path: Path):
        out = tmp_path / "out.jpg"
        result = runner.invoke(app, ["extract-cover", str(sample_pdf), "-o", str(out)])
        assert result.exit_code == 1
        assert "error:" in result.output.lower()

    def test_extract_page_out_of_range(self, sample_jpeg: Path, tmp_path: Path):
        pdf = tmp_path / "book.pdf"
        _make_pdf_with_image(pdf, sample_jpeg)
        out = tmp_path / "out.jpg"
        result = runner.invoke(
            app, ["extract-cover", str(pdf), "-o", str(out), "--page", "5"]
        )
        assert result.exit_code == 1

    def test_extract_png_with_alpha(self, sample_png: Path, tmp_path: Path):
        pdf = tmp_path / "book.pdf"
        _make_pdf_with_image(pdf, sample_png)
        out = tmp_path / "out.jpg"
        result = runner.invoke(app, ["extract-cover", str(pdf), "-o", str(out)])
        assert result.exit_code == 0, result.output
        # JPEG output must be valid RGB
        img = Image.open(out)
        assert img.mode == "RGB"
