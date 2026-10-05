"""Eventos tipados que trasladan el estado de una tarea hacia la interfaz."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.core.logger import sanitize_text

from .task_state import TaskState, coerce_task_state


class TaskEventType(str, Enum):
    STARTED = "started"
    PROGRESS = "progress"
    STATUS = "status"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class TaskErrorInfo:
    """Error estructurado apto para UI e historial; no conserva la excepción original."""

    user_message: str
    error_code: str | None = None
    diagnostic_message: str | None = None

    def __post_init__(self) -> None:
        if not self.user_message.strip():
            raise ValueError("user_message no puede estar vacío.")
        if self.error_code is not None and not self.error_code.strip():
            raise ValueError("error_code no puede estar vacío.")
        if self.diagnostic_message is not None:
            object.__setattr__(self, "diagnostic_message", sanitize_text(self.diagnostic_message))


@dataclass(frozen=True, slots=True)
class TaskEvent:
    """Actualización de una tarea; el porcentaje solo se incluye si es fiable."""

    event_type: TaskEventType
    state: TaskState
    message: str
    percentage: float | None = None
    current_page: int | None = None
    total_pages: int | None = None
    error: TaskErrorInfo | None = None

    def __post_init__(self) -> None:
        event_type = self._coerce_event_type(self.event_type)
        object.__setattr__(self, "event_type", event_type)
        state = coerce_task_state(self.state)
        object.__setattr__(self, "state", state)
        if not isinstance(self.message, str):
            raise TypeError("message debe ser texto.")

        if self.percentage is not None:
            if isinstance(self.percentage, bool) or not isinstance(self.percentage, int | float):
                raise TypeError("percentage debe ser un número entre 0 y 100.")
            percentage = float(self.percentage)
            if not 0 <= percentage <= 100:
                raise ValueError("percentage debe estar entre 0 y 100.")
            object.__setattr__(self, "percentage", percentage)

        if (self.current_page is None) != (self.total_pages is None):
            raise ValueError("current_page y total_pages deben indicarse juntos.")
        if (
            self.current_page is not None
            and self.total_pages is not None
            and (
                isinstance(self.current_page, bool)
                or isinstance(self.total_pages, bool)
                or self.current_page < 1
                or self.total_pages < 1
                or self.current_page > self.total_pages
            )
        ):
            raise ValueError("Los datos de página no son válidos.")

        if self.error is not None and not isinstance(self.error, TaskErrorInfo):
            raise TypeError("error debe ser TaskErrorInfo o None.")
        expected_state = {
            TaskEventType.COMPLETED: TaskState.COMPLETED,
            TaskEventType.FAILED: TaskState.FAILED,
            TaskEventType.CANCELLED: TaskState.CANCELLED,
        }.get(event_type)
        if expected_state is not None and state is not expected_state:
            raise ValueError("El tipo de evento no coincide con el estado final.")

    @staticmethod
    def _coerce_event_type(value: TaskEventType | str) -> TaskEventType:
        if isinstance(value, TaskEventType):
            return value
        try:
            return TaskEventType(value.casefold())
        except (AttributeError, ValueError) as error:
            raise ValueError(f"Tipo de evento desconocido: {value!r}") from error

    @property
    def is_indeterminate(self) -> bool:
        """True cuando no hay un porcentaje fiable que mostrar."""

        return self.percentage is None

    @classmethod
    def progress(
        cls,
        *,
        state: TaskState,
        message: str,
        percentage: float | None = None,
        current_page: int | None = None,
        total_pages: int | None = None,
    ) -> TaskEvent:
        return cls(
            event_type=TaskEventType.PROGRESS,
            state=state,
            message=message,
            percentage=percentage,
            current_page=current_page,
            total_pages=total_pages,
        )
