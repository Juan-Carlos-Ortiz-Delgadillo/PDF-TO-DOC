"""Zona de arrastrar y soltar un PDF."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent
from PySide6.QtWidgets import QFileDialog, QFrame, QLabel, QPushButton, QSizePolicy, QVBoxLayout


class DropZone(QFrame):
    """Panel grande para seleccionar PDFs por botón o arrastre."""

    fileSelected = Signal(str)

    def __init__(self, parent: object | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._drag_active = False

        self._icon = QLabel("PDF")
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon.setStyleSheet("font-size: 36px; font-weight: 700; color: #d93025;")

        self._title = QLabel("Selecciona tu archivo PDF")
        self._title.setStyleSheet("font-size: 20px; font-weight: 600;")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._subtitle = QLabel("Arrastra un PDF aquí o selecciónalo desde tu equipo")
        self._subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._subtitle.setWordWrap(True)

        self._button = QPushButton("Seleccionar PDF")
        self._button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._button.clicked.connect(self._open_file_dialog)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._icon)
        layout.addWidget(self._title)
        layout.addWidget(self._subtitle)
        layout.addWidget(self._button)
        self.setLayout(layout)
        self._apply_base_styles()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self._is_valid_pdf_drag(event):
            event.acceptProposedAction()
            self._drag_active = True
            self._apply_drag_styles()
        else:
            event.ignore()

    def dragLeaveEvent(self, event: object) -> None:
        self._drag_active = False
        self._apply_base_styles()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if not urls:
            event.ignore()
            return
        for url in urls:
            path = url.toLocalFile()
            if path and self._is_pdf_path(path):
                event.acceptProposedAction()
                self.fileSelected.emit(path)
                self._drag_active = False
                self._apply_base_styles()
                return
        event.ignore()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._open_file_dialog()
        super().mousePressEvent(event)

    def _open_file_dialog(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar un archivo PDF",
            str(Path.home()),
            "Archivos PDF (*.pdf)",
        )
        if file_name:
            self.fileSelected.emit(file_name)

    @staticmethod
    def _is_pdf_path(path: str) -> bool:
        return Path(path).suffix.lower() == ".pdf"

    @staticmethod
    def _is_valid_pdf_drag(event: QDragEnterEvent) -> bool:
        mime_data = event.mimeData()
        if mime_data is None:
            return False
        for url in mime_data.urls():
            if url.toLocalFile() and DropZone._is_pdf_path(url.toLocalFile()):
                return True
        return False

    def _apply_base_styles(self) -> None:
        self.setStyleSheet(
            "QFrame { border: 2px dashed #d0d7de; border-radius: 16px; background: #f8f9fb; }"
        )

    def _apply_drag_styles(self) -> None:
        self.setStyleSheet(
            "QFrame { border: 2px solid #1f6feb; border-radius: 16px; background: #e9f2ff; }"
        )
