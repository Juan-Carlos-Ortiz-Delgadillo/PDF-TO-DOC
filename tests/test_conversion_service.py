from __future__ import annotations

from pathlib import Path

import fitz

from app.models import ConversionConfig, PageSelection
from app.services import ConversionService


def test_conversion_service_converts_simple_pdf(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    docx_path = tmp_path / "result.docx"

    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Hola PDF2Word")
    document.save(pdf_path)
    document.close()

    config = ConversionConfig(
        input_path=pdf_path,
        output_path=docx_path,
        page_selection=PageSelection.all(),
        use_ocr=False,
        ocr_language="spa",
        multiprocessing_enabled=False,
        overwrite_confirmed=True,
    )

    result = ConversionService().convert(config)

    assert result.output_path == docx_path
    assert docx_path.exists()
    assert result.status.name == "COMPLETED"
