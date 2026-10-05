"""Modelos inmutables producidos por el análisis de un PDF."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class PDFPageInfo:
    """Datos detectados para una página con numeración visible desde 1."""

    page_number: int
    has_text: bool
    text_length: int
    has_images: bool
    requires_ocr: bool

    def __post_init__(self) -> None:
        if isinstance(self.page_number, bool) or self.page_number < 1:
            raise ValueError("page_number debe ser mayor o igual a 1.")
        if isinstance(self.text_length, bool) or self.text_length < 0:
            raise ValueError("text_length no puede ser negativo.")


@dataclass(frozen=True, slots=True)
class PDFInfo:
    """Resumen de un PDF sin conservar ni exponer su contenido."""

    path: Path
    page_count: int
    file_size: int
    has_text: bool
    has_images: bool
    is_encrypted: bool
    requires_ocr: bool
    pages: tuple[PDFPageInfo, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", Path(self.path))
        pages = tuple(self.pages)
        object.__setattr__(self, "pages", pages)

        if isinstance(self.page_count, bool) or self.page_count < 0:
            raise ValueError("page_count no puede ser negativo.")
        if isinstance(self.file_size, bool) or self.file_size < 0:
            raise ValueError("file_size no puede ser negativo.")
        if pages and len(pages) != self.page_count:
            raise ValueError("El número de páginas detalladas no coincide con page_count.")
        if any(not isinstance(page, PDFPageInfo) for page in pages):
            raise TypeError("pages debe contener instancias de PDFPageInfo.")

        page_numbers = tuple(page.page_number for page in pages)
        if len(set(page_numbers)) != len(page_numbers):
            raise ValueError("No puede haber páginas repetidas.")
        if any(page_number > self.page_count for page_number in page_numbers):
            raise ValueError("Hay una página detallada fuera del documento.")

    @property
    def document_kind(self) -> str:
        """Clasificación orientativa derivada de las señales de análisis."""

        if self.is_encrypted:
            return "protected"
        if self.requires_ocr and self.has_text:
            return "mixed"
        if self.requires_ocr:
            return "scanned"
        return "digital"

    @property
    def ocr_page_numbers(self) -> tuple[int, ...]:
        """Páginas para las que el analizador estima que OCR puede ser útil."""

        return tuple(page.page_number for page in self.pages if page.requires_ocr)
