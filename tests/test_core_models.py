from __future__ import annotations

from pathlib import Path

import pytest

from app.core.exceptions import PageSelectionError, TaskStateTransitionError
from app.models import (
    ConversionConfig,
    ConversionResult,
    PageSelection,
    PDFInfo,
    PDFPageInfo,
    TaskState,
    can_transition,
    ensure_transition,
    is_terminal_state,
    parse_page_selection,
)
from app.models.task_event import TaskErrorInfo, TaskEvent, TaskEventType


@pytest.mark.parametrize("value", ["all", "*", "todas", "todo"])
def test_page_selection_all_tokens(value: str) -> None:
    selection = parse_page_selection(value, 3)
    assert selection.resolve(3) == (1, 2, 3)
    assert selection.display_value() == "Todas"
    assert selection.is_contiguous(3)


def test_page_selection_range_and_specific_pages() -> None:
    selection = PageSelection.parse(" 2 - 4 ", 5)
    assert selection.resolve(5) == (2, 3, 4)
    assert selection.display_value() == "2-4"
    assert selection.to_zero_based_indices(5) == (1, 2, 3)

    specific = PageSelection.parse("3, 1,2", 5)
    assert specific.pages == (1, 2, 3)
    assert specific.display_value() == "1, 2, 3"
    assert specific.is_contiguous(5)
    assert not PageSelection.specific([1, 3]).is_contiguous(5)


@pytest.mark.parametrize("value", ["", "1-", "1,2-3", "1,,2", "hello"])
def test_page_selection_rejects_malformed_text(value: str) -> None:
    with pytest.raises(PageSelectionError):
        PageSelection.parse(value, 5)


def test_page_selection_rejects_invalid_bounds_and_duplicates() -> None:
    with pytest.raises(PageSelectionError):
        PageSelection.parse("1,1", 5)
    with pytest.raises(PageSelectionError):
        PageSelection.parse("2-1", 5)
    with pytest.raises(PageSelectionError):
        PageSelection.parse("6", 5)
    with pytest.raises(PageSelectionError):
        PageSelection.all().resolve(0)
    with pytest.raises(ValueError):
        PageSelection.specific([True])
    with pytest.raises(ValueError):
        PageSelection.specific(list(range(1, 10_002)))


def test_page_selection_limits_and_constructor_invariants() -> None:
    with pytest.raises(PageSelectionError):
        PageSelection.parse("1" * 1_025, 5)
    with pytest.raises(ValueError):
        PageSelection.range(0, 2)
    with pytest.raises(ValueError):
        PageSelection.range(2, 1)
    with pytest.raises(ValueError):
        PageSelection(kind="unknown")  # type: ignore[arg-type]


def test_conversion_config_validates_options_and_exposes_output_fields() -> None:
    config = ConversionConfig(
        input_path="input.pdf",
        output_path="result.docx",
        page_selection=PageSelection.all(),
        use_ocr=False,
        ocr_language=" spa ",
        multiprocessing_enabled=False,
        overwrite_confirmed=True,
    )
    assert config.output_directory == Path(".")
    assert config.output_filename == "result.docx"
    assert config.ocr_language == "spa"

    with pytest.raises(ValueError):
        ConversionConfig(
            input_path="input.pdf",
            output_path="result.txt",
            page_selection=PageSelection.all(),
            use_ocr=False,
            ocr_language="spa",
            multiprocessing_enabled=False,
            overwrite_confirmed=False,
        )
    with pytest.raises(ValueError):
        ConversionConfig(
            input_path="input.pdf",
            output_path="result.docx",
            page_selection=PageSelection.all(),
            use_ocr=False,
            ocr_language="spa;invalid",
            multiprocessing_enabled=False,
            overwrite_confirmed=False,
        )


def test_conversion_result_terminal_factories_and_validation() -> None:
    completed = ConversionResult.completed(
        input_path=Path("in.pdf"),
        output_path=Path("out.docx"),
        pages_requested=(1,),
        duration_seconds=0,
    )
    assert completed.status is TaskState.COMPLETED

    failed = ConversionResult.failed(
        input_path=Path("in.pdf"),
        pages_requested=(1,),
        duration_seconds=1.5,
        user_message="Falló",
        diagnostic_message="password=secret",
    )
    assert failed.status is TaskState.FAILED
    assert "secret" not in (failed.diagnostic_message or "")
    assert ConversionResult.cancelled(
        input_path=Path("in.pdf"),
        pages_requested=(),
        duration_seconds=0,
    ).status is TaskState.CANCELLED

    with pytest.raises(ValueError):
        ConversionResult(
            input_path=Path("in.pdf"),
            output_path=None,
            status=TaskState.COMPLETED,
            pages_requested=(),
            duration_seconds=0,
        )


def test_pdf_info_classifies_document_and_lists_ocr_pages() -> None:
    digital_page = PDFPageInfo(
        1,
        has_text=True,
        text_length=30,
        has_images=False,
        requires_ocr=False,
    )
    scanned_page = PDFPageInfo(2, has_text=False, text_length=0, has_images=True, requires_ocr=True)
    info = PDFInfo(
        path=Path("document.pdf"),
        page_count=2,
        file_size=128,
        has_text=True,
        has_images=True,
        is_encrypted=False,
        requires_ocr=True,
        pages=(digital_page, scanned_page),
    )
    assert info.document_kind == "mixed"
    assert info.ocr_page_numbers == (2,)

    protected = PDFInfo(
        path=Path("protected.pdf"),
        page_count=1,
        file_size=32,
        has_text=False,
        has_images=False,
        is_encrypted=True,
        requires_ocr=False,
        pages=(),
    )
    assert protected.document_kind == "protected"

    with pytest.raises(ValueError):
        PDFPageInfo(0, has_text=False, text_length=0, has_images=False, requires_ocr=False)
    with pytest.raises(ValueError):
        PDFInfo(
            path=Path("bad.pdf"),
            page_count=2,
            file_size=1,
            has_text=False,
            has_images=False,
            is_encrypted=False,
            requires_ocr=False,
            pages=(digital_page,),
        )


def test_task_state_transitions_and_task_events() -> None:
    assert can_transition(TaskState.IDLE, "analyzing")
    assert ensure_transition(TaskState.IDLE, TaskState.ANALYZING) is TaskState.ANALYZING
    assert is_terminal_state("completed")
    with pytest.raises(TaskStateTransitionError):
        ensure_transition(TaskState.IDLE, TaskState.COMPLETED)

    event = TaskEvent.progress(
        state=TaskState.CONVERTING,
        message="Procesando",
        percentage=50,
        current_page=1,
        total_pages=2,
    )
    assert event.percentage == 50.0
    assert not event.is_indeterminate
    assert TaskEvent(
        event_type=TaskEventType.STATUS,
        state=TaskState.ANALYZING,
        message="Analizando",
    ).is_indeterminate

    error = TaskErrorInfo("Error", diagnostic_message="token=private")
    assert "private" not in (error.diagnostic_message or "")
    with pytest.raises(ValueError):
        TaskEvent.progress(state=TaskState.CONVERTING, message="Progreso", percentage=101)
    with pytest.raises(ValueError):
        TaskEvent(
            event_type=TaskEventType.COMPLETED,
            state=TaskState.FAILED,
            message="Estado incompatible",
        )
