"""Ventana principal de la aplicación PDF2Word."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core.config import Theme
from app.models import ConversionConfig, PageSelection
from app.services import ConversionService
from app.services.settings_service import SettingsService
from app.ui.components.drop_zone import DropZone
from app.ui.components.file_card import FileDetailsCard
from app.ui.components.progress_card import ProgressCard
from app.ui.dialogs.about_dialog import AboutDialog
from app.ui.dialogs.settings_dialog import SettingsDialog


class PdfAnalysisThread(QThread):
    finished = Signal(object, str)

    def __init__(self, path: str, *, service: ConversionService) -> None:
        super().__init__()
        self._path = path
        self._service = service

    def run(self) -> None:
        try:
            info = self._service.analyze(Path(self._path))
            self.finished.emit(info, "")
        except Exception as exc:  # pragma: no cover - manejo de sesión de UI
            self.finished.emit(None, str(exc))


class ConversionThread(QThread):
    finished = Signal(object, str)

    def __init__(self, *, service: ConversionService, config: ConversionConfig) -> None:
        super().__init__()
        self._service = service
        self._config = config
        self.cancel_requested = False

    def run(self) -> None:
        try:
            if self.cancel_requested:
                self.finished.emit(None, "cancelado")
                return
            result = self._service.convert(self._config)
            self.finished.emit(result, "")
        except Exception as exc:  # pragma: no cover - manejo de sesión de UI
            self.finished.emit(None, str(exc))


class MainWindow(QMainWindow):
    """Ventana principal del convertidor PDF2Word."""

    def __init__(
        self,
        *,
        settings_service: SettingsService | None = None,
        conversion_service: ConversionService | None = None,
    ) -> None:
        super().__init__()
        self.settings_service = settings_service or SettingsService()
        self.settings = self.settings_service.load()
        self.conversion_service = conversion_service or ConversionService()
        self.current_pdf_path: Path | None = None
        self.current_pdf_info: Any | None = None
        self.analysis_thread: PdfAnalysisThread | None = None
        self.conversion_thread: ConversionThread | None = None
        self._cancel_requested = False
        self._apply_stylesheet()
        self._build_ui()
        self._apply_saved_settings()
        self._setup_page_selection()
        self._set_idle_state()

    def _build_ui(self) -> None:
        self.setWindowTitle("PDF2Word - Convertidor de PDF a Word")
        self.resize(1000, 720)
        self.setMinimumSize(760, 540)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        central_widget = QWidget(self)
        central_widget.setObjectName("central-panel")
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)
        app_title = QLabel("PDF2Word")
        app_title.setObjectName("app-title")
        app_title.setStyleSheet("font-size: 22px; font-weight: 700;")
        app_title.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        subtitle = QLabel("Convierte tus documentos PDF a Word fácilmente")
        subtitle.setObjectName("app-subtitle")
        subtitle.setWordWrap(True)
        subtitle.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.config_button = _tool_button("⚙️", "Configuración")
        self.about_button = _tool_button("ℹ️", "Acerca de")
        self.config_button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.about_button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.config_button.clicked.connect(self._open_settings)
        self.about_button.clicked.connect(self._open_about)

        top_row.addWidget(app_title)
        top_row.addWidget(subtitle)
        top_row.addWidget(self.config_button)
        top_row.addWidget(self.about_button)
        root_layout.addLayout(top_row)

        self.drop_zone = DropZone(self)
        self.drop_zone.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.drop_zone.fileSelected.connect(self._on_pdf_selected)
        root_layout.addWidget(self.drop_zone)

        self.file_card = FileDetailsCard(self)
        self.file_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        root_layout.addWidget(self.file_card)

        output_box = QWidget(self)
        output_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        output_layout = QGridLayout(output_box)
        output_layout.setContentsMargins(12, 12, 12, 12)
        output_layout.setSpacing(10)
        output_layout.addWidget(QLabel("<b>Configuración de salida</b>"), 0, 0, 1, 2)

        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("Selecciona la carpeta de destino")
        self.output_dir_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        choose_dir = _secondary_action_button("Examinar...")
        choose_dir.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        choose_dir.clicked.connect(self._choose_output_directory)
        output_layout.addWidget(self.output_dir_edit, 1, 0)
        output_layout.addWidget(choose_dir, 1, 1)

        output_name_label = QLabel("Nombre del archivo Word")
        output_name_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.output_name_edit = QLineEdit()
        self.output_name_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        output_layout.addWidget(output_name_label, 2, 0)
        output_layout.addWidget(self.output_name_edit, 2, 1)

        self.reset_output_button = _secondary_action_button(
            "Restaurar valores predeterminados"
        )
        self.reset_output_button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.reset_output_button.clicked.connect(self._restore_default_output)
        output_layout.addWidget(self.reset_output_button, 3, 0, 1, 2)
        root_layout.addWidget(output_box)

        options_box = QWidget(self)
        options_layout = QVBoxLayout(options_box)
        options_layout.setContentsMargins(12, 12, 12, 12)
        options_layout.setSpacing(10)
        options_layout.addWidget(QLabel("<b>Opciones de conversión</b>"))
        page_group = QButtonGroup(self)

        self.all_pages_radio = QRadioButton("Todas las páginas")
        self.range_radio = QRadioButton("Rango de páginas")
        self.specific_radio = QRadioButton("Páginas específicas")
        page_group.addButton(self.all_pages_radio)
        page_group.addButton(self.range_radio)
        page_group.addButton(self.specific_radio)
        page_group.setId(self.all_pages_radio, 0)
        page_group.setId(self.range_radio, 1)
        page_group.setId(self.specific_radio, 2)

        self.all_pages_radio.toggled.connect(self._update_pages_controls)
        self.range_radio.toggled.connect(self._update_pages_controls)
        self.specific_radio.toggled.connect(self._update_pages_controls)

        options_layout.addWidget(self.all_pages_radio)
        options_layout.addWidget(self.range_radio)
        range_layout = QHBoxLayout()
        range_layout.setSpacing(8)
        self.range_from = QSpinBox()
        self.range_from.setMinimum(1)
        self.range_from.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.range_to = QSpinBox()
        self.range_to.setMinimum(1)
        self.range_to.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        range_layout.addWidget(QLabel("Desde"))
        range_layout.addWidget(self.range_from)
        range_layout.addWidget(QLabel("Hasta"))
        range_layout.addWidget(self.range_to)
        range_layout.addStretch(1)
        options_layout.addLayout(range_layout)

        options_layout.addWidget(self.specific_radio)
        self.pages_edit = QLineEdit("1, 3, 5-8")
        self.pages_edit.setPlaceholderText("Ejemplo: 1, 3, 5-8")
        self.pages_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        options_layout.addWidget(self.pages_edit)

        self.ocr_checkbox = _checkbox("Detectar y utilizar OCR cuando sea necesario")
        self.ocr_checkbox.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        options_layout.addWidget(self.ocr_checkbox)
        root_layout.addWidget(options_box)

        self.progress_card = ProgressCard(self)
        self.progress_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        root_layout.addWidget(self.progress_card)

        result_row = QHBoxLayout()
        result_row.setSpacing(8)
        self.result_label = QLabel("")
        self.result_label.setWordWrap(True)
        self.result_path = QLabel("")
        self.result_path.setWordWrap(True)
        self.result_path.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.open_word_button = _secondary_action_button("Abrir Word")
        self.open_folder_button = _secondary_action_button("Abrir carpeta")
        self.open_word_button.clicked.connect(self._open_word_result)
        self.open_folder_button.clicked.connect(self._open_output_directory)
        self.open_word_button.setVisible(False)
        self.open_folder_button.setVisible(False)
        result_row.addWidget(self.result_label)
        result_row.addWidget(self.result_path)
        result_row.addWidget(self.open_word_button)
        result_row.addWidget(self.open_folder_button)
        root_layout.addLayout(result_row)

        actions_row = QHBoxLayout()
        actions_row.setContentsMargins(0, 0, 0, 0)
        actions_row.setSpacing(10)
        self.convert_button = _primary_action_button("Convertir a Word")
        self.clean_button = _secondary_action_button("Limpiar")
        self.quit_button = _secondary_action_button("Salir")
        self.convert_button.clicked.connect(self._start_conversion)
        self.clean_button.clicked.connect(self._clear_form)
        self.quit_button.clicked.connect(self.close)
        self.convert_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.clean_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.quit_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        actions_row.addWidget(self.clean_button)
        actions_row.addWidget(self.quit_button)
        actions_row.addStretch(1)
        actions_row.addWidget(self.convert_button)
        root_layout.addLayout(actions_row)

        scroll_area.setWidget(central_widget)
        self.setCentralWidget(scroll_area)

    def _apply_stylesheet(self, theme: Theme | None = None) -> None:
        stylesheet_path = Path(__file__).with_name("styles.qss")
        stylesheet = stylesheet_path.read_text(encoding="utf-8")
        active_theme = theme or self.settings.theme
        if active_theme is Theme.DARK:
            dark_stylesheet_path = stylesheet_path.with_name("styles_dark.qss")
            stylesheet += "\n" + dark_stylesheet_path.read_text(encoding="utf-8")
        self.setStyleSheet(stylesheet)

    def _apply_saved_settings(self) -> None:
        self.output_dir_edit.setText(str(self.settings.output_directory))
        self.ocr_checkbox.setChecked(self.settings.ocr_enabled)
        self.output_name_edit.setText(self._suggest_output_name())

    def _setup_page_selection(self) -> None:
        self.all_pages_radio.setChecked(True)
        self._update_pages_controls()

    def _update_pages_controls(self) -> None:
        range_enabled = self.range_radio.isChecked()
        specific_enabled = self.specific_radio.isChecked()
        self.range_from.setEnabled(range_enabled)
        self.range_to.setEnabled(range_enabled)
        self.pages_edit.setEnabled(specific_enabled)

    def _set_idle_state(self) -> None:
        self.progress_card.set_idle()
        self.file_card.clear()
        self.result_label.setText("")
        self.result_path.setText("")
        self.open_word_button.setVisible(False)
        self.open_folder_button.setVisible(False)
        self.convert_button.setEnabled(False)

    def _on_pdf_selected(self, file_name: str) -> None:
        pdf_path = Path(file_name)
        if not pdf_path.exists() or not pdf_path.is_file():
            QMessageBox.warning(
                self, "Archivo no válido", "El archivo seleccionado no existe o no es legible."
            )
            return
        try:
            self.conversion_service.analyzer.validate_input(pdf_path)
        except Exception as exc:  # pragma: no cover - validación del dominio
            QMessageBox.warning(self, "PDF no válido", str(exc))
            return
        self.current_pdf_path = pdf_path
        self._start_analysis(pdf_path)

    def _start_analysis(self, pdf_path: Path) -> None:
        self.progress_card.set_state(
            "Analizando PDF...", "Revisando páginas y contenido del documento.", indeterminate=True
        )
        self.analysis_thread = PdfAnalysisThread(str(pdf_path), service=self.conversion_service)
        self.analysis_thread.finished.connect(self._on_pdf_analysis_finished)
        self.analysis_thread.start()

    def _on_pdf_analysis_finished(self, pdf_info: Any, error: str) -> None:
        self.analysis_thread = None
        if pdf_info is None:
            self.current_pdf_info = None
            QMessageBox.warning(self, "Error de análisis", error or "No se pudo analizar el PDF.")
            self.progress_card.set_state(
                "Error en la conversión", "No fue posible analizar el archivo PDF."
            )
            return
        self.current_pdf_info = pdf_info
        page_count = int(getattr(pdf_info, "page_count", 0))
        self.file_card.update_from_pdf(
            pdf_info.path,
            size_bytes=int(getattr(pdf_info, "file_size", 0)),
            page_count=page_count,
            status="listo para convertir",
        )
        self.output_name_edit.setText(self._suggest_output_name(pdf_info.path))
        self.range_from.setMaximum(max(page_count, 1))
        self.range_to.setMaximum(max(page_count, 1))
        self.range_to.setValue(max(page_count, 1))
        self.progress_card.set_state(
            "Listo para convertir", "El PDF está validado y listo para procesarse.", value=100
        )
        self.convert_button.setEnabled(True)

    def _suggest_output_name(self, path: Path | None = None) -> str:
        source_path = path or self.current_pdf_path
        if source_path is None:
            return "documento.docx"
        return f"{Path(source_path).stem}.docx"

    def _choose_output_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar carpeta de salida",
            self.output_dir_edit.text() or str(Path.home()),
        )
        if directory:
            self.output_dir_edit.setText(directory)

    def _restore_default_output(self) -> None:
        self.output_dir_edit.setText(str(self.settings.output_directory))
        self.output_name_edit.setText(self._suggest_output_name())

    def _build_conversion_config(self) -> ConversionConfig:
        if self.current_pdf_path is None:
            raise ValueError("No hay un PDF seleccionado.")
        selected_pages = self._selected_pages()
        output_directory = Path(self.output_dir_edit.text()).expanduser()
        output_name = self.output_name_edit.text().strip()
        if not output_name:
            raise ValueError("El nombre del archivo Word no puede estar vacío.")
        output_name = Path(output_name).name
        if not output_name.lower().endswith(".docx"):
            output_name = f"{output_name}.docx"
        output_path = output_directory / output_name
        return ConversionConfig(
            input_path=self.current_pdf_path,
            output_path=output_path,
            page_selection=selected_pages,
            use_ocr=self.ocr_checkbox.isChecked(),
            ocr_language=self.settings.ocr_language,
            multiprocessing_enabled=self.settings.multiprocessing_enabled,
            overwrite_confirmed=False,
        )

    def _selected_pages(self) -> PageSelection:
        if self.current_pdf_info is None:
            return PageSelection.all()
        total_pages = int(self.current_pdf_info.page_count)
        if self.all_pages_radio.isChecked():
            return PageSelection.all()
        if self.range_radio.isChecked():
            start = int(self.range_from.value())
            end = int(self.range_to.value())
            if start > end or start < 1 or end > total_pages:
                raise ValueError("El rango de páginas no es válido.")
            return PageSelection.range(start, end)
        text = self.pages_edit.text().strip()
        if not text:
            raise ValueError("Introduce al menos una página válida.")
        return PageSelection.parse(text, total_pages)

    def _start_conversion(self) -> None:
        if self.current_pdf_path is None:
            QMessageBox.warning(
                self, "Archivo no seleccionado", "Debes seleccionar un PDF antes de convertir."
            )
            return
        try:
            config = self._build_conversion_config()
        except ValueError as exc:
            QMessageBox.warning(self, "Entrada inválida", str(exc))
            return

        output_path = config.output_path
        if output_path.exists():
            reply = QMessageBox(self)
            reply.setWindowTitle("Archivo existente")
            reply.setText(f"Ya existe el archivo:\n{output_path}\n\n¿Deseas reemplazarlo?")
            reply.addButton("Reemplazar", QMessageBox.ButtonRole.AcceptRole)
            choose_button = reply.addButton(
                "Elegir otro nombre",
                QMessageBox.ButtonRole.ActionRole,
            )
            cancel_button = reply.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
            reply.exec()
            if reply.clickedButton() is cancel_button:
                return
            if reply.clickedButton() is choose_button:
                self.output_name_edit.setFocus()
                return
            config = ConversionConfig(
                input_path=config.input_path,
                output_path=output_path,
                page_selection=config.page_selection,
                use_ocr=config.use_ocr,
                ocr_language=config.ocr_language,
                multiprocessing_enabled=config.multiprocessing_enabled,
                overwrite_confirmed=True,
            )

        self._cancel_requested = False
        self.progress_card.set_state(
            "Preparando conversión...",
            "Validando entrada y salida antes de iniciar.",
            value=25,
            show_cancel=True,
        )
        self.convert_button.setEnabled(False)
        self.conversion_thread = ConversionThread(service=self.conversion_service, config=config)
        self.conversion_thread.finished.connect(self._on_conversion_finished)
        self.conversion_thread.start()

    def _on_conversion_finished(self, result: object, error: str) -> None:
        self.conversion_thread = None
        self._cancel_requested = False
        self.progress_card.set_cancel_visible(False)
        if result is None:
            reason = error or "Error durante la conversión."
            self.progress_card.set_state("Error en la conversión", reason)
            QMessageBox.critical(self, "Error de conversión", reason)
            self.convert_button.setEnabled(True)
            return
        output_path = Path(result.output_path)
        self.result_label.setText("Conversión completada correctamente")
        self.result_path.setText(str(output_path))
        self.open_word_button.setVisible(True)
        self.open_folder_button.setVisible(True)
        self.progress_card.set_state(
            "Conversión completada", f"Documento generado en {output_path}", value=100
        )
        self.convert_button.setEnabled(True)

    def _open_word_result(self) -> None:
        if self.current_pdf_path is None:
            return
        output_path = Path(self.output_name_edit.text())
        if not output_path.is_absolute():
            output_path = Path(self.output_dir_edit.text()) / output_path
        if output_path.exists():
            QDesktopServices.openUrl(output_path.as_uri())
        else:
            QMessageBox.warning(
                self,
                "Documento no disponible",
                "El archivo DOCX aún no existe o no pudo validarse.",
            )

    def _open_output_directory(self) -> None:
        output_dir = Path(self.output_dir_edit.text()).expanduser()
        if output_dir.exists():
            QDesktopServices.openUrl(output_dir.as_uri())
        else:
            QMessageBox.warning(
                self, "Carpeta no disponible", "La carpeta de salida no existe o no es accesible."
            )

    def _open_settings(self) -> None:
        settings_dialog = SettingsDialog(self.settings, self.settings_service, self)
        settings_dialog.themePreviewChanged.connect(self._preview_theme)
        settings_dialog.rejected.connect(self._restore_saved_theme)
        if settings_dialog.exec() == SettingsDialog.DialogCode.Accepted:
            self.settings = self.settings_service.load()
            self._apply_stylesheet()
            self.output_dir_edit.setText(str(self.settings.output_directory))
            self.ocr_checkbox.setChecked(self.settings.ocr_enabled)

    def _preview_theme(self, theme: str) -> None:
        self._apply_stylesheet(Theme.coerce(theme))

    def _restore_saved_theme(self) -> None:
        self._apply_stylesheet(self.settings.theme)

    def _open_about(self) -> None:
        AboutDialog(self).exec()

    def _clear_form(self) -> None:
        self.current_pdf_path = None
        self.current_pdf_info = None
        self.file_card.clear()
        self.output_name_edit.setText(self._suggest_output_name())
        self.result_label.setText("")
        self.result_path.setText("")
        self.open_word_button.setVisible(False)
        self.open_folder_button.setVisible(False)
        self.convert_button.setEnabled(False)
        self.progress_card.set_idle()

    def closeEvent(self, event: Any) -> None:
        if self.conversion_thread is not None and self.conversion_thread.isRunning():
            reply = QMessageBox.question(
                self,
                "Conversión en curso",
                "Hay una conversión activa. ¿Deseas cancelar y cerrar la aplicación?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.conversion_thread.cancel_requested = True
                self.progress_card.set_state(
                    "Cancelando...", "Se está cerrando la operación de forma segura."
                )
                event.ignore()
                return
            event.ignore()
            return
        super().closeEvent(event)


def _checkbox(label: str) -> object:
    checkbox = __import__("PySide6.QtWidgets", fromlist=["QCheckBox"]).QCheckBox(label)
    return checkbox


def _tool_button(icon: str, label: str):
    from PySide6.QtWidgets import QPushButton

    button = QPushButton(f"{icon} {label}")
    button.setObjectName("tool-button")
    return button


def _primary_action_button(label: str):
    from PySide6.QtWidgets import QPushButton

    button = QPushButton(label)
    button.setObjectName("primary")
    return button


def _secondary_action_button(label: str):
    from PySide6.QtWidgets import QPushButton

    button = QPushButton(label)
    button.setObjectName("secondary")
    return button


def _size_policy():
    from PySide6.QtWidgets import QSizePolicy

    return QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
