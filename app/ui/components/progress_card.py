"""Tarjeta de progreso y estado de la conversión."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class ProgressCard(QFrame):
    """Muestra la etapa actual, estado y botón cancelar."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumHeight(180)

        self._icon = QLabel("⏳")
        self._icon.setStyleSheet("font-size: 28px;")
        self._icon.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._title = QLabel("Esperando archivo")
        self._title.setStyleSheet("font-size: 18px; font-weight: 700;")
        self._title.setWordWrap(True)
        self._message = QLabel("Selecciona un PDF para comenzar.")
        self._message.setWordWrap(True)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._cancel = QPushButton("Cancelar")
        self._cancel.setVisible(False)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(6)
        text_layout.addWidget(self._title)
        text_layout.addWidget(self._message)
        text_layout.addWidget(self._progress)

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 12, 12, 12)
        row.setSpacing(12)
        row.addWidget(self._icon)
        row.addLayout(text_layout, 1)
        row.addWidget(self._cancel)
        row.setStretch(1, 1)
        self.setLayout(row)

    def set_state(
        self,
        title: str,
        message: str,
        *,
        value: int | None = None,
        indeterminate: bool = False,
        show_cancel: bool = False,
    ) -> None:
        self._title.setText(title)
        self._message.setText(message)
        self._cancel.setVisible(show_cancel)

        if value is None:
            self._progress.setRange(0, 0)
            self._progress.setValue(0)
        else:
            self._progress.setRange(0, 100)
            self._progress.setValue(value)
            if indeterminate:
                self._progress.setRange(0, 0)

    def set_idle(self) -> None:
        self.set_state(
            "Esperando archivo", "Selecciona un PDF para comenzar.", value=0, indeterminate=False
        )

    def set_cancel_visible(self, visible: bool) -> None:
        self._cancel.setVisible(visible)
