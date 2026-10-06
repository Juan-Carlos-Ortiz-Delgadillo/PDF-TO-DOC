"""Operaciones pequeñas y seguras sobre rutas y archivos locales."""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.core.constants import PDF_SIGNATURE


def path_display_name(path: Path | str) -> str:
    """Devuelve solo el nombre de archivo para mensajes y registros seguros."""

    return Path(path).name or "archivo"


def format_file_size(size: int) -> str:
    """Formatea un tamaño para la interfaz sin depender de la plataforma."""

    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        raise ValueError("size debe ser un entero no negativo.")
    units = ("B", "KB", "MB", "GB", "TB")
    amount = float(size)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{int(amount)} {unit}" if unit == "B" else f"{amount:.1f} {unit}"
        amount /= 1024
    raise AssertionError("Las unidades de tamaño deben cubrir todos los casos.")


def read_file_prefix(path: Path | str, size: int = len(PDF_SIGNATURE)) -> bytes:
    """Lee un prefijo binario sin cargar el documento completo en memoria."""

    if size < 1:
        raise ValueError("size debe ser positivo.")
    with Path(path).open("rb") as source:
        return source.read(size)


def has_pdf_signature(path: Path | str) -> bool:
    """Comprueba la firma binaria de PDF; no sustituye la validación completa."""

    try:
        return read_file_prefix(path).startswith(PDF_SIGNATURE)
    except OSError:
        return False


def ensure_directory(path: Path | str) -> Path:
    """Crea una carpeta de forma idempotente y devuelve su ruta."""

    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    if not directory.is_dir():
        raise NotADirectoryError(f"La ruta no es una carpeta: {directory.name}")
    return directory


def atomic_write_text(
    path: Path | str,
    content: str,
    *,
    encoding: str = "utf-8",
    mode: int = 0o600,
) -> Path:
    """Escribe un archivo mediante reemplazo atómico en su misma carpeta.

    El archivo temporal se sincroniza antes del reemplazo para reducir el riesgo de
    una configuración truncada tras una interrupción del proceso.
    """

    destination = Path(path)
    if not destination.name:
        raise ValueError("La ruta de destino debe incluir un nombre de archivo.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.",
            suffix=".tmp",
            dir=destination.parent,
            text=True,
        )
        temporary_path = Path(temporary_name)
        try:
            if hasattr(os, "fchmod"):
                os.fchmod(descriptor, mode)
            else:
                os.chmod(temporary_name, mode)
            with os.fdopen(descriptor, "w", encoding=encoding) as temporary_file:
                descriptor = -1
                temporary_file.write(content)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, destination)
            with contextlib.suppress(OSError):
                # Algunos sistemas de archivos no admiten permisos POSIX.
                os.chmod(destination, mode)
        finally:
            if descriptor != -1:
                os.close(descriptor)
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)
    return destination


def atomic_write_json(
    path: Path | str,
    data: Mapping[str, Any],
    *,
    mode: int = 0o600,
) -> Path:
    """Serializa JSON local de manera legible y mediante reemplazo atómico."""

    serialized = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
    return atomic_write_text(path, f"{serialized}\n", mode=mode)


def safe_unlink(path: Path | str) -> bool:
    """Elimina un archivo concreto si existe, sin seguir una operación recursiva."""

    candidate = Path(path)
    with contextlib.suppress(FileNotFoundError):
        candidate.unlink()
        return True
    return False
