import shutil
from unittest.mock import patch, MagicMock
from pathlib import Path
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
            assert any(
                line.lower().startswith("success:")
                for line in result.output.splitlines()
            )

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
        assert "error:" in result.output.lower()

    def test_force_fails_when_qpdf_produces_no_output(
        self, sample_pdf: Path, tmp_path: Path
    ):
        out = tmp_path / "out.pdf"
        mock_result = MagicMock()
        mock_result.returncode = 2
        mock_result.stderr = "something broke"
        with (
            patch("calpdf.optimize.shutil.which", return_value="/usr/bin/qpdf"),
            patch("calpdf.optimize.subprocess.run", return_value=mock_result),
        ):
            result = runner.invoke(
                app,
                ["optimize", str(sample_pdf), "-o", str(out), "--force"],
            )
        assert result.exit_code == 1
        assert "no output" in result.output.lower()

    def test_force_succeeds_when_output_file_exists(
        self, sample_pdf: Path, tmp_path: Path
    ):
        out = tmp_path / "out.pdf"
        mock_result = MagicMock()
        mock_result.returncode = 2
        mock_result.stderr = "something broke"
        with (
            patch("calpdf.optimize.shutil.which", return_value="/usr/bin/qpdf"),
            patch("calpdf.optimize.subprocess.run", return_value=mock_result),
        ):
            # Simulate qpdf having written an output file before failing
            shutil.copy2(sample_pdf, out)
            result = runner.invoke(
                app,
                ["optimize", str(sample_pdf), "-o", str(out), "--force"],
            )
        assert result.exit_code == 0
        assert "warning" in result.output.lower()

    def test_qpdf_exit_3_warns_but_succeeds(self, sample_pdf: Path, tmp_path: Path):
        out = tmp_path / "out.pdf"
        mock_result = MagicMock()
        mock_result.returncode = 3
        mock_result.stderr = ""
        with (
            patch("calpdf.optimize.shutil.which", return_value="/usr/bin/qpdf"),
            patch("calpdf.optimize.subprocess.run", return_value=mock_result),
        ):
            shutil.copy2(sample_pdf, out)
            result = runner.invoke(app, ["optimize", str(sample_pdf), "-o", str(out)])
        assert result.exit_code == 0
        assert "warnings" in result.output.lower()

    def test_keep_metadata_drops_strip_flags(
        self, sample_pdf: Path, tmp_path: Path
    ):
        out = tmp_path / "out.pdf"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        with (
            patch("calpdf.optimize.shutil.which", return_value="/usr/bin/qpdf"),
            patch(
                "calpdf.optimize.subprocess.run", return_value=mock_result
            ) as mock_run,
        ):
            shutil.copy2(sample_pdf, out)
            result = runner.invoke(
                app,
                ["optimize", str(sample_pdf), "-o", str(out), "--keep-metadata"],
            )
        assert result.exit_code == 0
        cmd = mock_run.call_args[0][0]
        assert "--remove-info" not in cmd
        assert "--remove-metadata" not in cmd

    def test_strip_color_profiles_runs_gs_then_qpdf(
        self, sample_pdf: Path, tmp_path: Path
    ):
        out = tmp_path / "out.pdf"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        with (
            patch("calpdf.optimize.shutil.which", return_value="/usr/bin/mockbin"),
            patch(
                "calpdf.optimize.subprocess.run", return_value=mock_result
            ) as mock_run,
        ):
            shutil.copy2(sample_pdf, out)  # fake qpdf writing the output file
            result = runner.invoke(
                app,
                [
                    "optimize",
                    str(sample_pdf),
                    "-o",
                    str(out),
                    "--strip-color-profiles",
                ],
            )
        assert result.exit_code == 0, result.stdout
        assert mock_run.call_count == 2
        gs_cmd = mock_run.call_args_list[0][0][0]
        qpdf_cmd = mock_run.call_args_list[1][0][0]
        assert any("pdfwrite" in str(arg) for arg in gs_cmd)
        assert "--linearize" in qpdf_cmd
