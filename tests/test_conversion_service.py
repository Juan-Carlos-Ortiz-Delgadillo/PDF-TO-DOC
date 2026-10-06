from __future__ import annotations

from pathlib import Path

import fitz
import pytest
from docx import Document

from app.models import ConversionConfig, PageSelection
from app.services import ConversionService


def _create_pdf(path: Path, page_count: int = 1) -> None:
    document = fitz.open()
    for page_number in range(1, page_count + 1):
        page = document.new_page()
        page.insert_text((72, 72), f"PAGE-{page_number}")
    document.save(path)
    document.close()


def _convert(
    pdf_path: Path,
    docx_path: Path,
    selection: PageSelection,
) -> list[str]:
    config = ConversionConfig(
        input_path=pdf_path,
        output_path=docx_path,
        page_selection=selection,
        use_ocr=False,
        ocr_language="spa",
        multiprocessing_enabled=False,
        overwrite_confirmed=True,
    )

    ConversionService().convert(config)
    document = Document(docx_path)
    return [paragraph.text for paragraph in document.paragraphs if paragraph.text]


def test_conversion_service_converts_simple_pdf(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    docx_path = tmp_path / "result.docx"
    _create_pdf(pdf_path)

    config = ConversionConfig(
        input_path=pdf_path,
        output_path=docx_path,
        page_selection=PageSelection.all(),
        use_ocr=False,
        ocr_language="spa",
        multiprocessing_enabled=False,
        overwrite_confirmed=True,
    )

    result = ConversionService().convert(config)
    assert result.output_path == docx_path
    assert docx_path.exists()
    assert result.status.name == "COMPLETED"


@pytest.mark.parametrize(
    ("selection", "expected"),
    [
        (PageSelection.range(1, 2), ["PAGE-1", "PAGE-2"]),
        (PageSelection.specific([1, 3]), ["PAGE-1", "PAGE-3"]),
        (PageSelection.specific([4]), ["PAGE-4"]),
    ],
)
def test_conversion_service_converts_exact_selected_pages(
    tmp_path: Path,
    selection: PageSelection,
    expected: list[str],
) -> None:
    pdf_path = tmp_path / "multi-page.pdf"
    docx_path = tmp_path / "selected.docx"
    _create_pdf(pdf_path, page_count=4)

    actual = _convert(pdf_path, docx_path, selection)

    assert actual == expected
