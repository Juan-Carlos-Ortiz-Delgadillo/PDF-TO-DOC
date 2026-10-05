"""Primitivas compartidas de configuración, errores y registro de PDF2Word."""

from .config import AppSettings, ConfigRepository, OverwritePolicy, Theme
from .exceptions import (
    ConfigurationError,
    ConversionError,
    OCRDependencyError,
    OCRProcessingError,
    OutputPermissionError,
    OutputValidationError,
    PageSelectionError,
    PDF2WordError,
    PDFAnalysisError,
    PDFEncryptedError,
    PDFValidationError,
    TaskCancelledError,
    TaskStateTransitionError,
)

__all__ = [
    "AppSettings",
    "ConfigRepository",
    "ConfigurationError",
    "ConversionError",
    "OCRDependencyError",
    "OCRProcessingError",
    "OutputPermissionError",
    "OutputValidationError",
    "OverwritePolicy",
    "PDF2WordError",
    "PDFAnalysisError",
    "PDFEncryptedError",
    "PDFValidationError",
    "PageSelectionError",
    "TaskCancelledError",
    "TaskStateTransitionError",
    "Theme",
]
