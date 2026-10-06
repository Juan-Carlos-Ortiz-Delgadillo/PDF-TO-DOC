# Hotfix: restaurar la conversión PDF a DOCX

## Causa raíz

El error se reprodujo en el ejecutable empaquetado y el traceback terminaba al
cargar `numpy._core.multiarray`: `ImportError: cannot load module more than once
per process`. `pdf2docx` sí estaba dentro del bundle; el problema se produjo al
construirlo desde un entorno desalineado con `pyproject.toml`, destacando
NumPy 2.5.3 frente al pin del proyecto, NumPy 1.26.4. También había otras
versiones divergentes en ese entorno (OpenCV headless 5.0.0.93 frente a
4.11.0.86 y PySide6 frente a Essentials 6.6.3).

Con el entorno limpio y las versiones fijadas, la importación y la conversión
funcionaron. El build ahora falla antes de empaquetar si las versiones
instaladas no coinciden con los pins, para impedir que ese entorno genere otro
ejecutable defectuoso.

## Cambio realizado

- `build.py` valida las versiones fijadas antes de compilar. Recopila
  `pdf2docx`, `fitz`, `docx` y `fontTools`, declara imports ocultos de todos los
  módulos críticos y recopila los binarios de `fitz` y `cv2`.
- El build ejecuta una conversión PDF→DOCX real con el ejecutable recién
  generado, `PATH` vacío y directorios de usuario temporales. Comprueba que el
  DOCX no esté vacío y que su estructura ZIP sea válida. El CI ya construye
  `onedir`, por lo que este smoke test bloquea el job si falla.
- `conversion_service.py` registra el traceback completo al fallar la
  importación y expone el tipo y causa original en el diagnóstico.
- `pyproject.toml` declara versiones fijadas para las dependencias críticas
  que antes podían quedar implícitas o variar transitivamente:
  `opencv-python-headless`, `fonttools`, `fire` y `lxml`.
- Se añadieron pruebas de regresión para conversión real, diagnóstico/logging
  y presencia de las dependencias críticas en el manifiesto. CI ejecuta
  explícitamente la guardia de dependencias dinámicas; deptry/vulture no se
  usan actualmente en este proyecto.

Diff resumido: son cambios en el control del entorno de build y recolección
del bundle, diagnóstico del error de importación, pins directos y pruebas/CI;
no se cambió la lógica de conversión ni se quitaron dependencias.

## Verificación

- Reproducción previa: el ejecutable compilado con el entorno desalineado
  falló al cargar NumPy desde la importación de `pdf2docx`.
- Entorno fijado: `pip check` limpio y `pdf2docx==0.5.13`.
- Build final `onedir`: correcto. El smoke test del ejecutable importó
  `pdf2docx`, `fitz`, `docx`, `cv2`, `numpy`, `fontTools`, `lxml` y `fire`;
  convirtió el PDF de una página y produjo un DOCX de 36.766 bytes. El proceso
  de prueba tuvo `PATH` vacío y `HOME` temporal.
- Regresión y calidad: 49 pruebas aprobadas; cobertura total 84,11% (umbral
  80%); Ruff, mypy, Bandit y pip-audit aprobaron.
- Arranque del bundle final en macOS 27 arm64, 10 ejecuciones: primer paint
  frío 0,428 s; mediana caliente 0,402 s; p95 caliente 0,427 s. Ventana
  principal lista: 0,534 s fría y mediana caliente 0,467 s. El gate del build
  pasó (límites: 0,9 s frío y 0,45 s de mediana caliente).
- Comparado con el bundle fijado anterior medido en la misma máquina, el
  primer paint pasó de 0,612 a 0,428 s en frío y de 0,421 a 0,402 s de mediana
  caliente. El bundle pasó de 270.746.324 a 284.104.391 bytes (+4,9%); esta
  comparación es agregada y no aísla el efecto de cada cambio.

Artefacto verificado: `PDF2Word-1.0.0-macos-arm64.tar.gz` (108.424.390 bytes).
SHA-256:
`25a381864f5c4a0c3765161c9ff7d27a21f75ea24709cb42e59592fe88992490`.
En esta máquina está en `/tmp/pdf2docx-hotfix-release/`.

## Imports diferidos y riesgos similares

- `pdf2docx.Converter` en `app/services/conversion_service.py`: pin directo,
  recolección explícita y probado en el bundle.
- `fitz` en `app/services/pdf_analyzer.py`, y `docx` en
  `app/services/output_service.py`: dependencias fijadas y probadas en el
  bundle.
- `MainWindow` se importa al mostrar la UI desde `app/ui/launcher.py`; la
  prueba de arranque empaquetada y la suite de UI cubren esta ruta.
- El modo de smoke test importa dinámicamente los ocho módulos enumerados
  arriba; no se encontraron archivos locales `pdf2docx.py` o `fitz.py` que los
  sombreen.

## Revisión humana pendiente

La compilación y medición locales se hicieron en macOS arm64. Confirmar que
los jobs de CI para Windows y Linux pasan con sus respectivos bundles y smoke
tests. El smoke usa `PATH` vacío, pero no sustituye una validación en una VM
limpia sin Python instalado ni la revisión de firma/notarización de los
instaladores antes de publicar. OCR sigue dependiendo de herramientas
externas opcionales y no forma parte de esta prueba de conversión.
