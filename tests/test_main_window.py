from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.components.drop_zone import DropZone
from app.ui.main_window import MainWindow


def test_main_window_starts() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    assert window.windowTitle() == "PDF2Word - Convertidor de PDF a Word"
    assert window.size().width() >= 800
    app.processEvents()


def test_drop_zone_accepts_only_pdf() -> None:
    assert DropZone._is_pdf_path("/tmp/sample.pdf") is True
    assert DropZone._is_pdf_path("/tmp/sample.txt") is False


def test_output_name_suggestion() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    assert window._suggest_output_name(Path("/tmp/informe.pdf")) == "informe.docx"
    app.processEvents()
