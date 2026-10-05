"""Módulos de interfaz de PDF2Word."""

from __future__ import annotations

try:
    from app.ui.main_window import MainWindow
except Exception:  # pragma: no cover - fallback defensivo para entornos sin GUI
    class MainWindow:  # type: ignore[no-redef]
        """Fallback mínimo cuando la GUI no está disponible."""

        def __init__(self, *args: object, **kwargs: object) -> None:
            self.args = args
            self.kwargs = kwargs


__all__ = ["MainWindow"]
