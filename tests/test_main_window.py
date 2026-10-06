from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QDialogButtonBox, QPushButton

from app.core.config import AppSettings, ConfigRepository, Theme
from app.services.settings_service import SettingsService
from app.ui.components.drop_zone import DropZone
from app.ui.dialogs.settings_dialog import SettingsDialog
from app.ui.main_window import MainWindow


def test_main_window_starts() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    assert window.windowTitle() == "PDF2Word - Convertidor de PDF a Word"
    assert window.size().width() >= 800
    app.processEvents()
    assert "QLineEdit:disabled" in window.styleSheet()
    assert window.drop_zone.maximumHeight() <= 184
    assert window.progress_card.maximumHeight() <= 80
    assert window.clean_button.objectName() == "secondary"
    assert window.convert_button.objectName() == "primary"
    assert window.clean_button.mapTo(window, window.clean_button.rect().topLeft()).x() < (
        window.convert_button.mapTo(window, window.convert_button.rect().topLeft()).x()
    )
    assert "#f2f1ed" in window.styleSheet()
    select_button = window.drop_zone.findChild(QPushButton, "secondary")
    assert select_button is not None
    assert window.drop_zone.rect().contains(select_button.geometry())
    assert window.drop_zone.height() - select_button.geometry().bottom() >= 12


def test_dark_theme_is_applied_from_saved_settings(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    settings_service = SettingsService(ConfigRepository(tmp_path / "settings.json"))
    settings_service.save(AppSettings(theme=Theme.DARK))

    window = MainWindow(settings_service=settings_service)

    assert "#202326" in window.styleSheet()
    assert "#e6e8eb" in window.styleSheet()
    app.processEvents()


def test_night_mode_can_be_selected_and_saved(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    settings_service = SettingsService(ConfigRepository(tmp_path / "settings.json"))
    dialog = SettingsDialog(settings_service.load(), settings_service)

    assert dialog.theme_combo.findData(Theme.DARK.value) >= 0
    dialog.theme_combo.setCurrentIndex(dialog.theme_combo.findData(Theme.DARK.value))
    dialog._save()

    assert settings_service.load().theme is Theme.DARK
    app.processEvents()


def test_settings_dialog_action_buttons_are_distinguishable(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    settings_service = SettingsService(ConfigRepository(tmp_path / "settings.json"))
    window = MainWindow(settings_service=settings_service)
    dialog = SettingsDialog(window.settings, settings_service, window)
    buttons = dialog.findChild(QDialogButtonBox)

    assert buttons is not None
    save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
    cancel_button = buttons.button(QDialogButtonBox.StandardButton.Cancel)
    assert save_button is not None
    assert cancel_button is not None
    assert save_button.objectName() == "primary"
    assert cancel_button.objectName() == "secondary"
    assert "QPushButton#primary" in window.styleSheet()
    assert "QPushButton#secondary" in window.styleSheet()
    app.processEvents()


def test_theme_preview_updates_immediately_and_cancel_restores(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    settings_service = SettingsService(ConfigRepository(tmp_path / "settings.json"))
    window = MainWindow(settings_service=settings_service)
    dialog = SettingsDialog(window.settings, settings_service, window)
    dialog.themePreviewChanged.connect(window._preview_theme)
    dialog.rejected.connect(window._restore_saved_theme)

    dialog.theme_combo.setCurrentIndex(dialog.theme_combo.findData(Theme.DARK.value))
    assert "#202326" in window.styleSheet()

    dialog.reject()

    assert "#202326" not in window.styleSheet()
    assert "#f2f1ed" in window.styleSheet()
    assert settings_service.load().theme is Theme.SYSTEM
    app.processEvents()


def test_drop_zone_accepts_only_pdf() -> None:
    assert DropZone._is_pdf_path("/tmp/sample.pdf") is True
    assert DropZone._is_pdf_path("/tmp/sample.txt") is False


def test_output_name_suggestion() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    assert window._suggest_output_name(Path("/tmp/informe.pdf")) == "informe.docx"
    app.processEvents()
