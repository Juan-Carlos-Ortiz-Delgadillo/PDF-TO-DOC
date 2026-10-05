"""Errores de dominio con mensajes seguros para la interfaz."""

from __future__ import annotations

from typing import ClassVar

from .logger import sanitize_text


class PDF2WordError(Exception):
    """Base para errores que pueden presentarse sin exponer detalles internos."""

    default_error_code: ClassVar[str] = "pdf2word_error"
    default_user_message: ClassVar[str] = "Ocurrió un error durante la operación."

    def __init__(
        self,
        user_message: str | None = None,
        diagnostic_message: str | None = None,
        error_code: str | None = None,
    ) -> None:
        self.user_message = user_message or self.default_user_message
        self.diagnostic_message = sanitize_text(diagnostic_message) if diagnostic_message else None
        self.error_code = error_code or self.default_error_code
        super().__init__(self.diagnostic_message or self.user_message)


class PDFValidationError(PDF2WordError):
    default_error_code = "pdf_validation_error"
    default_user_message = "El archivo seleccionado no es un PDF válido."


class PDFEncryptedError(PDF2WordError):
    default_error_code = "pdf_encrypted_error"
    default_user_message = "El PDF está protegido y no se puede procesar sin autorización."


class PDFAnalysisError(PDF2WordError):
    default_error_code = "pdf_analysis_error"
    default_user_message = "No fue posible analizar el PDF seleccionado."


class OCRDependencyError(PDF2WordError):
    default_error_code = "ocr_dependency_error"
    default_user_message = "Las dependencias locales necesarias para OCR no están disponibles."


class OCRProcessingError(PDF2WordError):
    default_error_code = "ocr_processing_error"
    default_user_message = "No fue posible procesar el OCR del documento."


class ConversionError(PDF2WordError):
    default_error_code = "conversion_error"
    default_user_message = "No fue posible convertir el PDF a Word."


class OutputValidationError(PDF2WordError):
    default_error_code = "output_validation_error"
    default_user_message = "El archivo Word generado no pudo validarse."


class OutputPermissionError(PDF2WordError):
    default_error_code = "output_permission_error"
    default_user_message = "No hay permiso para escribir en la ubicación de salida."


class TaskCancelledError(PDF2WordError):
    default_error_code = "task_cancelled"
    default_user_message = "La conversión fue cancelada."


class TaskStateTransitionError(PDF2WordError):
    default_error_code = "invalid_task_state_transition"
    default_user_message = "La tarea no puede continuar desde su estado actual."


class PageSelectionError(PDF2WordError):
    default_error_code = "invalid_page_selection"
    default_user_message = "La selección de páginas no es válida."


class ConfigurationError(PDF2WordError):
    default_error_code = "configuration_error"
    default_user_message = "La configuración local no es válida."
