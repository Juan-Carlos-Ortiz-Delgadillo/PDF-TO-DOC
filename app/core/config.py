"""Configuración persistente y tipos de entorno para PDF2Word."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from app.utils.file_utils import atomic_write_json, ensure_directory


class Theme(str, Enum):
    """Tema visual de aplicación."""

    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"

    @classmethod
    def coerce(cls, value: str | Theme | None) -> Theme:
        if value is None:
            return cls.SYSTEM
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).strip().lower())
        except ValueError as error:
            raise ValueError(f"Tema no válido: {value!r}") from error


class OverwritePolicy(str, Enum):
    """Cómo se comporta la aplicación si el archivo de salida ya existe."""

    ASK = "ask"
    OVERWRITE = "overwrite"
    SKIP = "skip"

    @classmethod
    def coerce(cls, value: str | OverwritePolicy | None) -> OverwritePolicy:
        if value is None:
            return cls.ASK
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).strip().lower())
        except ValueError as error:
            raise ValueError(f"Política de sobrescritura no válida: {value!r}") from error


@dataclass(frozen=True, slots=True)
class AppSettings:
    """Configuración inmutable del programa."""

    theme: Theme = Theme.SYSTEM
    overwrite_policy: OverwritePolicy = OverwritePolicy.ASK
    ocr_enabled: bool = False
    ocr_language: str = "spa"
    output_directory: Path = field(default_factory=lambda: Path.home() / "Downloads")
    multiprocessing_enabled: bool = True
    default_page_selection: str = "all"

    def __post_init__(self) -> None:
        object.__setattr__(self, "theme", Theme.coerce(self.theme))
        object.__setattr__(self, "overwrite_policy", OverwritePolicy.coerce(self.overwrite_policy))
        language = str(self.ocr_language or "spa").strip()
        if not language:
            language = "spa"
        object.__setattr__(self, "ocr_language", language)
        object.__setattr__(self, "output_directory", Path(self.output_directory).expanduser())
        if not isinstance(self.ocr_enabled, bool):
            raise TypeError("ocr_enabled debe ser booleano.")
        if not isinstance(self.multiprocessing_enabled, bool):
            raise TypeError("multiprocessing_enabled debe ser booleano.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "theme": self.theme.value,
            "overwrite_policy": self.overwrite_policy.value,
            "ocr_enabled": self.ocr_enabled,
            "ocr_language": self.ocr_language,
            "output_directory": str(self.output_directory),
            "multiprocessing_enabled": self.multiprocessing_enabled,
            "default_page_selection": self.default_page_selection,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> AppSettings:
        if not isinstance(data, Mapping):
            raise ValueError("La configuración debe ser un objeto JSON válido.")
        raw_theme = data.get("theme", Theme.SYSTEM.value)
        raw_overwrite = data.get("overwrite_policy", OverwritePolicy.ASK.value)
        return cls(
            theme=Theme.coerce(raw_theme),
            overwrite_policy=OverwritePolicy.coerce(raw_overwrite),
            ocr_enabled=bool(data.get("ocr_enabled", False)),
            ocr_language=str(data.get("ocr_language", "spa") or "spa"),
            output_directory=data.get("output_directory", Path.home() / "Downloads"),
            multiprocessing_enabled=bool(data.get("multiprocessing_enabled", True)),
            default_page_selection=str(data.get("default_page_selection", "all") or "all"),
        )


class ConfigRepository:
    """Persistencia de configuración en JSON local con fallback seguro."""

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path).expanduser() if path is not None else self.default_path()

    @staticmethod
    def default_path() -> Path:
        if os.name == "nt":
            base = Path(os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming"))
            return base / "PDF2Word" / "settings.json"
        if sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / "PDF2Word" / "settings.json"
        base = Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"))
        return base / "pdf2word" / "settings.json"

    def load(self) -> AppSettings:
        if not self.path.exists():
            return AppSettings()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return AppSettings()
        try:
            return AppSettings.from_dict(payload)
        except ValueError:
            return AppSettings()

    def save(self, settings: AppSettings) -> Path:
        ensure_directory(self.path.parent)
        atomic_write_json(self.path, settings.to_dict())
        return self.path

    def update(self, **updates: Any) -> AppSettings:
        current = self.load().to_dict()
        current.update(updates)
        settings = AppSettings.from_dict(current)
        self.save(settings)
        return settings
