import json
from pathlib import Path

import pikepdf
import pytest
from typer.testing import CliRunner

from calpdf.cli import app
from calpdf.toc import extract_outline, validate_toc, build_outline_items

runner = CliRunner()


class TestValidateToc:
    def test_valid(self):
        data = [
            {"title": "Ch 1", "pageNumber": 1, "children": []},
            {
                "title": "Ch 2",
                "pageNumber": 3,
                "children": [{"title": "Sec 2.1", "pageNumber": 4, "children": []}],
            },
        ]
        assert validate_toc(data, total_pages=10) == []

    def test_missing_title(self):
        data = [{"pageNumber": 1, "children": []}]
        errors = validate_toc(data, total_pages=5)
        assert any("title" in e for e in errors)

    def test_empty_title(self):
        data = [{"title": "  ", "pageNumber": 1, "children": []}]
        errors = validate_toc(data, total_pages=5)
        assert any("empty" in e for e in errors)

    def test_missing_page_number(self):
        data = [{"title": "Ch", "children": []}]
        errors = validate_toc(data, total_pages=5)
        assert any("pageNumber" in e for e in errors)

    def test_page_number_zero(self):
        data = [{"title": "Ch", "pageNumber": 0, "children": []}]
        errors = validate_toc(data, total_pages=5)
        assert any(">= 1" in e for e in errors)

    def test_page_number_exceeds_total(self):
        data = [{"title": "Ch", "pageNumber": 99, "children": []}]
        errors = validate_toc(data, total_pages=5)
        assert any("exceeds" in e for e in errors)

    def test_missing_children(self):
        data = [{"title": "Ch", "pageNumber": 1}]
        errors = validate_toc(data, total_pages=5)
        assert any("children" in e for e in errors)

    def test_not_a_list(self):
        errors = validate_toc({"title": "oops"}, total_pages=5)
        assert any("list" in e for e in errors)

    def test_page_number_wrong_type(self):
        data = [{"title": "Ch", "pageNumber": "one", "children": []}]
        errors = validate_toc(data, total_pages=5)
        assert any("integer" in e for e in errors)


class TestExtractOutline:
    def test_roundtrip(self, sample_pdf_with_toc: Path):
        with pikepdf.open(sample_pdf_with_toc) as pdf:
            page_map = {page.obj.objgen: i for i, page in enumerate(pdf.pages)}
            with pdf.open_outline() as outline:
                toc = extract_outline(outline.root, pdf, page_map)

        assert len(toc) == 2
        assert toc[0]["title"] == "Chapter 1"
        assert toc[0]["pageNumber"] == 1
        assert toc[1]["title"] == "Chapter 2"
        assert toc[1]["pageNumber"] == 3
        assert len(toc[1]["children"]) == 1
        assert toc[1]["children"][0]["title"] == "Section 2.1"
        assert toc[1]["children"][0]["pageNumber"] == 4


class TestBuildOutlineItems:
    def test_builds_items(self, sample_pdf: Path):
        entries = [
            {"title": "First", "pageNumber": 1, "children": []},
            {
                "title": "Second",
                "pageNumber": 2,
                "children": [{"title": "Sub", "pageNumber": 3, "children": []}],
            },
        ]
        with pikepdf.open(sample_pdf) as pdf:
            items = build_outline_items(pdf, entries)
            assert len(items) == 2
            assert items[0].title == "First"
            assert items[1].title == "Second"
            assert len(items[1].children) == 1
            assert items[1].children[0].title == "Sub"


class TestExportTocCLI:
    def test_export_stdout(self, sample_pdf_with_toc: Path):
        result = runner.invoke(app, ["export-toc", str(sample_pdf_with_toc)])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data) == 2

    def test_export_to_file(self, sample_pdf_with_toc: Path, tmp_path: Path):
        out = tmp_path / "toc.json"
        result = runner.invoke(
            app, ["export-toc", str(sample_pdf_with_toc), "-o", str(out)]
        )
        assert result.exit_code == 0
        data = json.loads(out.read_text())
        assert len(data) == 2

    def test_export_missing_pdf(self, tmp_path: Path):
        result = runner.invoke(app, ["export-toc", str(tmp_path / "nope.pdf")])
        assert result.exit_code == 1

    def test_export_empty_toc(self, sample_pdf: Path):
        result = runner.invoke(app, ["export-toc", str(sample_pdf)])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data == []


