"""Validaciones de entrada y salida compartidas por la UI y los servicios."""

from __future__ import annotations

import os
import zipfile
from pathlib import Path

from app.core.constants import DOCX_EXTENSION, PDF_EXTENSION
from app.core.exceptions import OutputPermissionError, OutputValidationError, PDFValidationError

from .file_utils import has_pdf_signature, path_display_name


def validate_input_pdf(path: Path | str) -> Path:
    """Valida existencia, legibilidad, extensión y firma de un PDF local."""

    candidate = Path(path).expanduser()
    display_name = path_display_name(candidate)
    if not candidate.exists():
        raise PDFValidationError(
            "El archivo PDF seleccionado no existe.",
            diagnostic_message=f"No existe el archivo: {display_name}.",
        )
    if not candidate.is_file():
        raise PDFValidationError(
            "La ruta seleccionada no corresponde a un archivo PDF.",
            diagnostic_message=f"La ruta no es un archivo: {display_name}.",
        )
    if candidate.suffix.casefold() != PDF_EXTENSION:
        raise PDFValidationError(
            "Selecciona un archivo con extensión .pdf.",
            diagnostic_message=f"Extensión no admitida: {display_name}.",
        )
    try:
        file_size = candidate.stat().st_size
    except OSError as error:
        raise PDFValidationError(
            "No fue posible leer el PDF seleccionado.",
            diagnostic_message=f"No se pudo consultar {display_name}: {error}.",
        ) from error
    if file_size == 0:
        raise PDFValidationError("El archivo PDF está vacío.")
    if not has_pdf_signature(candidate):
        raise PDFValidationError(
            "El archivo no contiene una firma PDF válida.",
            diagnostic_message=f"Firma PDF ausente o ilegible en {display_name}.",
        )
    try:
        with candidate.open("rb"):
            pass
    except OSError as error:
        raise PDFValidationError(
            "No hay permiso para leer el PDF seleccionado.",
            diagnostic_message=f"No se pudo abrir {display_name}: {error}.",
        ) from error
    return candidate


def validate_output_path(path: Path | str, *, overwrite_confirmed: bool = False) -> Path:
    """Valida un destino DOCX sin crear ni sobrescribir nada."""

    candidate = Path(path).expanduser()
    display_name = path_display_name(candidate)
    if not candidate.name or candidate.name in {".", ".."}:
        raise OutputValidationError("Indica un nombre de archivo Word válido.")
    if candidate.suffix.casefold() != DOCX_EXTENSION:
        raise OutputValidationError("El archivo de salida debe tener extensión .docx.")
    parent = candidate.parent
    if not parent.exists():
        raise OutputValidationError("La carpeta de salida no existe.")
    if not parent.is_dir():
        raise OutputValidationError("La ubicación de salida no es una carpeta válida.")
    if candidate.exists() and not overwrite_confirmed:
        raise OutputValidationError(
            "El archivo de salida ya existe. Confirma la sobrescritura para continuar.",
            diagnostic_message=f"Destino existente: {display_name}.",
            error_code="output_exists",
        )
    if not os.access(parent, os.W_OK):
        raise OutputPermissionError(
            "No hay permiso para escribir en la carpeta de salida.",
            diagnostic_message=f"Sin permiso de escritura para destino: {display_name}.",
        )
    return candidate


def validate_docx_file(path: Path | str, *, min_size: int = 1) -> Path:
    """Comprueba que una salida tiene estructura DOCX, no solo extensión."""

    if min_size < 1:
        raise ValueError("min_size debe ser positivo.")
    candidate = Path(path)
    display_name = path_display_name(candidate)
    if not candidate.is_file():
        raise OutputValidationError(
            "El archivo Word generado no existe.",
            diagnostic_message=f"No se encontró DOCX: {display_name}.",
        )
    try:
        if candidate.stat().st_size < min_size:
            raise OutputValidationError("El archivo Word generado está vacío.")
        with zipfile.ZipFile(candidate) as archive:
            corrupted_entry = archive.testzip()
            contents = set(archive.namelist())
    except OutputValidationError:
        raise
    except (OSError, zipfile.BadZipFile) as error:
        raise OutputValidationError(
            "El archivo generado no tiene una estructura DOCX válida.",
            diagnostic_message=f"No se pudo abrir DOCX {display_name}: {error}.",
        ) from error
    if corrupted_entry is not None:
        raise OutputValidationError(
            "El archivo Word generado está dañado.",
            diagnostic_message=f"Entrada DOCX dañada: {corrupted_entry}.",
        )
    required_entries = {"[Content_Types].xml", "word/document.xml"}
    if not required_entries.issubset(contents):
        raise OutputValidationError(
            "El archivo generado no contiene un documento Word válido.",
            diagnostic_message=f"Estructura DOCX incompleta: {display_name}.",
        )
    return candidate


# Nombres explícitos para consumidores que prefieren la terminología de archivo.
validate_pdf_file = validate_input_pdf
validate_docx_structure = validate_docx_file
