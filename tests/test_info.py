import json
from pathlib import Path

from typer.testing import CliRunner

from calpdf.cli import app

runner = CliRunner()


class TestInfoCLI:
    def test_text_default(self, sample_pdf_with_toc: Path):
        result = runner.invoke(app, ["info", str(sample_pdf_with_toc)])
        assert result.exit_code == 0, result.output
        assert "pages:" in result.output.lower()
        assert "bookmarks:" in result.output.lower()

    def test_json_stdout(self, sample_pdf_with_toc: Path):
        result = runner.invoke(
            app, ["info", str(sample_pdf_with_toc), "--format", "json"]
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.stdout)
        assert data["pages"] == 5
        assert data["outline"]["total"] == 3

    def test_json_to_file(self, sample_pdf_with_toc: Path, tmp_path: Path):
        out = tmp_path / "info.json"
        result = runner.invoke(
            app, ["info", str(sample_pdf_with_toc), "--format", "json", "-o", str(out)]
        )
        assert result.exit_code == 0, result.output
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["pages"] == 5

    def test_text_with_output_warns(self, sample_pdf_with_toc: Path, tmp_path: Path):
        out = tmp_path / "out.txt"
        result = runner.invoke(
            app, ["info", str(sample_pdf_with_toc), "--format", "text", "-o", str(out)]
        )
        assert result.exit_code == 0
        assert "ignored" in result.output.lower()
        assert not out.exists()

    def test_missing_pdf(self, tmp_path: Path):
        result = runner.invoke(app, ["info", str(tmp_path / "nope.pdf")])
        assert result.exit_code == 1
        assert "error:" in result.output.lower()

    def test_empty_outline(self, sample_pdf: Path):
        result = runner.invoke(app, ["info", str(sample_pdf), "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["outline"]["total"] == 0
