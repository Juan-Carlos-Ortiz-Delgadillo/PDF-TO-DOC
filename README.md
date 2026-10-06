# PDF2Word

PDF2Word convierte documentos PDF a Microsoft Word (.docx) localmente, sin enviar documentos a servicios externos.

## Requisitos e instalación

Se requiere Python 3.12 para instalar desde el código fuente:

```bash
python -m pip install .
```

Los comandos instalados son `pdf2word-gui` para abrir la interfaz gráfica y `pdf2word` para usar la CLI. También se puede ejecutar la GUI desde el árbol fuente:

```bash
python -m app.ui.main_window
```

Instala las herramientas de desarrollo y pruebas con:

```bash
python -m pip install ".[dev]"
```

## Uso de la CLI

Convierte un PDF directamente:

```bash
pdf2word input.pdf output.docx --pages "1-4" --overwrite
```

También puedes ejecutar la CLI desde el código fuente:

```bash
python -m app.main input.pdf output.docx --pages "1-4" --overwrite
```

Para activar OCR local:

```bash
pdf2word input.pdf output.docx --ocr --language spa
```

El OCR es opcional y requiere OCRmyPDF, Tesseract y los datos del idioma elegido instalados localmente.

## Construcción de ejecutables

Con Python 3.12 y las dependencias de desarrollo instaladas, ejecuta:

```bash
python build.py
```

El proceso genera una aplicación GUI autocontenida, comprueba que arranque y crea un archivo comprimido con su checksum SHA-256 en `dist/`. En macOS el archivo contiene un bundle `.app`; en Windows y Linux contiene un ejecutable. La construcción se hace nativamente en cada plataforma. Las publicaciones automatizadas incluyen macOS (arquitectura del runner), Windows x86_64 y Linux x86_64. El binario Linux requiere bibliotecas del sistema compatibles con Ubuntu 22.04 o posterior.

El build usa los iconos específicos de plataforma en `assets/` (ICNS para macOS, ICO para Windows y PNG para Linux). El nombre de la aplicación se conserva como `PDF2Word`.

El mantenedor confirma que creó el icono y autoriza su uso y redistribución pública dentro de esta aplicación. Los metadatos de la imagen no permiten verificar esa autoría de forma independiente.

## Descargas

Descarga la versión más reciente desde [GitHub Releases](https://github.com/JuanOrtiz-Software/PDF-TO-DOC/releases/latest). Allí encontrarás los paquetes autocontenidos para macOS, Windows y Linux, junto con sus checksums SHA-256.

Para macOS también está disponible el [instalador DMG de arrastrar a Applications](https://github.com/JuanOrtiz-Software/PDF-TO-DOC/releases/latest/download/PDF2Word.dmg) y su [checksum SHA-256](https://github.com/JuanOrtiz-Software/PDF-TO-DOC/releases/latest/download/PDF2Word.dmg.sha256). La aplicación macOS aún no está firmada con Developer ID ni notarizada; Gatekeeper puede mostrar una advertencia al abrirla.

### Instalación en macOS con imagen DMG

En macOS, instala las dependencias de desarrollo y ejecuta:

```bash
python -m pip install ".[dev]"
./scripts/build-dmg.sh
```

El archivo `dist/PDF2Word.dmg` abre en Finder con la app, una flecha visual y
un acceso directo a Applications; arrastra la app a Applications para
instalarla. `dist/PDF2Word.dmg.sha256` contiene su checksum. Para reutilizar un
bundle existente sin reconstruirlo, ejecuta
`./scripts/build-dmg.sh --skip-build`.

El fondo se define en `assets/dmg-background.svg`; la imagen PNG de 1400×900
que Finder muestra se guarda en `assets/dmg-background.png` y dentro del DMG
como `.background.png`. Los tamaños de
ventana, posiciones e iconos se configuran en
`scripts/dmgbuild_settings.py`. El proceso valida los metadatos de `.DS_Store`,
el alias `/Applications`, el bundle y la imagen de fondo antes de terminar.
Para regenerar el PNG tras cambiar el SVG, ejecuta
`sips -s format png assets/dmg-background.svg --out assets/dmg-background.png`.

La imagen no está firmada con Developer ID ni notarizada. Para distribución
pública sin las advertencias habituales de Gatekeeper se necesita una
membresía de Apple Developer, un certificado **Developer ID Application**,
firma con Hardened Runtime y notarización mediante `notarytool`. No guardes
certificados ni credenciales en el repositorio o en el DMG; configúralos como
secretos del sistema de build cuando estén disponibles.

## Privacidad y limitaciones

La conversión se realiza localmente. El proyecto no envía documentos a servicios remotos ni registra su contenido. Los PDFs complejos o escaneados pueden perder fidelidad; el OCR no garantiza exactitud ni una reproducción visual perfecta.

La arquitectura y otras limitaciones se describen en [docs/architecture.md](docs/architecture.md) y [docs/known-limitations.md](docs/known-limitations.md).

## Licencia

PDF2Word se distribuye bajo GNU Affero General Public License v3.0 (AGPL-3.0-only). Consulta [LICENSE](LICENSE).

## Publicación

Tras revisar la versión, crea y publica el primer tag:

```bash
git tag v1.0.0
git push --tags
```

GitHub Actions construye artefactos por plataforma, prueba su arranque y los adjunta al Release.
