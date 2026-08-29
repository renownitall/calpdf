"""Tests for calpdf.dlcover."""

from pathlib import Path
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner

import pytest
import requests

from calpdf.cli import app
from calpdf.common import AppError
from calpdf.dlcover import (
    URL_CHAIN,
    _detected_format,
    _looks_like_image,
    download_cover,
)

runner = CliRunner()


def _response(status_code: int = 200, content: bytes = b"") -> MagicMock:
    """Build a minimal fake requests response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = content
    return resp


def test_command_names_are_unique() -> None:
    """Each CLI command is registered exactly once."""
    names = [command.name for command in app.registered_commands]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    assert not duplicates, f"duplicate command registrations: {duplicates}"


class TestImageSignatureHelpers:
    def test_looks_like_jpeg(self, tiny_jpeg_bytes: bytes):
        assert _looks_like_image(tiny_jpeg_bytes) is True

    def test_looks_like_png(self):
        assert _looks_like_image(b"\x89PNG\r\n\x1a\nrest") is True

    def test_rejects_html(self):
        assert _looks_like_image(b"<html><body>not an image</body></html>") is False

    def test_rejects_empty(self):
        assert _looks_like_image(b"") is False

    def test_detected_format_jpeg(self, tiny_jpeg_bytes: bytes):
        assert _detected_format(tiny_jpeg_bytes) == "JPEG"

    def test_detected_format_png(self):
        assert _detected_format(b"\x89PNG rest") == "PNG"

    def test_detected_format_unknown(self):
        assert _detected_format(b"something else") is None


class TestDownloadCover:
    def test_first_source_success_writes_file_and_stops(
        self, tmp_path: Path, tiny_jpeg_bytes: bytes
    ):
        target = tmp_path / "cover.jpg"
        with patch(
            "calpdf.dlcover.requests.get",
            return_value=_response(200, tiny_jpeg_bytes),
        ) as mock_get:
            result = download_cover("B08X92NRKV", target)
        assert result == target
        assert target.read_bytes() == tiny_jpeg_bytes
        assert mock_get.call_count == 1

    def test_falls_back_after_404(self, tmp_path: Path, tiny_jpeg_bytes: bytes):
        target = tmp_path / "cover.jpg"
        with patch(
            "calpdf.dlcover.requests.get",
            side_effect=[_response(404), _response(200, tiny_jpeg_bytes)],
        ) as mock_get:
            result = download_cover("B08X92NRKV", target)
        assert result == target
        assert target.exists()
        assert mock_get.call_count == 2

    def test_skips_response_below_min_size(
        self, tmp_path: Path, tiny_jpeg_bytes: bytes
    ):
        target = tmp_path / "cover.jpg"
        small = b"\xff\xd8\xff" + b"x" * 10  # valid signature, well under MIN_SIZE
        with patch(
            "calpdf.dlcover.requests.get",
            side_effect=[_response(200, small), _response(200, tiny_jpeg_bytes)],
        ) as mock_get:
            result = download_cover("B08X92NRKV", target)
        assert result == target
        assert mock_get.call_count == 2

    def test_skips_non_image_payload(self, tmp_path: Path, tiny_jpeg_bytes: bytes):
        target = tmp_path / "cover.jpg"
        # Repeated so the payload comfortably exceeds MIN_SIZE
        html = b"<html><body>not a cover</body></html>" * 50
        with patch(
            "calpdf.dlcover.requests.get",
            side_effect=[_response(200, html), _response(200, tiny_jpeg_bytes)],
        ) as mock_get:
            result = download_cover("B08X92NRKV", target)
        assert result == target
        assert mock_get.call_count == 2

    def test_skips_request_exception(self, tmp_path: Path, tiny_jpeg_bytes: bytes):
        target = tmp_path / "cover.jpg"
        with patch(
            "calpdf.dlcover.requests.get",
            side_effect=[
                requests.RequestException("connection reset"),
                _response(200, tiny_jpeg_bytes),
            ],
        ) as mock_get:
            result = download_cover("B08X92NRKV", target)
        assert result == target
        assert mock_get.call_count == 2

    def test_all_sources_fail_raises(self, tmp_path: Path):
        target = tmp_path / "cover.jpg"
        with (
            patch(
                "calpdf.dlcover.requests.get",
                return_value=_response(404),
            ) as mock_get,
            pytest.raises(AppError, match="Failed to find a valid cover"),
        ):
            download_cover("BADID", target)
        assert mock_get.call_count == len(URL_CHAIN)
        assert not target.exists()


class TestBookIdValidation:
    def test_dl_cover_rejects_path_traversal(self, tmp_path: Path):
        with patch("calpdf.dlcover.requests.get") as mock_get:
            result = runner.invoke(
                app, ["dl-cover", "../evil", "-o", str(tmp_path / "c.jpg")]
            )
        assert result.exit_code == 1
        assert "invalid book_id" in result.output.lower()
        mock_get.assert_not_called()

    def test_dl_cover_accepts_isbn_with_dashes(
        self, tmp_path: Path, tiny_jpeg_bytes: bytes
    ):
        with patch(
            "calpdf.dlcover.requests.get",
            return_value=_response(200, tiny_jpeg_bytes),
        ):
            result = runner.invoke(
                app,
                ["dl-cover", "978-0-14-032872-1", "-o", str(tmp_path / "c.jpg")],
            )
        assert result.exit_code == 0, result.output

    def test_set_cover_rejects_invalid_id(self, sample_pdf: Path):
        with patch("calpdf.dlcover.requests.get") as mock_get:
            result = runner.invoke(app, ["set-cover", str(sample_pdf), "../../evil"])
        assert result.exit_code == 1
        mock_get.assert_not_called()
