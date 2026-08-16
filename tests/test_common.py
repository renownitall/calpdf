from pathlib import Path

import pytest

from calpdf.common import (
    AppError,
    detect_swap,
    ensure_backup,
    message,
    normalize_paths,
    same_path,
    validate_input_file,
    validate_output_dir,
)


class TestMessage:
    def test_with_text(self):
        assert message(ValueError("boom")) == "boom"

    def test_empty_falls_back_to_class_name(self):
        assert message(ValueError()) == "ValueError"

    def test_whitespace_only_falls_back(self):
        assert message(ValueError("   ")) == "ValueError"


class TestSamePath:
    def test_same(self, tmp_path: Path):
        p = tmp_path / "a.pdf"
        assert same_path(p, p) is True

    def test_different(self, tmp_path: Path):
        assert same_path(tmp_path / "a.pdf", tmp_path / "b.pdf") is False

    def test_resolves_relative(self, tmp_path: Path):
        a = tmp_path / "sub" / ".." / "a.pdf"
        b = tmp_path / "a.pdf"
        assert same_path(a, b) is True


class TestNormalizePaths:
    def test_normal_file(self):
        out, bak = normalize_paths(Path("book.pdf"))
        assert out == Path("book.pdf")
        assert bak == Path("book.pdf.bak")

    def test_bak_file(self):
        out, bak = normalize_paths(Path("book.pdf.bak"))
        assert out == Path("book.pdf")
        assert bak == Path("book.pdf.bak")


class TestEnsureBackup:
    def test_backup_already_exists(self, tmp_path: Path):
        bak = tmp_path / "f.pdf.bak"
        bak.write_text("original")
        result = ensure_backup(tmp_path / "f.pdf", bak)
        assert result == bak

    def test_creates_backup_from_output(self, tmp_path: Path):
        out = tmp_path / "f.pdf"
        bak = tmp_path / "f.pdf.bak"
        out.write_text("data")
        result = ensure_backup(out, bak)
        assert result == bak
        assert bak.read_text() == "data"

    def test_neither_exists(self, tmp_path: Path):
        with pytest.raises(AppError, match="Neither"):
            ensure_backup(tmp_path / "x.pdf", tmp_path / "x.pdf.bak")


class TestValidateInputFile:
    def test_missing(self, tmp_path: Path):
        with pytest.raises(AppError, match="not found"):
            validate_input_file(tmp_path / "nope.pdf")

    def test_exists(self, tmp_path: Path):
        f = tmp_path / "yes.pdf"
        f.write_text("ok")
        validate_input_file(f)  # should not raise


class TestValidateOutputDir:
    def test_parent_missing(self, tmp_path: Path):
        with pytest.raises(AppError, match="does not exist"):
            validate_output_dir(tmp_path / "no_such_dir" / "out.pdf")

    def test_path_is_directory(self, tmp_path: Path):
        d = tmp_path / "somedir"
        d.mkdir()
        with pytest.raises(AppError, match="is a directory"):
            validate_output_dir(d)

    def test_valid(self, tmp_path: Path):
        validate_output_dir(tmp_path / "out.pdf")  # should not raise


class TestDetectSwap:
    def test_swapped(self):
        result = detect_swap(Path("cover.jpg"), Path("book.pdf"))
        assert result is not None
        assert "swapped" in result.lower()

    def test_correct_order(self):
        assert detect_swap(Path("book.pdf"), Path("cover.jpg")) is None

    def test_both_pdf(self):
        assert detect_swap(Path("a.pdf"), Path("b.pdf")) is None
