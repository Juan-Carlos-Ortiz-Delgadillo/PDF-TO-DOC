"""Tarjeta con información del PDF seleccionado."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget


class FileDetailsCard(QFrame):
    """Muestra el nombre, ruta, tamaño y estado analítico del PDF."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumHeight(160)
        self._icon = QLabel("📄")
        self._icon.setStyleSheet("font-size: 28px;")
        self._icon.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._name = QLabel("Sin archivo seleccionado")
        self._name.setStyleSheet("font-weight: 600; font-size: 15px;")
        self._name.setWordWrap(True)
        self._path = QLabel("Aún no hay un PDF cargado.")
        self._path.setWordWrap(True)
        self._meta = QLabel("Tamaño: —  •  Páginas: —")
        self._meta.setWordWrap(True)
        self._status = QLabel("Estado: pendiente de análisis")
        self._status.setWordWrap(True)
        self._status.setObjectName("status")

        left = QVBoxLayout()
        left.setSpacing(4)
        left.addWidget(self._name)
        left.addWidget(self._path)
        left.addWidget(self._meta)
        left.addWidget(self._status)

        container = QHBoxLayout(self)
        container.setContentsMargins(12, 12, 12, 12)
        container.setSpacing(12)
        container.addWidget(self._icon)
        container.addLayout(left, 1)
        self.setLayout(container)

    def update_from_pdf(
        self,
        path: str | Path,
        *,
        size_bytes: int | None,
        page_count: int | None,
        status: str,
    ) -> None:
        pdf_path = Path(path)
        self._name.setText(pdf_path.name)
        self._path.setText(str(pdf_path))
        size_label = self._format_size(size_bytes) if size_bytes is not None else "—"
        pages_label = str(page_count) if page_count is not None else "—"
        self._meta.setText(f"Tamaño: {size_label}  •  Páginas: {pages_label}")
        self._status.setText(f"Estado: {status}")

    def clear(self) -> None:
        self._name.setText("Sin archivo seleccionado")
        self._path.setText("Aún no hay un PDF cargado.")
        self._meta.setText("Tamaño: —  •  Páginas: —")
        self._status.setText("Estado: pendiente de análisis")

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        units = ["B", "KB", "MB", "GB"]
        value = float(size_bytes)
        for unit in units:
            if value < 1024.0 or unit == units[-1]:
                if unit == "B":
                    return f"{int(value)} {unit}"
                return f"{value:.1f} {unit}"
            value /= 1024.0
        return "0 B"