class TestApplyTocCLI:
    def test_apply_in_place(self, sample_pdf: Path, tmp_path: Path):
        toc_data = [
            {"title": "Intro", "pageNumber": 1, "children": []},
            {"title": "Body", "pageNumber": 2, "children": []},
        ]
        toc_file = tmp_path / "toc.json"
        toc_file.write_text(json.dumps(toc_data))

        result = runner.invoke(app, ["apply-toc", str(sample_pdf), str(toc_file)])
        assert result.exit_code == 0
        assert "Success" in result.stdout

        # Verify the ToC was applied
        with pikepdf.open(sample_pdf) as pdf:
            page_map = {page.obj.objgen: i for i, page in enumerate(pdf.pages)}
            with pdf.open_outline() as outline:
                toc = extract_outline(outline.root, pdf, page_map)
            assert len(toc) == 2
            assert toc[0]["title"] == "Intro"

    def test_apply_to_output(self, sample_pdf: Path, tmp_path: Path):
        toc_data = [{"title": "Only", "pageNumber": 1, "children": []}]
        toc_file = tmp_path / "toc.json"
        toc_file.write_text(json.dumps(toc_data))
        out = tmp_path / "output.pdf"

        result = runner.invoke(
            app, ["apply-toc", str(sample_pdf), str(toc_file), "-o", str(out)]
        )
        assert result.exit_code == 0
        assert out.exists()

    def test_apply_invalid_json(self, sample_pdf: Path, tmp_path: Path):
        toc_file = tmp_path / "bad.json"
        toc_file.write_text("{not valid json")
        result = runner.invoke(app, ["apply-toc", str(sample_pdf), str(toc_file)])
        assert result.exit_code == 1

    def test_apply_invalid_toc_structure(self, sample_pdf: Path, tmp_path: Path):
        toc_data = [{"title": "Ch", "pageNumber": 999, "children": []}]
        toc_file = tmp_path / "toc.json"
        toc_file.write_text(json.dumps(toc_data))
        result = runner.invoke(app, ["apply-toc", str(sample_pdf), str(toc_file)])
        assert result.exit_code == 1

    def test_full_roundtrip(self, sample_pdf_with_toc: Path, tmp_path: Path):
        """Export ToC, apply it to a fresh PDF, re-export, and compare."""
        # Export original
        result = runner.invoke(app, ["export-toc", str(sample_pdf_with_toc)])
        assert result.exit_code == 0
        original_toc = json.loads(result.stdout)

        # Create a fresh PDF with same page count
        fresh = tmp_path / "fresh.pdf"
        with pikepdf.open(sample_pdf_with_toc) as pdf:
            fresh_pdf = pikepdf.Pdf.new()
            for _ in range(len(pdf.pages)):
                fresh_pdf.add_blank_page(page_size=(612, 792))
            fresh_pdf.save(fresh)
            fresh_pdf.close()

        # Apply original ToC
        toc_file = tmp_path / "toc.json"
        toc_file.write_text(json.dumps(original_toc))
        result = runner.invoke(app, ["apply-toc", str(fresh), str(toc_file)])
        assert result.exit_code == 0

        # Re-export and compare
        result = runner.invoke(app, ["export-toc", str(fresh)])
        assert result.exit_code == 0
        roundtrip_toc = json.loads(result.stdout)

        assert len(roundtrip_toc) == len(original_toc)
        for orig, rt in zip(original_toc, roundtrip_toc):
            assert orig["title"] == rt["title"]
            assert orig["pageNumber"] == rt["pageNumber"]
            assert len(orig["children"]) == len(rt["children"])
