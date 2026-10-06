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
python build.py --mode onedir
```

El proceso genera una aplicación GUI autocontenida en formato PyInstaller
`--onedir`, mide diez lanzamientos desde el inicio del proceso hasta el primer
paint de Qt y crea un archivo comprimido con checksum SHA-256 en `dist/`.
Falla si el primer lanzamiento supera 0,9 s o la mediana de los nueve
lanzamientos siguientes supera 0,45 s; esos umbrales dejan un margen del 10 %
respecto al objetivo de 1 s en frío y 500 ms en caliente. “Frío” en este test
significa el primer proceso tras compilar: GitHub-hosted runners no garantizan
una caché de disco/OS vacía. La prueba usa el plugin Qt offscreen, por lo que
mide el primer render de la ventana sin medir inicialización física del monitor.
Los resultados y tamaños del bundle/archivo se guardan en
`dist/startup-benchmark.json`. El mismo informe registra, sin gate, cuándo la
ventana principal queda lista después de la splash.

En macOS el archivo comprimido contiene `PDF2Word.app`; en Windows y Linux
contiene una carpeta `PDF2Word` con el ejecutable y sus dependencias. La
construcción se hace nativamente en cada plataforma. CI ejecuta la medición
para macOS arm64, Windows x86_64 y Linux x86_64. El binario Linux requiere
bibliotecas del sistema compatibles con Ubuntu 22.04 o posterior.

`--onefile` se puede seleccionar para comparar con
`python build.py --mode onefile`, pero no es el formato principal porque la
extracción temporal en cada lanzamiento aumenta la latencia.

El build usa los iconos específicos de plataforma en `assets/` (ICNS para macOS, ICO para Windows y PNG para Linux). El nombre de la aplicación se conserva como `PDF2Word`.

El mantenedor confirma que creó el icono y autoriza su uso y redistribución pública dentro de esta aplicación. Los metadatos de la imagen no permiten verificar esa autoría de forma independiente.

## Descargas

Descarga la versión más reciente desde [GitHub Releases](https://github.com/JuanOrtiz-Software/PDF-TO-DOC/releases/latest). El release contiene estos paquetes:

| Sistema | Archivo | Arquitectura |
| --- | --- | --- |
| macOS | [`PDF2Word.dmg`](https://github.com/JuanOrtiz-Software/PDF-TO-DOC/releases/latest/download/PDF2Word.dmg) | Apple Silicon (arm64) |
| macOS, alternativa comprimida | `PDF2Word-<version>-macos-arm64.tar.gz` ([release](https://github.com/JuanOrtiz-Software/PDF-TO-DOC/releases/latest)) | Apple Silicon (arm64) |
| Windows | `PDF2Word-<version>-windows-x86_64.zip` ([release](https://github.com/JuanOrtiz-Software/PDF-TO-DOC/releases/latest)) | 64 bits, Intel/AMD (x86_64) |
| Linux | `PDF2Word-<version>-linux-x86_64.tar.gz` ([release](https://github.com/JuanOrtiz-Software/PDF-TO-DOC/releases/latest)) | 64 bits, Intel/AMD (x86_64) |

`<version>` es el número de versión del release (por ejemplo, `1.0.0`). Abre la página del release y descarga el archivo de la tabla que coincida con tu sistema y arquitectura.

Los paquetes son ejecutables autocontenidos: no requieren instalar Python. Linux sí necesita las bibliotecas gráficas del sistema indicadas abajo.

### Instalar en macOS

1. Descarga `PDF2Word.dmg` y ábrelo.
2. En la ventana del Finder, arrastra **PDF2Word** a **Applications**.
3. Cuando termine la copia, expulsa el volumen DMG y abre PDF2Word desde Applications.

El DMG es la opción recomendada. El archivo `.tar.gz` alternativo contiene `PDF2Word.app` en la raíz: extráelo y mueve esa app a Applications. Este release es para Apple Silicon; no se publica un build nativo Intel. La aplicación no está firmada con Developer ID ni notarizada, por lo que Gatekeeper puede advertir al abrirla.

### Instalar en Windows

1. Descarga el archivo `.zip` y extráelo (por ejemplo, con **Extraer todo** en el menú contextual).
2. Abre `PDF2Word` dentro de la carpeta extraída y ejecuta `PDF2Word.exe`.

El ZIP contiene la carpeta `PDF2Word`; ejecuta
`PDF2Word\PDF2Word.exe` dentro de ella, sin mover el EXE fuera de la carpeta de
dependencias. No hay instalador ni asistente. Es un build para Windows de 64
bits x86_64. Windows SmartScreen puede mostrar una advertencia porque el
ejecutable no tiene firma de editor.

### Instalar en Linux

Descarga el archivo `PDF2Word-<version>-linux-x86_64.tar.gz` y abre una terminal en la carpeta donde se descargó. Para la versión 1.0.0, ejecuta:

```bash
tar -xzf PDF2Word-1.0.0-linux-x86_64.tar.gz
./PDF2Word/PDF2Word
```

El archivo contiene la carpeta `PDF2Word` con el ejecutable y las bibliotecas
empaquetadas. No separes el ejecutable de esa carpeta. El paquete es para Linux
x86_64. En Ubuntu 22.04 o posterior, instala las bibliotecas gráficas de Qt
que necesita con:

```bash
sudo apt update
sudo apt install libegl1 libxcb-cursor0 libxcb-image0 libxcb-icccm4 \
  libxcb-render-util0 libxcb-keysyms1 libxcb-shape0 libxkbcommon-x11-0 \
  libxcb-xkb1
