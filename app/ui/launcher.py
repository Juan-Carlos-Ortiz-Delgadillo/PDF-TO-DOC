"""Arranque de dos fases para mostrar una ventana antes de cargar la UI completa."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPaintEvent
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox, QVBoxLayout, QWidget


class StartupWindow(QWidget):
    """Ventana mínima que se pinta mientras se prepara la interfaz principal."""

    def __init__(self, *, marker_path: Path | None = None) -> None:
        super().__init__(None, Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint)
        self._marker_path = marker_path
        self.setWindowTitle("PDF2Word")
        self.setFixedSize(360, 112)
        self.setStyleSheet(
            "QWidget { background: #f2f1ed; color: #25282b; }"
            "QLabel#title { font-size: 22px; font-weight: 700; }"
            "QLabel#status { color: #60666c; font-size: 13px; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 18)
        title = QLabel("PDF2Word")
        title.setObjectName("title")
        status = QLabel("Preparando el convertidor…")
        status.setObjectName("status")
        layout.addWidget(title)
        layout.addWidget(status)

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        if self._marker_path is not None:
            marker_path = self._marker_path
            self._marker_path = None
            marker_path.write_text(f"{time.monotonic_ns()}\n", encoding="ascii")


def main() -> int:
    application = QApplication.instance() or QApplication(sys.argv)
    marker_path = os.environ.get("PDF2WORD_STARTUP_MARKER")
    startup_window = StartupWindow(
        marker_path=Path(marker_path) if marker_path else None,
    )
    startup_window.show()
    application.processEvents()
    ready_marker_path = os.environ.get("PDF2WORD_READY_MARKER")

    main_window: QWidget | None = None

    def show_main_window() -> None:
        nonlocal main_window
        try:
            from app.ui.main_window import MainWindow

            main_window = MainWindow()
            main_window.show()
            application.processEvents()
            if ready_marker_path:
                Path(ready_marker_path).write_text(
                    f"{time.monotonic_ns()}\n",
                    encoding="ascii",
                )
            startup_window.close()
        except Exception as error:  # pragma: no cover - error is shown to the user
            startup_window.close()
            message = f"No se pudo iniciar PDF2Word: {type(error).__name__}: {error}"
            if ready_marker_path:
                print(message, file=sys.stderr)
                application.quit()
                return
            QMessageBox.critical(
                None,
                "No se pudo iniciar PDF2Word",
                message,
            )
            application.quit()

    QTimer.singleShot(0, show_main_window)
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
