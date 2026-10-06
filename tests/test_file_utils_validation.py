from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from docx import Document

from app.core.exceptions import OutputValidationError, PDFValidationError
from app.utils.file_utils import (
    atomic_write_json,
    atomic_write_text,
    ensure_directory,
    format_file_size,
    has_pdf_signature,
    path_display_name,
    read_file_prefix,
    safe_unlink,
)
from app.utils.validation import validate_docx_file, validate_input_pdf, validate_output_path


def test_file_helpers_format_and_read_paths(tmp_path: Path) -> None:
    path = tmp_path / "document.pdf"
    path.write_bytes(b"%PDF-1.7\nbody")
    assert path_display_name(path) == "document.pdf"
    assert read_file_prefix(path, 5) == b"%PDF-"
    assert has_pdf_signature(path)
    assert format_file_size(0) == "0 B"
    assert format_file_size(1_024) == "1.0 KB"
    assert safe_unlink(path)
    assert not safe_unlink(path)
    with pytest.raises(ValueError):
        format_file_size(True)
    with pytest.raises(ValueError):
        read_file_prefix(path, 0)


def test_atomic_writes_and_directory_creation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "nested" / "settings.json"
    atomic_write_json(destination, {"theme": "dark"})
    assert json.loads(destination.read_text(encoding="utf-8")) == {"theme": "dark"}
    assert ensure_directory(destination.parent) == destination.parent

    text_path = tmp_path / "settings.txt"
    monkeypatch.delattr(os, "fchmod")
    atomic_write_text(text_path, "safe")
    assert text_path.read_text(encoding="utf-8") == "safe"


def test_input_pdf_validation_reports_invalid_inputs(tmp_path: Path) -> None:
    valid_pdf = tmp_path / "valid.pdf"
    valid_pdf.write_bytes(b"%PDF-1.7\n")
    assert validate_input_pdf(valid_pdf) == valid_pdf

    with pytest.raises(PDFValidationError):
        validate_input_pdf(tmp_path / "missing.pdf")
    empty_pdf = tmp_path / "empty.pdf"
    empty_pdf.touch()
    with pytest.raises(PDFValidationError):
        validate_input_pdf(empty_pdf)
    invalid_pdf = tmp_path / "invalid.pdf"
    invalid_pdf.write_bytes(b"not a pdf")
    with pytest.raises(PDFValidationError):
        validate_input_pdf(invalid_pdf)
    with pytest.raises(PDFValidationError):
        validate_input_pdf(tmp_path)


def test_output_path_validation(tmp_path: Path) -> None:
    output = tmp_path / "result.docx"
    assert validate_output_path(output) == output
    output.touch()
    with pytest.raises(OutputValidationError):
        validate_output_path(output)
    assert validate_output_path(output, overwrite_confirmed=True) == output
    with pytest.raises(OutputValidationError):
        validate_output_path(tmp_path / "result.txt")
    with pytest.raises(OutputValidationError):
        validate_output_path(tmp_path / "missing" / "result.docx")


def test_docx_file_validation_checks_structure(tmp_path: Path) -> None:
    valid_docx = tmp_path / "valid.docx"
    document = Document()
    document.add_paragraph("valid")
    document.save(valid_docx)
    assert validate_docx_file(valid_docx) == valid_docx

    with pytest.raises(ValueError):
        validate_docx_file(valid_docx, min_size=0)
    with pytest.raises(OutputValidationError):
        validate_docx_file(tmp_path / "missing.docx")
    invalid_docx = tmp_path / "invalid.docx"
    invalid_docx.write_text("not a document", encoding="utf-8")
    with pytest.raises(OutputValidationError):
        validate_docx_file(invalid_docx)