```

En otras distribuciones instala los paquetes equivalentes. Si el sistema informa que no se puede ejecutar por permisos, usa `chmod +x PDF2Word/PDF2Word` y vuelve a ejecutar `./PDF2Word/PDF2Word`.

No necesitas instalar Python. El ejecutable incluye Python y las dependencias de la aplicación, pero utiliza bibliotecas gráficas del sistema operativo.

### Comprobar la descarga

Cada paquete comprimido tiene un manifiesto `SHA256SUMS-PDF2Word-<version>-<plataforma>.txt` con su SHA-256. Descarga el manifiesto correspondiente en la misma carpeta que el paquete. En Linux, por ejemplo para la versión 1.0.0:

```bash
sha256sum --check SHA256SUMS-PDF2Word-1.0.0-linux-x86_64.txt
```

Para el DMG de macOS, descarga también [`PDF2Word.dmg.sha256`](https://github.com/JuanOrtiz-Software/PDF-TO-DOC/releases/latest/download/PDF2Word.dmg.sha256), colócalo junto al DMG y ejecuta `shasum -a 256 -c PDF2Word.dmg.sha256` desde esa carpeta. Un resultado `OK` confirma que el archivo coincide con el checksum publicado. Los checksums no instalan la aplicación.

En macOS se comprueba un manifiesto de paquete comprimido con `shasum -a 256 -c <nombre-del-manifiesto>`. En Windows PowerShell, con el ZIP y su manifiesto en la misma carpeta, ejecuta (sustituye `1.0.0` si descargaste otra versión):

```powershell
$expected = ((Get-Content .\SHA256SUMS-PDF2Word-1.0.0-windows-x86_64.txt -Raw) -split '\s+')[0]
$actual = (Get-FileHash .\PDF2Word-1.0.0-windows-x86_64.zip -Algorithm SHA256).Hash
if ($actual -ne $expected) { throw "Checksum incorrecto" }
"Checksum OK"
```

### Construir el DMG desde el código fuente (mantenedores)

Estas instrucciones son para generar el instalador, no para instalar una descarga. En macOS, con Python 3.12, clona el repositorio, instala las dependencias de desarrollo y ejecuta:

```bash
python -m pip install ".[dev]"
./scripts/build-dmg.sh
```

El DMG se crea en `dist/PDF2Word.dmg`. Usa `--skip-build` para empaquetar un bundle `.app` ya generado. El fondo editable está en `assets/dmg-background.svg`; después de modificarlo, regenera el PNG que usa Finder con:

```bash
sips -s format png assets/dmg-background.svg --out assets/dmg-background.png
```

El tamaño de ventana, la posición de los iconos y sus tamaños se configuran en `scripts/dmgbuild_settings.py`. La distribución pública firmada y sin advertencias de Gatekeeper requiere membresía de Apple Developer, certificado **Developer ID Application**, firma con Hardened Runtime y notarización mediante `notarytool`. No guardes certificados ni credenciales en el repositorio.

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
