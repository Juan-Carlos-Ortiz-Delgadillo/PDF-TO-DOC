"""Historial local, acotado y resistente a corrupción de conversiones."""

from __future__ import annotations

import json
import logging
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Any

from app.core.exceptions import PDF2WordError
from app.models import ConversionResult

_LOGGER = logging.getLogger(__name__)
_HISTORY_VERSION = 1


@dataclass(frozen=True, slots=True)
class HistoryEntry:
    """Metadatos mínimos de una conversión, sin contenido ni credenciales."""

    input_path: Path
    output_path: Path | None
    timestamp: datetime
    pages_requested: tuple[int, ...]
    duration_seconds: float
    status: str
    error_code: str | None = None

    def __post_init__(self) -> None:
        input_path = Path(self.input_path)
        output_path = Path(self.output_path) if self.output_path is not None else None
        timestamp = self.timestamp
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)
        else:
            timestamp = timestamp.astimezone(UTC)
        pages = tuple(int(page) for page in self.pages_requested)

        if any(page < 1 for page in pages):
            raise ValueError("Las páginas del historial deben usar numeración desde 1")
        if self.duration_seconds < 0:
            raise ValueError("La duración del historial no puede ser negativa")
        if not str(self.status).strip():
            raise ValueError("El estado del historial no puede estar vacío")

        object.__setattr__(self, "input_path", input_path)
        object.__setattr__(self, "output_path", output_path)
        object.__setattr__(self, "timestamp", timestamp)
        object.__setattr__(self, "pages_requested", pages)
        object.__setattr__(self, "status", str(self.status))

    @classmethod
    def from_conversion_result(cls, result: ConversionResult) -> HistoryEntry:
        """Crea una entrada a partir del contrato de resultado de conversión."""

        raw_status = result.status
        status = getattr(raw_status, "value", raw_status)
        raw_pages = getattr(result, "pages_requested", ())
        return cls(
            input_path=Path(result.input_path),
            output_path=(
                Path(output_path)
                if (output_path := getattr(result, "output_path", None)) is not None
                else None
            ),
            timestamp=datetime.now(UTC),
            pages_requested=tuple(int(page) for page in raw_pages),
            duration_seconds=float(result.duration_seconds),
            status=str(status),
            error_code=getattr(result, "error_code", None),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serializa únicamente metadatos permitidos para persistencia local."""

        return {
            "input_path": str(self.input_path),
            "output_path": str(self.output_path) if self.output_path is not None else None,
            "timestamp": self.timestamp.isoformat(),
            "pages_requested": list(self.pages_requested),
            "duration_seconds": self.duration_seconds,
            "status": self.status,
            "error_code": self.error_code,
        }

    @classmethod
    def from_dict(cls, value: object) -> HistoryEntry:
        """Reconstruye una entrada validando un registro JSON no confiable."""

        if not isinstance(value, dict):
            raise ValueError("La entrada de historial debe ser un objeto JSON")

        raw_timestamp = value.get("timestamp")
        if not isinstance(raw_timestamp, str):
            raise ValueError("La entrada de historial no tiene fecha válida")
        timestamp = datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00"))

        raw_pages = value.get("pages_requested", [])
        if not isinstance(raw_pages, list):
            raise ValueError("La selección de páginas del historial debe ser una lista")

        input_path = value.get("input_path")
        output_path = value.get("output_path")
        status = value.get("status")
        duration = value.get("duration_seconds")
        error_code = value.get("error_code")
        if not isinstance(input_path, str) or not input_path:
            raise ValueError("La entrada de historial no tiene ruta de entrada válida")
        if output_path is not None and not isinstance(output_path, str):
            raise ValueError("La ruta de salida del historial no es válida")
        if not isinstance(status, str):
            raise ValueError("El estado del historial no es válido")
        if not isinstance(duration, int | float):
            raise ValueError("La duración del historial no es válida")
        if error_code is not None and not isinstance(error_code, str):
            raise ValueError("El código de error del historial no es válido")

        return cls(
            input_path=Path(input_path),
            output_path=Path(output_path) if output_path else None,
            timestamp=timestamp,
            pages_requested=tuple(int(page) for page in raw_pages),
            duration_seconds=float(duration),
            status=status,
            error_code=error_code,
        )


class HistoryService:
    """Administra un único JSON local con escritura atómica y límite de entradas.

    Por defecto se conservan las 100 conversiones más recientes. Si el JSON se
    corrompe, la lectura devuelve un historial vacío; antes de la siguiente
    escritura se conserva una copia ``.corrupt-*`` para no destruir evidencia
    recuperable del archivo dañado.
    """

    def __init__(self, path: Path | None = None, *, max_entries: int = 100) -> None:
        if max_entries < 1:
            raise ValueError("max_entries debe ser al menos 1")
        self._path = Path(path).expanduser() if path is not None else self.default_path()
        self._max_entries = max_entries
        self._lock = RLock()

    @property
    def path(self) -> Path:
        """Ruta del archivo JSON de historial."""

        return self._path

    @property
    def max_entries(self) -> int:
        """Número máximo de entradas persistidas."""

        return self._max_entries

    @staticmethod
    def default_path() -> Path:
        """Obtiene una ubicación de datos de usuario adecuada a la plataforma."""

        application_name = "PDF2Word"
        home = Path.home()
        if sys.platform == "darwin":
            return home / "Library" / "Application Support" / application_name / "history.json"
        if os.name == "nt":
            base = Path(os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or home)
            return base / application_name / "history.json"
        base = Path(os.environ.get("XDG_STATE_HOME", home / ".local" / "state"))
        return base / application_name / "history.json"

    def load(self) -> list[HistoryEntry]:
        """Carga entradas válidas; una corrupción no impide iniciar la aplicación."""

        with self._lock:
            entries, _ = self._load_entries()
            return entries

    def record(self, entry: HistoryEntry) -> HistoryEntry:
        """Añade una entrada y persiste las más recientes de forma atómica."""

        if not isinstance(entry, HistoryEntry):
            raise TypeError("entry debe ser una instancia de HistoryEntry")
        with self._lock:
            entries, corrupted = self._load_entries()
            if corrupted:
                self._preserve_corrupt_file()
            entries.append(entry)
            trimmed_entries = entries[-self._max_entries :]
            self._write_entries(trimmed_entries)
        return entry

    def record_result(self, result: ConversionResult) -> HistoryEntry:
        """Convierte y registra un resultado de conversión."""

        return self.record(HistoryEntry.from_conversion_result(result))

    def add(self, entry: HistoryEntry) -> HistoryEntry:
        """Alias de :meth:`record` para consumidores que hablan de """ """añadir""" """."""

        return self.record(entry)

    def clear(self) -> None:
        """Vacía el historial mediante la misma escritura atómica."""

        with self._lock:
            _, corrupted = self._load_entries()
            if corrupted:
                self._preserve_corrupt_file()
            self._write_entries([])

    def _load_entries(self) -> tuple[list[HistoryEntry], bool]:
        if not self._path.exists():
            return [], False
        try:
            with self._path.open("r", encoding="utf-8") as history_file:
                payload = json.load(history_file)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            _LOGGER.warning("No se pudo leer el historial local: %s", type(error).__name__)
            return [], True

        raw_entries = self._entries_from_payload(payload)
        if raw_entries is None:
            _LOGGER.warning("El historial local tiene una estructura no reconocida")
            return [], True

        entries: list[HistoryEntry] = []
        for index, raw_entry in enumerate(raw_entries):
            try:
                entries.append(HistoryEntry.from_dict(raw_entry))
            except (TypeError, ValueError, OverflowError) as error:
                _LOGGER.warning(
                    "Se omitió una entrada inválida del historial local (índice %s, %s)",
                    index,
                    type(error).__name__,
                )
        return entries[-self._max_entries :], False

    @staticmethod
    def _entries_from_payload(payload: object) -> list[object] | None:
        # Se acepta la lista plana usada por versiones tempranas para facilitar
        # una migración sin pérdida de historial.
        if isinstance(payload, list):
            return payload
        if not isinstance(payload, dict):
            return None
        entries = payload.get("entries")
        if not isinstance(entries, list):
            return None
        return entries

    def _write_entries(self, entries: list[HistoryEntry]) -> None:
        payload = {
            "version": _HISTORY_VERSION,
            "entries": [entry.to_dict() for entry in entries],
        }
        temporary_name: str | None = None
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{self._path.stem}-",
                suffix=".tmp",
                dir=self._path.parent,
            )
            with os.fdopen(descriptor, "w", encoding="utf-8") as history_file:
                json.dump(payload, history_file, ensure_ascii=False, indent=2, sort_keys=True)
                history_file.write("\n")
                history_file.flush()
                os.fsync(history_file.fileno())
            self._set_private_permissions(Path(temporary_name))
            os.replace(temporary_name, self._path)
            temporary_name = None
        except (OSError, TypeError, ValueError) as error:
            raise PDF2WordError(
                "No se pudo guardar el historial local.",
                diagnostic_message=f"{type(error).__name__}: {str(error)[:300]}",
                error_code="history_write_failed",
            ) from error
        finally:
            if temporary_name is not None:
                try:
                    Path(temporary_name).unlink(missing_ok=True)
                except OSError:
                    _LOGGER.warning("No se pudo limpiar un temporal de historial")

    def _preserve_corrupt_file(self) -> None:
        if not self._path.exists():
            return
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        backup_path = self._path.with_name(f"{self._path.name}.corrupt-{timestamp}")
        try:
            shutil.copy2(self._path, backup_path)
            self._set_private_permissions(backup_path)
        except OSError as error:
            raise PDF2WordError(
                "No se pudo preservar el historial dañado antes de reemplazarlo.",
                diagnostic_message=f"{type(error).__name__}: {str(error)[:300]}",
                error_code="history_corrupt_backup_failed",
            ) from error

    @staticmethod
    def _set_private_permissions(path: Path) -> None:
        if os.name != "nt":
            try:
                path.chmod(0o600)
            except OSError:
                _LOGGER.warning("No se pudieron ajustar permisos del historial local")
