"""Arranque de dos fases para mostrar una ventana antes de cargar la UI completa."""

from __future__ import annotations

import importlib
import logging
import os
import sys
import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPaintEvent
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox, QVBoxLayout, QWidget

_CONVERSION_MODULES = (
    "pdf2docx",
    "fitz",
    "docx",
    "cv2",
    "numpy",
    "fontTools",
    "lxml",
    "fire",
)


def _run_conversion_smoke_test(arguments: list[str]) -> int | None:
    if len(arguments) < 2 or arguments[1] != "--self-test-conversion":
        return None
    if len(arguments) != 4:
        print(
            "Uso de prueba interna: --self-test-conversion <entrada.pdf> <salida.docx>",
            file=sys.stderr,
        )
        return 2

    try:
        for module_name in _CONVERSION_MODULES:
            importlib.import_module(module_name)

        from app.bootstrap import bootstrap_application
        from app.models import ConversionConfig, PageSelection
        from app.services.conversion_service import ConversionService

        bootstrap_application()
        source_path = Path(arguments[2])
        output_path = Path(arguments[3])
        service = ConversionService()
        info = service.analyze(source_path)
        result = service.convert(
            ConversionConfig(
                input_path=source_path,
                output_path=output_path,
                page_selection=PageSelection.all(),
                use_ocr=False,
                ocr_language="spa",
                multiprocessing_enabled=False,
                overwrite_confirmed=True,
            )
        )
        if not result.output_path.is_file() or result.output_path.stat().st_size <= 0:
            raise RuntimeError("La conversión no produjo un DOCX con contenido.")
        print(
            f"Conversión verificada: {info.page_count} página(s), "
            f"{result.output_path.stat().st_size} bytes."
        )
        return 0
    except Exception:
        logging.exception("Falló la prueba de conversión empaquetada.")
        return 1


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
    smoke_test_result = _run_conversion_smoke_test(sys.argv)
    if smoke_test_result is not None:
        return smoke_test_result

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
            from app.bootstrap import bootstrap_application

            bootstrap_application()
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
            logging.exception("No se pudo iniciar la interfaz principal.")
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
