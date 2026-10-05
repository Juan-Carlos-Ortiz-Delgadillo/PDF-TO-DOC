"""Estados y transiciones válidas de una tarea de conversión."""

from __future__ import annotations

from enum import Enum
from types import MappingProxyType

from app.core.exceptions import TaskStateTransitionError


class TaskState(str, Enum):
    IDLE = "idle"
    ANALYZING = "analyzing"
    OCR_REQUIRED = "ocr_required"
    OCR_PROCESSING = "ocr_processing"
    CONVERTING = "converting"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in TERMINAL_TASK_STATES

    def can_transition_to(self, next_state: TaskState | str) -> bool:
        return can_transition(self, next_state)


TERMINAL_TASK_STATES = frozenset(
    {TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED}
)

VALID_TASK_TRANSITIONS = MappingProxyType(
    {
        TaskState.IDLE: frozenset({TaskState.ANALYZING}),
        TaskState.ANALYZING: frozenset(
            {TaskState.OCR_REQUIRED, TaskState.CONVERTING, TaskState.FAILED, TaskState.CANCELLED}
        ),
        TaskState.OCR_REQUIRED: frozenset(
            {TaskState.OCR_PROCESSING, TaskState.CONVERTING, TaskState.FAILED, TaskState.CANCELLED}
        ),
        TaskState.OCR_PROCESSING: frozenset(
            {TaskState.CONVERTING, TaskState.FAILED, TaskState.CANCELLED}
        ),
        TaskState.CONVERTING: frozenset(
            {TaskState.FINALIZING, TaskState.FAILED, TaskState.CANCELLED}
        ),
        TaskState.FINALIZING: frozenset(
            {TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED}
        ),
        TaskState.COMPLETED: frozenset({TaskState.IDLE}),
        TaskState.FAILED: frozenset({TaskState.IDLE}),
        TaskState.CANCELLED: frozenset({TaskState.IDLE}),
    }
)


def coerce_task_state(value: TaskState | str) -> TaskState:
    """Acepta el enum o su valor serializable y devuelve el enum correspondiente."""

    if isinstance(value, TaskState):
        return value
    if not isinstance(value, str):
        raise ValueError("El estado de tarea debe ser texto o TaskState.")
    try:
        return TaskState(value.casefold())
    except ValueError as error:
        try:
            return TaskState[value.upper()]
        except KeyError:
            raise ValueError(f"Estado de tarea desconocido: {value!r}") from error


def can_transition(current: TaskState | str, next_state: TaskState | str) -> bool:
    """Indica si una transición está permitida por la máquina de estados."""

    return coerce_task_state(next_state) in VALID_TASK_TRANSITIONS[coerce_task_state(current)]


def ensure_transition(current: TaskState | str, next_state: TaskState | str) -> TaskState:
    """Valida y devuelve el nuevo estado, o lanza un error de dominio claro."""

    current_state = coerce_task_state(current)
    target_state = coerce_task_state(next_state)
    if not can_transition(current_state, target_state):
        raise TaskStateTransitionError(
            "La tarea no puede continuar desde su estado actual.",
            diagnostic_message=(
                "Transición no permitida: "
                f"{current_state.value} -> {target_state.value}."
            ),
        )
    return target_state


def is_terminal_state(value: TaskState | str) -> bool:
    """Indica si un estado no admite más etapas de trabajo."""

    return coerce_task_state(value) in TERMINAL_TASK_STATES
