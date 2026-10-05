"""Análisis local y no destructivo de documentos PDF con PyMuPDF."""

from __future__ import annotations

import contextlib
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from app.core.exceptions import PDFAnalysisError, PDFEncryptedError, PDFValidationError
from app.models import PDFInfo, PDFPageInfo


class PDFAnalyzer:
    """Obtiene metadatos de un PDF y estima prudentemente si requiere OCR.

    Una página sólo se marca como candidata a OCR cuando combina poco texto
    extraíble con imágenes que ocupan una porción relevante de la página.
    Así, una fotografía pequeña con un pie de foto, una página en blanco o un
    PDF digital con pocos caracteres no se confunden automáticamente con un
    escaneo. La estimación no sustituye una revisión visual del documento.
    """

    _SIGNATURE_SCAN_BYTES = 1_024

    def __init__(
        self,
        *,
        minimum_text_length: int = 20,
        minimum_image_coverage: float = 0.45,
        require_pdf_extension: bool = True,
    ) -> None:
        if minimum_text_length < 0:
            raise ValueError("minimum_text_length no puede ser negativo")
        if not 0.0 < minimum_image_coverage <= 1.0:
            raise ValueError("minimum_image_coverage debe estar entre 0 y 1")

        self._minimum_text_length = minimum_text_length
        self._minimum_image_coverage = minimum_image_coverage
        self._require_pdf_extension = require_pdf_extension

    @property
    def minimum_text_length(self) -> int:
        """Longitud mínima de texto usada por la heurística de OCR."""

        return self._minimum_text_length

    @property
    def minimum_image_coverage(self) -> float:
        """Cobertura mínima de imágenes usada por la heurística de OCR."""

        return self._minimum_image_coverage

    def analyze(self, path: Path) -> PDFInfo:
        """Analiza *path* sin modificarlo y devuelve información tipada.

        Raises:
            PDFValidationError: si la ruta, tamaño, extensión o firma no son
                válidos para un PDF.
            PDFEncryptedError: si el documento exige contraseña para abrirse.
            PDFAnalysisError: si PyMuPDF no puede leer un PDF aparentemente
                válido o no está disponible.
        """

        pdf_path = self.validate_input(path)
        fitz = self._load_fitz()
        document: Any | None = None

        try:
            document = fitz.open(pdf_path)
            is_encrypted = bool(getattr(document, "is_encrypted", False))
            if bool(getattr(document, "needs_pass", False)):
                raise PDFEncryptedError(
                    "Este PDF está protegido; revisa si necesita contraseña.",
                    diagnostic_message="PyMuPDF indicó que el documento requiere contraseña.",
                    error_code="pdf_password_required",
                )

            page_count = int(getattr(document, "page_count", len(document)))
            if page_count <= 0:
                raise PDFAnalysisError(
                    "No se pudo leer el documento porque no contiene páginas.",
                    diagnostic_message="El documento abierto por PyMuPDF tiene cero páginas.",
                    error_code="pdf_without_pages",
                )

            pages = tuple(
                self._analyze_page(document[index], index + 1)
                for index in range(page_count)
            )
        except PDFEncryptedError:
            raise
        except PDFAnalysisError:
            raise
        except (OSError, RuntimeError, ValueError, TypeError) as error:
            raise PDFAnalysisError(
                "No se pudo leer el documento PDF.",
                diagnostic_message=self._diagnostic_for(error),
                error_code="pdf_read_error",
            ) from error
        finally:
            if document is not None:
                with contextlib.suppress(OSError, RuntimeError, ValueError):
                    document.close()

        return PDFInfo(
            path=pdf_path,
            page_count=page_count,
            file_size=pdf_path.stat().st_size,
            has_text=any(page.has_text for page in pages),
            has_images=any(page.has_images for page in pages),
            is_encrypted=is_encrypted,
            requires_ocr=any(page.requires_ocr for page in pages),
            pages=pages,
        )

    def validate_input(self, path: Path) -> Path:
        """Valida una ruta de entrada y la firma PDF antes de abrirla."""

        pdf_path = Path(path).expanduser()
        if self._require_pdf_extension and pdf_path.suffix.lower() != ".pdf":
            raise PDFValidationError(
                "Selecciona un archivo con extensión .pdf.",
                diagnostic_message="La extensión de entrada no es .pdf.",
                error_code="invalid_pdf_extension",
            )

        try:
            if not pdf_path.exists() or not pdf_path.is_file():
                raise PDFValidationError(
                    "El archivo PDF seleccionado no existe o no es un archivo.",
                    diagnostic_message="La ruta de entrada no apunta a un archivo regular.",
                    error_code="pdf_not_found",
                )
            size = pdf_path.stat().st_size
            if size <= 0:
                raise PDFValidationError(
                    "El archivo PDF está vacío.",
                    diagnostic_message="El tamaño de la entrada es cero bytes.",
                    error_code="empty_pdf",
                )
            with pdf_path.open("rb") as source:
                header = source.read(self._SIGNATURE_SCAN_BYTES)
        except PDFValidationError:
            raise
        except (OSError, PermissionError) as error:
            raise PDFValidationError(
                "No se pudo acceder al archivo PDF seleccionado.",
                diagnostic_message=self._diagnostic_for(error),
                error_code="pdf_unreadable",
            ) from error

        if b"%PDF-" not in header:
            raise PDFValidationError(
                "El archivo no parece ser un PDF válido.",
                diagnostic_message="No se encontró una firma %PDF- en los primeros 1024 bytes.",
                error_code="invalid_pdf_signature",
            )
        return pdf_path

    def classify(self, info: PDFInfo) -> str:
        """Clasifica orientativamente un PDF como digital, escaneado o mixto."""

        if not info.pages:
            return "desconocido"
        ocr_pages = sum(page.requires_ocr for page in info.pages)
        if ocr_pages == 0:
            return "digital"
        if ocr_pages == len(info.pages):
            return "escaneado"
        return "mixto"

    def _analyze_page(self, page: Any, page_number: int) -> PDFPageInfo:
        try:
            text = page.get_text("text") or ""
            text_length = len(text.strip())
            image_coverage, has_images = self._image_coverage(page)
        except (OSError, RuntimeError, ValueError, TypeError, KeyError) as error:
            raise PDFAnalysisError(
                "No se pudo analizar una página del PDF.",
                diagnostic_message=(
                    f"Error al analizar la página {page_number}: "
                    f"{self._diagnostic_for(error)}"
                ),
                error_code="pdf_page_analysis_error",
            ) from error

        requires_ocr = self._requires_ocr(
            text_length=text_length,
            has_images=has_images,
            image_coverage=image_coverage,
        )
        return PDFPageInfo(
            page_number=page_number,
            has_text=text_length > 0,
            text_length=text_length,
            has_images=has_images,
            requires_ocr=requires_ocr,
        )

    def _image_coverage(self, page: Any) -> tuple[float, bool]:
        """Calcula una aproximación de área de imágenes sobre el área de página."""

        page_area = self._rectangle_area(getattr(page, "rect", None))
        image_area = 0.0
        image_blocks: Iterable[dict[str, Any]] = ()

        page_dict = page.get_text("dict")
        if isinstance(page_dict, dict):
            blocks = page_dict.get("blocks", ())
            if isinstance(blocks, list | tuple):
                image_blocks = (
                    block
                    for block in blocks
                    if isinstance(block, dict) and block.get("type") == 1
                )

        for block in image_blocks:
            image_area += self._rectangle_area(block.get("bbox"))

        image_refs = page.get_images(full=False)
        has_images = bool(image_area > 0 or image_refs)
        if page_area <= 0:
            return 0.0, has_images
        return min(image_area / page_area, 1.0), has_images

    @staticmethod
    def _rectangle_area(rectangle: Any) -> float:
        """Devuelve el área de un rectángulo PyMuPDF o de una tupla ``bbox``."""

        if rectangle is None:
            return 0.0
        try:
            if hasattr(rectangle, "width") and hasattr(rectangle, "height"):
                return max(float(rectangle.width), 0.0) * max(float(rectangle.height), 0.0)
            left, top, right, bottom = rectangle
            return max(float(right) - float(left), 0.0) * max(float(bottom) - float(top), 0.0)
        except (TypeError, ValueError):
            return 0.0

    def _requires_ocr(self, *, text_length: int, has_images: bool, image_coverage: float) -> bool:
        return (
            text_length < self._minimum_text_length
            and has_images
            and image_coverage >= self._minimum_image_coverage
        )

    @staticmethod
    def _load_fitz() -> Any:
        try:
            import fitz
        except ImportError as error:
            raise PDFAnalysisError(
                "No se puede analizar el PDF porque falta PyMuPDF.",
                diagnostic_message="No fue posible importar el paquete fitz (PyMuPDF).",
                error_code="pymupdf_unavailable",
            ) from error
        return fitz

    @staticmethod
    def _diagnostic_for(error: BaseException) -> str:
        """Evita exponer rutas o contenido de entrada en un diagnóstico de UI."""

        return f"{type(error).__name__}: {str(error)[:300]}"
