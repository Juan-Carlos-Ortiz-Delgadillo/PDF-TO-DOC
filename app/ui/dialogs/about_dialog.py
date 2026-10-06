"""Diálogo de información de la aplicación."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout

APP_VERSION = "1.0.2"


class AboutDialog(QDialog):
    """Muestra nombre, versión y descripción de la aplicación."""

    def __init__(self, parent: object | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Acerca de PDF2Word")
        self.resize(360, 200)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>PDF2Word</h2>"))
        layout.addWidget(QLabel(f"Versión: {APP_VERSION}"))
        layout.addWidget(
            QLabel("Convierte tus documentos PDF a Word de forma local y segura.")
        )
        layout.addWidget(
            QLabel(
                "Sin depender de servicios externos ni del almacenamiento en la nube."
            )
        )
