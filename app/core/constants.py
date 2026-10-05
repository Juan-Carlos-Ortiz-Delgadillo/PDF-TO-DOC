"""Constantes de dominio que no dependen de la interfaz ni de bibliotecas externas."""

from __future__ import annotations

from typing import Final

APP_NAME: Final[str] = "PDF2Word"
APP_SLUG: Final[str] = "pdf2word"
CONFIG_VERSION: Final[int] = 1

PDF_EXTENSION: Final[str] = ".pdf"
DOCX_EXTENSION: Final[str] = ".docx"
PDF_SIGNATURE: Final[bytes] = b"%PDF-"

DEFAULT_OCR_LANGUAGE: Final[str] = "spa"
DEFAULT_LOG_MAX_BYTES: Final[int] = 5 * 1024 * 1024
DEFAULT_LOG_BACKUP_COUNT: Final[int] = 3

# Mantener estos límites evita que una entrada de UI accidental o maliciosa consuma
# memoria de forma desproporcionada antes de llegar al motor de conversión.
MAX_PAGE_SELECTION_TEXT_LENGTH: Final[int] = 1_024
MAX_PAGE_SELECTION_ITEMS: Final[int] = 10_000

SENSITIVE_FIELD_NAMES: Final[frozenset[str]] = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "contrasena",
        "contraseña",
        "credential",
        "credentials",
        "password",
        "passwd",
        "secret",
        "token",
    }
)
