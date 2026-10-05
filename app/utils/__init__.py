"""Utilidades de archivos, validación y entorno sin dependencias de interfaz."""

from .file_utils import (
    atomic_write_json,
    atomic_write_text,
    ensure_directory,
    format_file_size,
    has_pdf_signature,
    path_display_name,
    safe_unlink,
)
from .system_utils import (
    CommandAvailability,
    OCRDependencyStatus,
    check_command,
    get_ocr_dependency_status,
    get_tesseract_languages,
    get_user_data_directory,
)
from .validation import (
    validate_docx_file,
    validate_docx_structure,
    validate_input_pdf,
    validate_output_path,
    validate_pdf_file,
)

__all__ = [
    "CommandAvailability",
    "OCRDependencyStatus",
    "atomic_write_json",
    "atomic_write_text",
    "check_command",
    "ensure_directory",
    "format_file_size",
    "get_ocr_dependency_status",
    "get_tesseract_languages",
    "get_user_data_directory",
    "has_pdf_signature",
    "path_display_name",
    "safe_unlink",
    "validate_docx_file",
    "validate_docx_structure",
    "validate_input_pdf",
    "validate_output_path",
    "validate_pdf_file",
]
