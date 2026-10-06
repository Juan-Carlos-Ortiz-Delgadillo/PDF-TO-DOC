"""Registro local con rotación y saneamiento de datos sensibles."""

from __future__ import annotations

import copy
import logging
import os
import re
import sys
from collections.abc import Mapping
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from .constants import (
    APP_SLUG,
    DEFAULT_LOG_BACKUP_COUNT,
    DEFAULT_LOG_MAX_BYTES,
    SENSITIVE_FIELD_NAMES,
)

_REDACTED = "[REDACTADO]"
_SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(password|passwd|contrase(?:ñ|n)a|secret|token|api[_-]?key|authorization)\b"
    r"(\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|[^\s,;]+)"
)
_BEARER_TOKEN_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
_ABSOLUTE_PATH_RE = re.compile(r"(?<!\w)(?:[A-Za-z]:[\\/]|/)[^\s\"']+")


def sanitize_text(value: str) -> str:
    """Elimina secretos obvios y reduce rutas absolutas en texto diagnóstico.

    No intenta interpretar contenido de documentos; solo procesa texto de errores y
    mensajes de registro. El resultado conserva el nombre del archivo, que suele ser
    suficiente para diagnosticar un problema sin registrar la ubicación completa.
    """

    redacted = _SENSITIVE_ASSIGNMENT_RE.sub(r"\1\2" + _REDACTED, value)
    redacted = _BEARER_TOKEN_RE.sub("Bearer " + _REDACTED, redacted)

    def _shorten_path(match: re.Match[str]) -> str:
        raw_path = match.group(0)
        normalized = raw_path.replace("\\", "/").rstrip("/")
        filename = normalized.rsplit("/", maxsplit=1)[-1]
        return f"…/{filename}" if filename else "…/"

    return _ABSOLUTE_PATH_RE.sub(_shorten_path, redacted)


def sanitize_log_value(value: Any) -> Any:
    """Devuelve una versión segura de un valor que vaya a un registro."""

    if isinstance(value, Path):
        return value.name
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, Mapping):
        return {
            str(key): _REDACTED
            if str(key).casefold() in SENSITIVE_FIELD_NAMES
            else sanitize_log_value(item)
            for key, item in value.items()
        }
    if isinstance(value, tuple):
        return tuple(sanitize_log_value(item) for item in value)
    if isinstance(value, list):
        return [sanitize_log_value(item) for item in value]
    if isinstance(value, set):
        return {sanitize_log_value(item) for item in value}
    return value


class SanitizingFormatter(logging.Formatter):
    """Formatter que evita que los argumentos de logging filtren secretos."""

    def format(self, record: logging.LogRecord) -> str:
        safe_record = copy.copy(record)
        safe_record.msg = (
            record.msg if isinstance(record.msg, str) else sanitize_log_value(record.msg)
        )
        safe_record.args = sanitize_log_value(record.args)
        safe_message = sanitize_text(safe_record.getMessage())
        safe_record.msg = "%s"
        safe_record.args = (safe_message,)
        return super().format(safe_record)


def get_default_log_path() -> Path:
    """Obtiene una ruta de log escribible por usuario, fuera de la instalación."""

    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "PDF2Word" / "logs" / f"{APP_SLUG}.log"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Logs" / "PDF2Word" / f"{APP_SLUG}.log"
    base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return base / APP_SLUG / "logs" / f"{APP_SLUG}.log"


def configure_logging(
    log_path: Path | None = None,
    *,
    level: int = logging.INFO,
    max_bytes: int = DEFAULT_LOG_MAX_BYTES,
    backup_count: int = DEFAULT_LOG_BACKUP_COUNT,
) -> logging.Logger:
    """Configura el logger de la aplicación sin duplicar handlers entre arranques."""

    if max_bytes <= 0:
        raise ValueError("max_bytes debe ser positivo.")
    if backup_count < 0:
        raise ValueError("backup_count no puede ser negativo.")

    logger = logging.getLogger(APP_SLUG)
    logger.setLevel(level)
    logger.propagate = False

    for handler in tuple(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    formatter = SanitizingFormatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    destination = log_path or get_default_log_path()
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            destination,
            encoding="utf-8",
            maxBytes=max_bytes,
            backupCount=backup_count,
        )
    except OSError:
        # La aplicación sigue siendo usable si el sistema no permite crear el log.
        logger.warning("No fue posible preparar el archivo de registro local.")
    else:
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Obtiene un logger hijo; la configuración se realiza en el arranque."""

    return logging.getLogger(APP_SLUG if name is None else f"{APP_SLUG}.{name}")
