"""Comprobación de dependencias del sistema para OCR y conversión."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.utils.system_utils import OCRDependencyStatus, check_command, get_ocr_dependency_status


class ToolStatus(str, Enum):
    """Estado de un binario o dependencia opcional."""

    AVAILABLE = "available"
    MISSING = "missing"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class DependencyCheckService:
    """Agrupa la comprobación de comandos del sistema para la aplicación."""

    def check_pdf_tools(self) -> dict[str, ToolStatus]:
        return {
            "python": ToolStatus.AVAILABLE,
            "pdftoppm": (
                ToolStatus.AVAILABLE
                if check_command("pdftoppm").available
                else ToolStatus.MISSING
            ),
            "tesseract": (
                ToolStatus.AVAILABLE
                if check_command("tesseract").available
                else ToolStatus.MISSING
            ),
            "ocrmypdf": (
                ToolStatus.AVAILABLE
                if check_command("ocrmypdf").available
                else ToolStatus.MISSING
            ),
        }

    def check_ocr(self) -> dict[str, object]:
        status: OCRDependencyStatus = get_ocr_dependency_status()
        return {
            "ocrmypdf": status.ocrmypdf,
            "tesseract": status.tesseract,
            "languages": status.languages,
            "is_available": status.is_available,
        }
