"""Tests that verify consistent behavior across all commands."""

import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pikepdf
import pytest
from typer.testing import CliRunner

from calpdf.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pdf(path: Path, pages: int = 3) -> Path:
    pdf = pikepdf.Pdf.new()
    for _ in range(pages):
        pdf.add_blank_page(page_size=(612, 792))
    pdf.save(path)
    pdf.close()
    return path


def _make_toc_file(path: Path, entries: int = 2) -> Path:
    data = [
        {"title": f"Chapter {i + 1}", "pageNumber": i + 1, "children": []}
        for i in range(entries)
    ]
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Backup (.bak) consistency
# ---------------------------------------------------------------------------


class TestBackupConsistency:
    """Every in-place command must create a .bak and not overwrite an existing one."""

    def test_replace_cover_creates_backup(self, sample_pdf: Path, sample_jpeg: Path):
        result = runner.invoke(
            app, ["replace-cover", str(sample_pdf), str(sample_jpeg)]
        )
        assert result.exit_code == 0
        bak = sample_pdf.with_name(sample_pdf.name + ".bak")
        assert bak.exists()
        assert "backup" in result.output.lower()

    def test_apply_toc_creates_backup(self, sample_pdf: Path, tmp_path: Path):
        toc = _make_toc_file(tmp_path / "toc.json")
        result = runner.invoke(app, ["apply-toc", str(sample_pdf), str(toc)])
        assert result.exit_code == 0
        bak = sample_pdf.with_name(sample_pdf.name + ".bak")
        assert bak.exists()
        assert "backup" in result.output.lower()

    def test_optimize_creates_backup(self, sample_pdf: Path):
        mock_result = MagicMock()
        mock_result.returncode = 0
        with (
            patch("calpdf.optimize.shutil.which", return_value="/usr/bin/qpdf"),
            patch("calpdf.optimize.subprocess.run", return_value=mock_result),
        ):
            bak = sample_pdf.with_name(sample_pdf.name + ".bak")
            result = runner.invoke(app, ["optimize", str(sample_pdf)])
            assert result.exit_code == 0
            assert bak.exists()
            assert "backup" in result.output.lower()

    def test_replace_cover_preserves_existing_backup(
        self, sample_pdf: Path, sample_jpeg: Path
    ):
        bak = sample_pdf.with_name(sample_pdf.name + ".bak")
        # Must be a valid PDF so replace-cover can read from it
        shutil.copy2(sample_pdf, bak)
        original_size = bak.stat().st_size

        result = runner.invoke(
            app, ["replace-cover", str(sample_pdf), str(sample_jpeg)]
        )
        assert result.exit_code == 0
        # Backup must not have been overwritten
        assert bak.stat().st_size == original_size

    def test_apply_toc_preserves_existing_backup(
        self, sample_pdf: Path, tmp_path: Path
    ):
        bak = sample_pdf.with_name(sample_pdf.name + ".bak")
        shutil.copy2(sample_pdf, bak)
        original_size = bak.stat().st_size

        toc = _make_toc_file(tmp_path / "toc.json")
        result = runner.invoke(app, ["apply-toc", str(sample_pdf), str(toc)])
        assert result.exit_code == 0
        assert bak.stat().st_size == original_size

    def test_no_backup_with_output_flag(
        self, sample_pdf: Path, sample_jpeg: Path, tmp_path: Path
    ):
        """When --output is a different path, no .bak should be created."""
        out = tmp_path / "output.pdf"
        result = runner.invoke(
            app,
            ["replace-cover", str(sample_pdf), str(sample_jpeg), "-o", str(out)],
        )
        assert result.exit_code == 0
        bak = sample_pdf.with_name(sample_pdf.name + ".bak")
        assert not bak.exists()
        # Check the success line specifically; don't match against path
        # substrings that might contain "backup" in the tmp dir name.
        for line in result.output.splitlines():
            if line.lower().startswith("success:"):
                assert "(backup:" not in line.lower()


# ---------------------------------------------------------------------------
# Error handling consistency
# ---------------------------------------------------------------------------


