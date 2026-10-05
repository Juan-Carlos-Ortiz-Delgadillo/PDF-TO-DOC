"""Diálogo de configuración de la aplicación."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.config import AppSettings, Theme
from app.services.settings_service import SettingsService


class SettingsDialog(QDialog):
    """Permite ajustar opciones locales básicas de la aplicación."""

    def __init__(
        self,
        settings: AppSettings,
        settings_service: SettingsService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.settings_service = settings_service or SettingsService()
        self.settings = settings
        self.setWindowTitle("Configuración")
        self.resize(420, 260)

        form = QFormLayout()

        self.theme_combo = QComboBox()
        self.theme_combo.addItems([Theme.SYSTEM.value, Theme.LIGHT.value, Theme.DARK.value])
        self.theme_combo.setCurrentText(self.settings.theme.value)

        self.output_dir = QLineEdit(str(self.settings.output_directory))
        self.output_dir.setReadOnly(True)
        browse = QPushButton("Examinar...")
        browse.clicked.connect(self._choose_output_directory)
        directory_row = QWidget()
        directory_layout = QHBoxLayout(directory_row)
        directory_layout.addWidget(self.output_dir)
        directory_layout.addWidget(browse)

        self.ocr_enabled = QCheckBox("Activar OCR automático")
        self.ocr_enabled.setChecked(self.settings.ocr_enabled)

        self.ocr_language = QComboBox()
        self.ocr_language.addItems(["spa", "eng", "fra", "deu"])
        self.ocr_language.setCurrentText(self.settings.ocr_language)

        form.addRow(QLabel("Tema:"), self.theme_combo)
        form.addRow(QLabel("Carpeta salida:"), directory_row)
        form.addRow(QLabel("OCR:"), self.ocr_enabled)
        form.addRow(QLabel("Idioma OCR:"), self.ocr_language)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _choose_output_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            "Selecciona una carpeta de salida",
            str(self.output_dir.text() or Path.home()),
        )
        if directory:
            self.output_dir.setText(directory)

    def _save(self) -> None:
        self.settings = AppSettings(
            theme=self.theme_combo.currentText(),
            overwrite_policy=self.settings.overwrite_policy,
            ocr_enabled=self.ocr_enabled.isChecked(),
            ocr_language=self.ocr_language.currentText(),
            output_directory=self.output_dir.text() or self.settings.output_directory,
            multiprocessing_enabled=self.settings.multiprocessing_enabled,
            default_page_selection=self.settings.default_page_selection,
        )
        self.settings_service.save(self.settings)
        self.accept()
