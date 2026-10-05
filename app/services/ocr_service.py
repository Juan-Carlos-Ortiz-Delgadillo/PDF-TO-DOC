"""Servicio de OCR opcional para documentos que requieren OCR local."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from app.core.exceptions import OCRDependencyError, OCRProcessingError


class OCRService:
    """Ejecuta OCR local para PDF usando OCRmyPDF cuando está disponible."""

    def __init__(self, *, language: str = "spa") -> None:
        self.language = language.strip() or "spa"

    def ensure_available(self) -> None:
        if shutil.which("ocrmypdf") is None:
            raise OCRDependencyError(
                "OCR local no disponible: falta OCRmyPDF.",
                diagnostic_message="No se encontró el comando 'ocrmypdf' en PATH.",
                error_code="ocr_ocrmypdf_missing",
            )

    def run(self, input_path: str | Path, *, output_path: str | Path | None = None) -> Path:
        self.ensure_available()
        source = Path(input_path)
        if not source.exists():
            raise OCRProcessingError(
                "El archivo de entrada no existe para OCR.",
                diagnostic_message=f"No existe la ruta: {source}.",
                error_code="ocr_input_missing",
            )
        destination = (
            Path(output_path)
            if output_path is not None
            else source.with_suffix(".ocr.pdf")
        )
        if destination.suffix.lower() != ".pdf":
            raise OCRProcessingError(
                "La salida de OCR debe ser un PDF.",
                diagnostic_message=f"Destino incorrecto: {destination}.",
                error_code="ocr_invalid_output",
            )

        command = [
            "ocrmypdf",
            "--language",
            self.language,
            "--output-type",
            "pdf",
            str(source),
            str(destination),
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except (FileNotFoundError, subprocess.CalledProcessError, OSError) as error:
            raise OCRProcessingError(
                "No se pudo ejecutar OCRmyPDF sobre el PDF seleccionado.",
                diagnostic_message=str(error),
                error_code="ocr_run_failed",
            ) from error

        if not destination.exists():
            raise OCRProcessingError(
                "OCRmyPDF no generó un archivo de salida válido.",
                diagnostic_message=f"No se encontró el PDF OCR: {destination}.",
                error_code="ocr_output_missing",
            )
        return destination