class TestErrorHandlingConsistency:
    """All commands must print 'Error: ...' to output and exit 1 on failure."""

    def test_replace_cover_missing_pdf(self, sample_jpeg: Path, tmp_path: Path):
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
        assert "error:" in result.output.lower()

    def test_apply_toc_missing_pdf(self, tmp_path: Path):
        toc = _make_toc_file(tmp_path / "toc.json")
        result = runner.invoke(app, ["apply-toc", str(tmp_path / "nope.pdf"), str(toc)])
        assert result.exit_code == 1
        assert "error:" in result.output.lower()

    def test_optimize_missing_pdf(self, tmp_path: Path):
        result = runner.invoke(app, ["optimize", str(tmp_path / "nope.pdf")])
        assert result.exit_code == 1
        assert "error:" in result.output.lower()

    def test_dl_cover_all_sources_fail(self, tmp_path: Path):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        with patch("calpdf.dlcover.requests.get", return_value=mock_resp):
            result = runner.invoke(
                app, ["dl-cover", "BADID", "-o", str(tmp_path / "c.jpg")]
            )
        assert result.exit_code == 1
        assert "error:" in result.output.lower()

    def test_export_toc_missing_pdf(self, tmp_path: Path):
        result = runner.invoke(app, ["export-toc", str(tmp_path / "nope.pdf")])
        assert result.exit_code == 1
        assert "error:" in result.output.lower()


# ---------------------------------------------------------------------------
# set-cover validates PDF before downloading
# ---------------------------------------------------------------------------


class TestSetCoverEarlyValidation:
    """set-cover must fail before attempting any download if the PDF is missing."""

    def test_missing_pdf_fails_without_download(self, tmp_path: Path):
        with patch("calpdf.dlcover.requests.get") as mock_get:
            result = runner.invoke(
                app,
                [
                    "set-cover",
                    str(tmp_path / "nonexistent.pdf"),
                    "B08X92NRKV",
                ],
            )
            assert result.exit_code == 1
            assert "error:" in result.output.lower()
            mock_get.assert_not_called()

    def test_missing_pdf_with_output_fails_without_download(self, tmp_path: Path):
        with patch("calpdf.dlcover.requests.get") as mock_get:
            result = runner.invoke(
                app,
                [
                    "set-cover",
                    str(tmp_path / "nonexistent.pdf"),
                    "B08X92NRKV",
                    "-o",
                    str(tmp_path / "out.pdf"),
                ],
            )
            assert result.exit_code == 1
            mock_get.assert_not_called()


# ---------------------------------------------------------------------------
# In-place detection consistency
# ---------------------------------------------------------------------------


class TestInPlaceConsistency:
    """--output pointing to the same file as input should behave like in-place."""

    def test_replace_cover_same_output_as_input(
        self, sample_pdf: Path, sample_jpeg: Path
    ):
        result = runner.invoke(
            app,
            [
                "replace-cover",
                str(sample_pdf),
                str(sample_jpeg),
                "-o",
                str(sample_pdf),
            ],
        )
        assert result.exit_code == 0
        bak = sample_pdf.with_name(sample_pdf.name + ".bak")
        assert bak.exists()

    def test_apply_toc_same_output_as_input(self, sample_pdf: Path, tmp_path: Path):
        toc = _make_toc_file(tmp_path / "toc.json")
        result = runner.invoke(
            app,
            [
                "apply-toc",
                str(sample_pdf),
                str(toc),
                "-o",
                str(sample_pdf),
            ],
        )
        assert result.exit_code == 0
        bak = sample_pdf.with_name(sample_pdf.name + ".bak")
        assert bak.exists()


# ---------------------------------------------------------------------------
# Success message consistency
# ---------------------------------------------------------------------------


class TestSuccessMessageConsistency:
    """All mutating commands must print 'Success: ...' on completion."""

    def test_replace_cover_success_prefix(
        self, sample_pdf: Path, sample_jpeg: Path, tmp_path: Path
    ):
        out = tmp_path / "out.pdf"
        result = runner.invoke(
            app,
            ["replace-cover", str(sample_pdf), str(sample_jpeg), "-o", str(out)],
        )
        assert result.exit_code == 0
        assert any(
            line.lower().startswith("success:") for line in result.output.splitlines()
        )

    def test_apply_toc_success_prefix(self, sample_pdf: Path, tmp_path: Path):
        toc = _make_toc_file(tmp_path / "toc.json")
        out = tmp_path / "out.pdf"
        result = runner.invoke(
            app, ["apply-toc", str(sample_pdf), str(toc), "-o", str(out)]
        )
        assert result.exit_code == 0
        assert any(
            line.lower().startswith("success:") for line in result.output.splitlines()
        )

    def test_optimize_success_prefix(self, sample_pdf: Path, tmp_path: Path):
        out = tmp_path / "out.pdf"
        mock_result = MagicMock()
        mock_result.returncode = 0
        with (
            patch("calpdf.optimize.shutil.which", return_value="/usr/bin/qpdf"),
            patch("calpdf.optimize.subprocess.run", return_value=mock_result),
        ):
            shutil.copy2(sample_pdf, out)
            result = runner.invoke(app, ["optimize", str(sample_pdf), "-o", str(out)])
        assert result.exit_code == 0
        assert any(
            line.lower().startswith("success:") for line in result.output.splitlines()
        )
