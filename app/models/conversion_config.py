"""Configuración inmutable de una conversión concreta."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from app.core.constants import DOCX_EXTENSION

from .page_selection import PageSelection

_OCR_LANGUAGE_RE = re.compile(r"^[A-Za-z0-9_+\-]{1,64}$")


@dataclass(frozen=True, slots=True)
class ConversionConfig:
    """Opciones de una tarea, sin contraseñas ni contenido de documentos."""

    input_path: Path
    output_path: Path
    page_selection: PageSelection
    use_ocr: bool
    ocr_language: str
    multiprocessing_enabled: bool
    overwrite_confirmed: bool

    def __post_init__(self) -> None:
        input_path = self._coerce_path(self.input_path, "input_path")
        output_path = self._coerce_path(self.output_path, "output_path")
        object.__setattr__(self, "input_path", input_path)
        object.__setattr__(self, "output_path", output_path)

        if output_path.suffix.casefold() != DOCX_EXTENSION:
            raise ValueError("output_path debe tener extensión .docx.")
        if not isinstance(self.page_selection, PageSelection):
            raise TypeError("page_selection debe ser una instancia de PageSelection.")
        for field_name in (
            "use_ocr",
            "multiprocessing_enabled",
            "overwrite_confirmed",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} debe ser booleano.")

        language = self.ocr_language.strip() if isinstance(self.ocr_language, str) else ""
        if not _OCR_LANGUAGE_RE.fullmatch(language):
            raise ValueError("ocr_language debe ser un identificador OCR válido.")
        object.__setattr__(self, "ocr_language", language)

    @staticmethod
    def _coerce_path(value: Path | os.PathLike[str] | str, field_name: str) -> Path:
        if not isinstance(value, Path | os.PathLike | str):
            raise TypeError(f"{field_name} debe ser una ruta.")
        path = Path(value)
        if not str(path):
            raise ValueError(f"{field_name} no puede estar vacío.")
        return path

    def pages_requested(self, total_pages: int) -> tuple[int, ...]:
        """Resuelve la selección para el PDF analizado, aún en base humana."""

        return self.page_selection.resolve(total_pages)

    @property
    def output_directory(self) -> Path:
        return self.output_path.parent

    @property
    def output_filename(self) -> str:
        return self.output_path.name
