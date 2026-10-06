from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from app.core.exceptions import PDFAnalysisError, PDFEncryptedError, PDFValidationError
from app.models import PDFInfo
from app.services.pdf_analyzer import PDFAnalyzer


def _create_pdf(path: Path, *, include_text: bool = True) -> None:
    document = fitz.open()
    page = document.new_page()
    if include_text:
        page.insert_text((72, 72), "Este documento contiene suficiente texto")
    document.save(path)
    document.close()


def test_pdf_analyzer_reads_digital_document_and_classifies_it(tmp_path: Path) -> None:
    path = tmp_path / "digital.pdf"
    _create_pdf(path)

    info = PDFAnalyzer().analyze(str(path))

    assert info.page_count == 1
    assert info.has_text
    assert not info.requires_ocr
    assert PDFAnalyzer().classify(info) == "digital"


def test_pdf_analyzer_rejects_missing_invalid_and_corrupt_pdfs(tmp_path: Path) -> None:
    analyzer = PDFAnalyzer()
    with pytest.raises(PDFValidationError):
        analyzer.analyze(tmp_path / "missing.pdf")

    invalid = tmp_path / "invalid.pdf"
    invalid.write_bytes(b"not a pdf")
    with pytest.raises(PDFValidationError):
        analyzer.analyze(invalid)

    corrupt = tmp_path / "corrupt.pdf"
    corrupt.write_bytes(b"%PDF-1.7\ninvalid")
    with pytest.raises(PDFAnalysisError):
        analyzer.analyze(corrupt)


def test_pdf_analyzer_detects_encryption(tmp_path: Path) -> None:
    path = tmp_path / "encrypted.pdf"
    document = fitz.open()
    document.new_page()
    document.save(
        path,
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw="owner",
        user_pw="user",
    )
    document.close()

    with pytest.raises(PDFEncryptedError):
        PDFAnalyzer().analyze(path)


def test_pdf_analyzer_classification_and_geometry_helpers() -> None:
    analyzer = PDFAnalyzer()
    assert analyzer.classify(
        PDFInfo(
            path=Path("empty.pdf"),
            page_count=0,
            file_size=0,
            has_text=False,
            has_images=False,
            is_encrypted=False,
            requires_ocr=False,
            pages=(),
        )
    ) == "desconocido"
    assert PDFAnalyzer._rectangle_area((0, 0, 10, 10)) == 100
    assert PDFAnalyzer._rectangle_area((10, 10, 0, 0)) == 0
    assert PDFAnalyzer._rectangle_area(None) == 0
    assert analyzer.minimum_text_length == 20
    assert analyzer.minimum_image_coverage == 0.45
    with pytest.raises(ValueError):
        PDFAnalyzer(minimum_image_coverage=0)
