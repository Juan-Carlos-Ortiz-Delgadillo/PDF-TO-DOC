"""Punto de entrada principal para la aplicación."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.bootstrap import bootstrap_application
from app.models import ConversionConfig, PageSelection
from app.services import ConversionService


def main() -> int:
    """Ejecuta la fase de arranque y devuelve un código de salida."""

    bootstrap_application()
    parser = argparse.ArgumentParser(description="Convierte un PDF local a DOCX.")
    parser.add_argument("input_pdf", help="Ruta del archivo PDF de entrada.")
    parser.add_argument("output_docx", help="Ruta del archivo DOCX de salida.")
    parser.add_argument(
        "--pages",
        default="all",
        help="Selección de páginas: all, 1-4 o 1,3,5.",
    )
    parser.add_argument(
        "--ocr",
        action="store_true",
        help="Activa OCR local si el PDF lo requiere.",
    )
    parser.add_argument("--language", default="spa", help="Idioma de OCR para OCRmyPDF.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Sobrescribe el archivo final si existe.",
    )
    args = parser.parse_args()

    try:
        service = ConversionService()
        pdf_info = service.analyze(Path(args.input_pdf))
        selection = PageSelection.parse(args.pages, pdf_info.page_count)
        config = ConversionConfig(
            input_path=Path(args.input_pdf),
            output_path=Path(args.output_docx),
            page_selection=selection,
            use_ocr=args.ocr,
            ocr_language=args.language,
            multiprocessing_enabled=False,
            overwrite_confirmed=args.overwrite,
        )
        result = service.convert(config)
    except Exception as error:  # pragma: no cover - CLI surface
        raise SystemExit(f"Error: {error}") from error

    print(f"Conversión completada: {result.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
