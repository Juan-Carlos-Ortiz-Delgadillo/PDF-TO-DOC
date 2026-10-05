# PDF2Word

PDF2Word es una aplicación local para convertir documentos PDF a Microsoft Word (.docx) sin depender de servicios externos.

## Objetivo

- Validar PDF locales antes de procesarlos.
- Detectar si un documento requiere OCR.
- Convertir a DOCX con un motor local.
- Publicar el resultado en una ruta elegida por el usuario.
- Mantener un historial local seguro sin registrar contenido del documento.

## Requisitos

- Python 3.12+
- PySide6
- PyMuPDF
- pdf2docx
- python-docx

## Uso

Modo base (arranque de la aplicación):

```bash
python -m app.main
```

Conversión directa de un PDF a DOCX:

```bash
python -m app.main input.pdf output.docx --pages "1-4" --overwrite
```

También puedes activar OCR local cuando el documento lo requiera:

```bash
python -m app.main input.pdf output.docx --ocr --language spa
```

## Privacidad

La conversión se realiza localmente. El proyecto no envía documentos a servicios remotos ni registra su contenido.

## Licencia

PDF2Word se distribuye bajo la licencia GNU Affero General Public License v3.0 (AGPL-3.0-only).
Consulta el texto completo en [LICENSE](LICENSE).

## Limitaciones conocidas

- El OCR es opcional y depende de Tesseract/OCRmyPDF instalados localmente.
- El resultado puede variar según columnas, tablas, imágenes, encabezados y análisis de PDF.
- Las páginas escaneadas requieren OCR y pueden no conservar el formato exacto.

 Consulte la documentación en la carpeta `docs/`.
