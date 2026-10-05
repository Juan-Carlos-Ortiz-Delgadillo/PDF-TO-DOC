"""Servicios de dominio para el procesamiento local de PDF2Word.

Los servicios de este paquete no dependen de la interfaz Qt.  Las
dependencias opcionales (PyMuPDF, python-docx y OCRmyPDF) se cargan sólo en
el momento en que se necesitan, para que la aplicación pueda informar una
ausencia de dependencia de forma controlada.
"""

from app.services.conversion_service import ConversionService
from app.services.dependency_check_service import (
    DependencyCheckService,
    OCRDependencyStatus,
    ToolStatus,
)
from app.services.history_service import HistoryEntry, HistoryService
from app.services.ocr_service import OCRService
from app.services.output_service import OutputService
from app.services.pdf_analyzer import PDFAnalyzer
from app.services.settings_service import SettingsService

__all__ = [
    "ConversionService",
    "DependencyCheckService",
    "HistoryEntry",
    "HistoryService",
    "OCRDependencyStatus",
    "OCRService",
    "OutputService",
    "PDFAnalyzer",
    "SettingsService",
    "ToolStatus",
]
