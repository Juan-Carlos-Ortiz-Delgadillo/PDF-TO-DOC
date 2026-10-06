"""Motor central de conversión de PDF a DOCX."""

from __future__ import annotations

import contextlib
import time
from pathlib import Path

from app.core.exceptions import ConversionError, PDF2WordError, PDFValidationError
from app.models import ConversionConfig, ConversionResult, PDFInfo
from app.services.ocr_service import OCRService
from app.services.output_service import OutputService
from app.services.pdf_analyzer import PDFAnalyzer


class ConversionService:
    """Orquesta el análisis, OCR opcional y publicación de un documento."""

    def __init__(
        self,
        *,
        analyzer: PDFAnalyzer | None = None,
        output_service: OutputService | None = None,
        ocr_service: OCRService | None = None,
    ) -> None:
        self.analyzer = analyzer or PDFAnalyzer()
        self.output_service = output_service or OutputService()
        self.ocr_service = ocr_service or OCRService()

    def analyze(self, pdf_path: str | Path) -> PDFInfo:
        """Analiza un PDF sin ejecutar la conversión."""

        return self.analyzer.analyze(pdf_path)

    def convert(self, config: ConversionConfig) -> ConversionResult:
        """Convierte un PDF en DOCX siguiendo la configuración de tarea."""

        start_time = time.monotonic()
        source_path = self.analyzer.validate_input(config.input_path)
        pdf_info = self.analyzer.analyze(source_path)
        selected_pages = config.pages_requested(pdf_info.page_count)

        if pdf_info.is_encrypted:
            raise PDFValidationError(
                "El PDF está protegido y no se puede convertir sin contraseña.",
                diagnostic_message="PyMuPDF indicó que el archivo exige contraseña.",
                error_code="pdf_password_required",
            )

        output_directory = self.output_service.ensure_output_directory(
            config.output_path.parent,
            create=True,
        )
        temp_output = self.output_service.create_temporary_output(
            output_directory / config.output_path.name,
            overwrite_confirmed=config.overwrite_confirmed,
            create_directory=True,
        )

        try:
            source_for_conversion = source_path
            if config.use_ocr and pdf_info.requires_ocr:
                source_for_conversion = self.ocr_service.run(
                    source_path,
                    output_path=source_path.with_suffix(".ocr.pdf"),
                )

                if not source_for_conversion.exists():
                    raise PDFValidationError(
                        "El OCR local no produjo un PDF válido.",
                        diagnostic_message=(
                            "La salida creada por OCR no existe o no es accesible."
                        ),
                        error_code="ocr_output_missing",
                    )

            self._convert_pdf_to_docx(
                source_for_conversion,
                temp_output,
                selected_pages,
                total_pages=pdf_info.page_count,
                multiprocessing_enabled=config.multiprocessing_enabled,
            )
            validated_path = self.output_service.validate_docx(temp_output)
            published_path = self.output_service.publish(
                validated_path,
                config.output_path,
                overwrite_confirmed=config.overwrite_confirmed,
            )
            duration = time.monotonic() - start_time
            return ConversionResult.completed(
                input_path=source_path,
                output_path=published_path,
                pages_requested=selected_pages,
                duration_seconds=duration,
                user_message="Conversión completada correctamente.",
            )
        except PDF2WordError:
            raise
        except Exception as error:  # pragma: no cover - se envuelve al nivel del dominio
            duration = time.monotonic() - start_time
            raise ConversionError(
                "No se pudo completar la conversión del PDF a Word.",
                diagnostic_message=f"{type(error).__name__}: {error}",
                error_code="conversion_failed",
            ) from error
        finally:
            self.output_service.cleanup_temporary(temp_output)

    def _convert_pdf_to_docx(
        self,
        pdf_path: str | Path,
        output_path: str | Path,
        selected_pages: tuple[int, ...],
        *,
        total_pages: int,
        multiprocessing_enabled: bool,
    ) -> None:
        """Convierte el PDF usando la librería local pdf2docx."""

        try:
            from pdf2docx import Converter
        except ImportError as error:
            raise ConversionError(
                "Falta la dependencia local 'pdf2docx'.",
                diagnostic_message="No fue posible importar pdf2docx.",
                error_code="pdf2docx_missing",
            ) from error

        converter = Converter(str(pdf_path))
        try:
            all_pages = tuple(range(1, total_pages + 1))
            if selected_pages == all_pages:
                converter.convert(str(output_path))
                return

            if selected_pages and selected_pages == tuple(
                range(selected_pages[0], selected_pages[-1] + 1)
            ):
                converter.convert(
                    str(output_path),
                    start=selected_pages[0] - 1,
                    end=selected_pages[-1],
                    multi_processing=multiprocessing_enabled,
                )
                return

            converter.convert(
                str(output_path),
                pages=[page - 1 for page in selected_pages],
                multi_processing=False,
            )
        except Exception as error:
            raise ConversionError(
                "La librería local de conversión falló durante la exportación.",
                diagnostic_message=f"{type(error).__name__}: {error}",
                error_code="pdf2docx_conversion_error",
            ) from error
        finally:
            with contextlib.suppress(Exception):
                converter.close()
