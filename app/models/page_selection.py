"""Selección de páginas con numeración visible desde 1."""

from __future__ import annotations

import builtins
import re
from dataclasses import dataclass
from enum import Enum

from app.core.constants import MAX_PAGE_SELECTION_ITEMS, MAX_PAGE_SELECTION_TEXT_LENGTH
from app.core.exceptions import PageSelectionError


class PageSelectionKind(str, Enum):
    """Formas de selección admitidas por el flujo de conversión."""

    ALL = "all"
    RANGE = "range"
    PAGES = "pages"


_RANGE_RE = re.compile(r"^(\d+)\s*-\s*(\d+)$")
_PAGES_RE = re.compile(r"^\d+(?:\s*,\s*\d+)*$")
_ALL_TOKENS = frozenset({"*", "all", "todas", "todo"})


@dataclass(frozen=True, slots=True)
class PageSelection:
    """Selección independiente de la API y de los índices de cada motor.

    Las páginas específicas se normalizan ascendentemente. Así el DOCX mantiene el
    orden natural del documento incluso si la interfaz recibió los números en otro
    orden.
    """

    kind: PageSelectionKind
    start: int | None = None
    end: int | None = None
    pages: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        kind = self._coerce_kind(self.kind)
        object.__setattr__(self, "kind", kind)

        if kind is PageSelectionKind.ALL:
            if self.start is not None or self.end is not None or self.pages:
                raise ValueError("La selección total no admite páginas ni rango.")
            return

        if kind is PageSelectionKind.RANGE:
            if self.pages:
                raise ValueError("Un rango no admite una lista de páginas.")
            self._validate_page_number(self.start, "inicio")
            self._validate_page_number(self.end, "fin")
            assert self.start is not None
            assert self.end is not None
            if self.start > self.end:
                raise ValueError("El inicio del rango no puede superar el final.")
            return

        if self.start is not None or self.end is not None:
            raise ValueError("Una lista de páginas no admite límites de rango.")
        normalized = tuple(self.pages)
        if not normalized:
            raise ValueError("Debe indicarse al menos una página.")
        if len(normalized) > MAX_PAGE_SELECTION_ITEMS:
            raise ValueError("La selección contiene demasiadas páginas.")
        for page_number in normalized:
            self._validate_page_number(page_number, "página")
        if len(set(normalized)) != len(normalized):
            raise ValueError("La selección contiene páginas duplicadas.")
        object.__setattr__(self, "pages", tuple(sorted(normalized)))

    @staticmethod
    def _coerce_kind(value: PageSelectionKind | str) -> PageSelectionKind:
        if isinstance(value, PageSelectionKind):
            return value
        try:
            return PageSelectionKind(value)
        except ValueError as error:
            raise ValueError(f"Tipo de selección desconocido: {value!r}") from error

    @staticmethod
    def _validate_page_number(value: int | None, label: str) -> None:
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"El valor de {label} debe ser un entero mayor o igual a 1.")

    @classmethod
    def all(cls) -> PageSelection:
        """Crea una selección de todas las páginas."""

        return cls(PageSelectionKind.ALL)

    @classmethod
    def range(cls, start: int, end: int) -> PageSelection:
        """Crea un rango inclusivo de páginas visibles."""

        return cls(PageSelectionKind.RANGE, start=start, end=end)

    @classmethod
    def specific(cls, pages: tuple[int, ...] | list[int]) -> PageSelection:
        """Crea una selección de páginas específicas en orden natural."""

        return cls(PageSelectionKind.PAGES, pages=tuple(pages))

    @classmethod
    def parse(cls, value: str, total_pages: int) -> PageSelection:
        """Convierte la entrada de UI a una selección validada para un PDF concreto."""

        if not isinstance(value, str):
            raise PageSelectionError("La selección de páginas debe ser texto.")
        if len(value) > MAX_PAGE_SELECTION_TEXT_LENGTH:
            raise PageSelectionError("La selección de páginas es demasiado extensa.")

        text = value.strip()
        if not text:
            raise PageSelectionError("Indica las páginas que quieres convertir.")
        if text.casefold() in _ALL_TOKENS:
            selection = cls.all()
        else:
            range_match = _RANGE_RE.fullmatch(text)
            if range_match:
                selection = cls.range(int(range_match.group(1)), int(range_match.group(2)))
            elif _PAGES_RE.fullmatch(text):
                selection = cls.specific([int(item.strip()) for item in text.split(",")])
            else:
                raise PageSelectionError(
                    "Usa todas las páginas, un rango como 3-8 o una lista como 1,4,9."
                )
        return selection.validate_for(total_pages)

    def validate_for(self, total_pages: int) -> PageSelection:
        """Comprueba que la selección cabe dentro de ``total_pages``."""

        if isinstance(total_pages, bool) or not isinstance(total_pages, int) or total_pages < 1:
            raise PageSelectionError("El PDF no contiene páginas disponibles para convertir.")

        selected = self._raw_pages(total_pages)
        if selected[-1] > total_pages:
            raise PageSelectionError(
                "La selección incluye una página mayor que el total del documento.",
                diagnostic_message=f"Página solicitada: {selected[-1]}; total: {total_pages}.",
            )
        return self

    def resolve(self, total_pages: int) -> tuple[int, ...]:
        """Devuelve páginas humanas concretas, siempre en orden de documento."""

        self.validate_for(total_pages)
        return self._raw_pages(total_pages)

    def to_zero_based_indices(self, total_pages: int) -> tuple[int, ...]:
        """Traduce la selección a índices base cero para adaptadores de motores."""

        return tuple(page_number - 1 for page_number in self.resolve(total_pages))

    def is_contiguous(self, total_pages: int) -> bool:
        """Indica si el motor puede tratar la selección como un único intervalo."""

        selected = self.resolve(total_pages)
        return selected == tuple(builtins.range(selected[0], selected[-1] + 1))

    def display_value(self) -> str:
        """Representación breve y segura para una etiqueta de interfaz."""

        if self.kind is PageSelectionKind.ALL:
            return "Todas"
        if self.kind is PageSelectionKind.RANGE:
            return f"{self.start}-{self.end}"
        return ", ".join(str(page_number) for page_number in self.pages)

    def _raw_pages(self, total_pages: int) -> tuple[int, ...]:
        if self.kind is PageSelectionKind.ALL:
            return tuple(builtins.range(1, total_pages + 1))
        if self.kind is PageSelectionKind.RANGE:
            assert self.start is not None
            assert self.end is not None
            return tuple(builtins.range(self.start, self.end + 1))
        return self.pages


def parse_page_selection(value: str, total_pages: int) -> PageSelection:
    """Alias funcional de :meth:`PageSelection.parse` para la capa de UI."""

    return PageSelection.parse(value, total_pages)
