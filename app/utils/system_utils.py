"""Consultas locales del sistema y de dependencias externas opcionales."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from app.core.constants import APP_NAME, APP_SLUG


@dataclass(frozen=True, slots=True)
class CommandAvailability:
    """Disponibilidad de un ejecutable sin ejecutar comandos de shell."""

    command: str
    available: bool
    path: Path | None = None


@dataclass(frozen=True, slots=True)
class OCRDependencyStatus:
    """Resumen local de OCRmyPDF, Tesseract e idiomas detectados."""

    ocrmypdf: CommandAvailability
    tesseract: CommandAvailability
    languages: tuple[str, ...] = ()

    @property
    def is_available(self) -> bool:
        return self.ocrmypdf.available and self.tesseract.available


def find_command(command: str) -> Path | None:
    """Localiza un ejecutable usando PATH, sin construir una orden de shell."""

    if not command or any(character.isspace() for character in command):
        return None
    result = shutil.which(command)
    return Path(result) if result else None


def check_command(command: str) -> CommandAvailability:
    """Describe si un comando local está disponible."""

    path = find_command(command)
    return CommandAvailability(command=command, available=path is not None, path=path)


def get_tesseract_languages(*, timeout_seconds: float = 5.0) -> tuple[str, ...]:
    """Consulta idiomas instalados de Tesseract con argumentos seguros."""

    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds debe ser positivo.")
    if find_command("tesseract") is None:
        return ()
    try:
        result = subprocess.run(
            ["tesseract", "--list-langs"],
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ()
    if result.returncode != 0:
        return ()
    languages = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip() and not line.casefold().startswith("list of available languages")
    ]
    return tuple(sorted(set(languages)))


def get_ocr_dependency_status(*, timeout_seconds: float = 5.0) -> OCRDependencyStatus:
    """Detecta dependencias OCR sin descargar ni modificar el sistema."""

    ocrmypdf = check_command("ocrmypdf")
    tesseract = check_command("tesseract")
    languages = (
        get_tesseract_languages(timeout_seconds=timeout_seconds)
        if tesseract.available
        else ()
    )
    return OCRDependencyStatus(ocrmypdf=ocrmypdf, tesseract=tesseract, languages=languages)


def get_user_data_directory(app_name: str = APP_NAME) -> Path:
    """Ruta de datos de usuario adecuada para cada sistema, sin crearla."""

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / app_name
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / app_name
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / APP_SLUG
