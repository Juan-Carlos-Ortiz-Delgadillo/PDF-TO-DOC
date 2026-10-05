"""Resultado final y serializable de una tarea de conversión."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from app.core.logger import sanitize_text

from .task_state import TaskState, coerce_task_state, is_terminal_state


@dataclass(frozen=True, slots=True)
class ConversionResult:
    """Resultado sin contenido de documento ni información secreta."""

    input_path: Path
    output_path: Path | None
    status: TaskState
    pages_requested: tuple[int, ...]
    duration_seconds: float
    error_code: str | None = None
    user_message: str = ""
    diagnostic_message: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.input_path, Path | os.PathLike[str] | str):
            raise TypeError("input_path debe ser una ruta.")
        object.__setattr__(self, "input_path", Path(self.input_path))
        if self.output_path is not None:
            if not isinstance(self.output_path, Path | os.PathLike[str] | str):
                raise TypeError("output_path debe ser una ruta o None.")
            object.__setattr__(self, "output_path", Path(self.output_path))

        status = coerce_task_state(self.status)
        object.__setattr__(self, "status", status)
        if not is_terminal_state(status):
            raise ValueError("ConversionResult solo admite estados finales.")
        if status is TaskState.COMPLETED and self.output_path is None:
            raise ValueError("Una conversión completada debe incluir output_path.")

        requested_pages = tuple(self.pages_requested)
        if any(
            isinstance(page, bool) or not isinstance(page, int) or page < 1
            for page in requested_pages
        ):
            raise ValueError("pages_requested debe contener páginas positivas.")
        if len(set(requested_pages)) != len(requested_pages):
            raise ValueError("pages_requested no puede contener duplicados.")
        object.__setattr__(self, "pages_requested", requested_pages)

        duration = float(self.duration_seconds)
        if duration < 0:
            raise ValueError("duration_seconds no puede ser negativo.")
        object.__setattr__(self, "duration_seconds", duration)

        if self.error_code is not None and not self.error_code.strip():
            raise ValueError("error_code no puede estar vacío.")
        if self.diagnostic_message is not None:
            object.__setattr__(self, "diagnostic_message", sanitize_text(self.diagnostic_message))

    @classmethod
    def completed(
        cls,
        *,
        input_path: Path,
        output_path: Path,
        pages_requested: tuple[int, ...],
        duration_seconds: float,
        user_message: str = "Conversión completada.",
    ) -> ConversionResult:
        return cls(
            input_path=input_path,
            output_path=output_path,
            status=TaskState.COMPLETED,
            pages_requested=pages_requested,
            duration_seconds=duration_seconds,
            user_message=user_message,
        )

    @classmethod
    def failed(
        cls,
        *,
        input_path: Path,
        pages_requested: tuple[int, ...],
        duration_seconds: float,
        user_message: str,
        error_code: str | None = None,
        diagnostic_message: str | None = None,
    ) -> ConversionResult:
        return cls(
            input_path=input_path,
            output_path=None,
            status=TaskState.FAILED,
            pages_requested=pages_requested,
            duration_seconds=duration_seconds,
            error_code=error_code,
            user_message=user_message,
            diagnostic_message=diagnostic_message,
        )

    @classmethod
    def cancelled(
        cls,
        *,
        input_path: Path,
        pages_requested: tuple[int, ...],
        duration_seconds: float,
        user_message: str = "La conversión fue cancelada.",
    ) -> ConversionResult:
        return cls(
            input_path=input_path,
            output_path=None,
            status=TaskState.CANCELLED,
            pages_requested=pages_requested,
            duration_seconds=duration_seconds,
            user_message=user_message,
        )
