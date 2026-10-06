from __future__ import annotations

import builtins
import logging
from pathlib import Path

import fitz
import pytest
from docx import Document

from app.core.exceptions import ConversionError
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
    assert docx_path.stat().st_size > 0
    assert Document(docx_path).paragraphs
    assert result.status.name == "COMPLETED"


def test_pdf2docx_import_error_includes_cause_and_logs_traceback(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    original_import = builtins.__import__

    def fail_pdf2docx_import(
        name: str,
        globals: object = None,
        locals: object = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object:
        if name == "pdf2docx":
            raise ImportError("numpy loader failure")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fail_pdf2docx_import)
    caplog.set_level(logging.ERROR)

    with pytest.raises(ConversionError, match="ImportError: numpy loader failure"):
        ConversionService()._convert_pdf_to_docx(
            "unused.pdf",
            "unused.docx",
            (1,),
            total_pages=1,
            multiprocessing_enabled=False,
        )

    error_record = next(record for record in caplog.records if "pdf2docx" in record.message)
    assert error_record.exc_info is not None
    assert error_record.exc_info[0] is ImportError


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
