"""Modelos tipados compartidos por los servicios, motores y la interfaz."""

from .conversion_config import ConversionConfig
from .conversion_result import ConversionResult
from .page_selection import PageSelection, PageSelectionKind, parse_page_selection
from .pdf_info import PDFInfo, PDFPageInfo
from .task_event import TaskErrorInfo, TaskEvent, TaskEventType
from .task_state import (
    TERMINAL_TASK_STATES,
    VALID_TASK_TRANSITIONS,
    TaskState,
    can_transition,
    coerce_task_state,
    ensure_transition,
    is_terminal_state,
)

__all__ = [
    "ConversionConfig",
    "ConversionResult",
    "PDFInfo",
    "PDFPageInfo",
    "PageSelection",
    "PageSelectionKind",
    "TERMINAL_TASK_STATES",
    "TaskErrorInfo",
    "TaskEvent",
    "TaskEventType",
    "TaskState",
    "VALID_TASK_TRANSITIONS",
    "can_transition",
    "coerce_task_state",
    "ensure_transition",
    "is_terminal_state",
    "parse_page_selection",
]
