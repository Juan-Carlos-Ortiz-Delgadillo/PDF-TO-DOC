"""Módulos de interfaz de PDF2Word."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.ui.main_window import MainWindow


def __getattr__(name: str) -> type[MainWindow]:
    if name != "MainWindow":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from app.ui.main_window import MainWindow

    return MainWindow


__all__ = ["MainWindow"]
