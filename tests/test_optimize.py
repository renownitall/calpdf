from pathlib import Path
from unittest.mock import patch, MagicMock

import shutil

import pytest
from typer.testing import CliRunner

from calpdf.cli import app

runner = CliRunner()


class TestOptimizeCLI:
    def test_qpdf_not_found(self, sample_pdf: Path, tmp_path: Path):
        with patch("calpdf.optimize.shutil.which", return_value=None):
            result = runner.invoke(
                app,
                ["optimize", str(sample_pdf), "-o", str(tmp_path / "out.pdf")],
            )
            assert result.exit_code == 1
            # Typer's CliRunner mixes stderr into result.output
            assert "qpdf" in result.output.lower()

    def test_success(self, sample_pdf: Path, tmp_path: Path):
        out = tmp_path / "out.pdf"
        mock_result = MagicMock()
        mock_result.returncode = 0

        with (
            patch("calpdf.optimize.shutil.which", return_value="/usr/bin/qpdf"),
            patch("calpdf.optimize.subprocess.run", return_value=mock_result),
        ):
            # The real qpdf would create the output; we fake it
            shutil.copy2(sample_pdf, out)

            result = runner.invoke(app, ["optimize", str(sample_pdf), "-o", str(out)])
            assert result.exit_code == 0

    def test_qpdf_failure_without_force(self, sample_pdf: Path, tmp_path: Path):
        out = tmp_path / "out.pdf"
        mock_result = MagicMock()
        mock_result.returncode = 2
        mock_result.stderr = "something broke"

        with (
            patch("calpdf.optimize.shutil.which", return_value="/usr/bin/qpdf"),
            patch("calpdf.optimize.subprocess.run", return_value=mock_result),
        ):
            result = runner.invoke(app, ["optimize", str(sample_pdf), "-o", str(out)])
            assert result.exit_code == 1

    def test_missing_input(self, tmp_path: Path):
        result = runner.invoke(
            app,
            ["optimize", str(tmp_path / "nope.pdf")],
        )
        assert result.exit_code == 1
