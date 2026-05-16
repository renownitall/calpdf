import io
import os
from pathlib import Path

import pikepdf
import pytest
from PIL import Image

from calpdf import output as _output_module


@pytest.fixture(autouse=True)
def _reset_output():
    """Reset the output module to defaults before each test.

    Forces no-color so assertions don't have to deal with ANSI codes.
    Also resets quiet mode in case a previous test changed it.
    """
    _output_module.configure(quiet=False, no_color=True)
    yield
    _output_module.configure(quiet=False, no_color=True)


@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    pdf_path = tmp_path / "sample.pdf"
    pdf = pikepdf.Pdf.new()
    for i in range(3):
        page = pdf.add_blank_page(page_size=(612, 792))
        content = f"BT /F1 12 Tf 100 700 Td (Page {i + 1}) Tj ET"
        page.obj["/Contents"] = pdf.make_stream(content.encode())
    pdf.save(pdf_path)
    pdf.close()
    return pdf_path


@pytest.fixture
def sample_pdf_with_toc(tmp_path: Path) -> Path:
    pdf_path = tmp_path / "with_toc.pdf"
    pdf = pikepdf.Pdf.new()
    for i in range(5):
        pdf.add_blank_page(page_size=(612, 792))

    with pdf.open_outline() as outline:
        outline.root.append(
            pikepdf.OutlineItem(
                "Chapter 1",
                pikepdf.Array([pdf.pages[0].obj, pikepdf.Name("/Fit")]),
            )
        )
        outline.root.append(
            pikepdf.OutlineItem(
                "Chapter 2",
                pikepdf.Array([pdf.pages[2].obj, pikepdf.Name("/Fit")]),
            )
        )
        child = pikepdf.OutlineItem(
            "Section 2.1",
            pikepdf.Array([pdf.pages[3].obj, pikepdf.Name("/Fit")]),
        )
        outline.root[1].children.append(child)

    pdf.save(pdf_path)
    pdf.close()
    return pdf_path


@pytest.fixture
def sample_jpeg(tmp_path: Path) -> Path:
    img_path = tmp_path / "cover.jpg"
    img = Image.new("RGB", (600, 800), color=(100, 150, 200))
    img.save(img_path, "JPEG", quality=85)
    return img_path


@pytest.fixture
def sample_png(tmp_path: Path) -> Path:
    img_path = tmp_path / "cover.png"
    img = Image.new("RGBA", (600, 800), color=(100, 150, 200, 128))
    img.save(img_path, "PNG")
    return img_path


@pytest.fixture
def tiny_jpeg_bytes() -> bytes:
    """Return raw bytes for a JPEG image that exceeds MIN_SIZE (1024 bytes)."""
    width, height = 64, 64
    random_pixels = os.urandom(width * height * 3)
    img = Image.frombytes("RGB", (width, height), random_pixels)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=95)
    data = buf.getvalue()
    assert len(data) >= 1024, f"Test JPEG is only {len(data)} bytes; bump dimensions"
    return data
