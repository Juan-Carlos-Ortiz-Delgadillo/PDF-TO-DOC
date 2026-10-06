#!/bin/bash
set -euo pipefail

APP_NAME="PDF2Word"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_BUNDLE="${PROJECT_ROOT}/dist/${APP_NAME}.app"
BACKGROUND="${PROJECT_ROOT}/assets/dmg-background.png"
SETTINGS="${PROJECT_ROOT}/scripts/dmgbuild_settings.py"
VERIFY_SCRIPT="${PROJECT_ROOT}/scripts/verify_dmg.py"
OUTPUT_DMG="${PROJECT_ROOT}/dist/${APP_NAME}.dmg"
BUILD_APP=1
PYTHON="${PYTHON:-python3.12}"

usage() {
    printf 'Uso: %s [--skip-build]\n' "$0"
    printf '  --skip-build  Usa dist/%s.app sin volver a compilarla.\n' "$APP_NAME"
}

while (($#)); do
    case "$1" in
        --skip-build)
            BUILD_APP=0
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            printf 'Opción desconocida: %s\n' "$1" >&2
            usage >&2
            exit 2
            ;;
    esac
    shift
done

if [[ "$(uname -s)" != "Darwin" ]]; then
    printf 'Este script solo puede crear DMG en macOS.\n' >&2
    exit 1
fi

if [[ "$BUILD_APP" -eq 1 ]]; then
    if ! command -v "$PYTHON" >/dev/null 2>&1; then
        printf 'No se encontró %s. Instala Python 3.12 o define PYTHON.\n' "$PYTHON" >&2
        exit 1
    fi
    (
        cd "$PROJECT_ROOT"
        "$PYTHON" build.py
    )
fi

if ! command -v "$PYTHON" >/dev/null 2>&1; then
    printf 'No se encontró %s para verificar el DMG.\n' "$PYTHON" >&2
    exit 1
fi
DMGBUILD="${DMGBUILD:-dmgbuild}"
if ! command -v "$DMGBUILD" >/dev/null 2>&1; then
    printf 'No se encontró dmgbuild. Instala las dependencias de desarrollo con:\n' >&2
    printf '  python3.12 -m pip install ".[dev]"\n' >&2
    exit 1
fi
if [[ ! -d "$APP_BUNDLE" || ! -f "$APP_BUNDLE/Contents/Info.plist" ]]; then
    printf 'No se encontró un bundle macOS válido: %s\n' "$APP_BUNDLE" >&2
    exit 1
fi
if [[ ! -f "$BACKGROUND" || ! -f "$SETTINGS" || ! -f "$VERIFY_SCRIPT" ]]; then
    printf 'Falta el fondo del DMG o su configuración.\n' >&2
    exit 1
fi

APP_ICON_FILE=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIconFile' "$APP_BUNDLE/Contents/Info.plist")
if [[ ! -f "$APP_BUNDLE/Contents/Resources/$APP_ICON_FILE" ]]; then
    printf 'El bundle no contiene el icono declarado: %s\n' "$APP_ICON_FILE" >&2
    exit 1
fi

STAGING_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/pdf2word-dmg.XXXXXX")"
FINAL_DMG="${STAGING_ROOT}/${APP_NAME}.dmg"
VERIFY_MOUNT="${STAGING_ROOT}/verify"
ATTACHED=0

cleanup() {
    if [[ "$ATTACHED" -eq 1 ]]; then
        hdiutil detach "$VERIFY_MOUNT" -quiet >/dev/null 2>&1 || true
    fi
    rm -rf "$STAGING_ROOT"
}
trap cleanup EXIT

mkdir -p "$VERIFY_MOUNT"
"$DMGBUILD" \
    -s "$SETTINGS" \
    -D "app=$APP_BUNDLE" \
    -D "background=$BACKGROUND" \
    "$APP_NAME" \
    "$FINAL_DMG"

hdiutil verify "$FINAL_DMG"
hdiutil attach -quiet -nobrowse -readonly -mountpoint "$VERIFY_MOUNT" "$FINAL_DMG"
ATTACHED=1

if [[ ! -d "$VERIFY_MOUNT/${APP_NAME}.app" ]]; then
    printf 'El DMG final no contiene %s.app.\n' "$APP_NAME" >&2
    exit 1
fi
if [[ ! -L "$VERIFY_MOUNT/Applications" || "$(readlink "$VERIFY_MOUNT/Applications")" != "/Applications" ]]; then
    printf 'El acceso Applications no apunta a /Applications.\n' >&2
    exit 1
fi
if [[ ! -f "$VERIFY_MOUNT/.background.png" ]]; then
    printf 'El fondo personalizado no está presente en el DMG.\n' >&2
    exit 1
fi
if [[ ! -f "$VERIFY_MOUNT/.DS_Store" ]]; then
    printf 'El DMG no contiene la configuración de Finder (.DS_Store).\n' >&2
    exit 1
fi
"$PYTHON" "$VERIFY_SCRIPT" "$VERIFY_MOUNT" "$APP_NAME"

unexpected_entries="$(find "$VERIFY_MOUNT" -mindepth 1 -maxdepth 1 \
    ! -name ".DS_Store" \
    ! -name ".background.png" \
    ! -name "${APP_NAME}.app" \
    ! -name "Applications" \
    -print)"
if [[ -n "$unexpected_entries" ]]; then
    printf 'El DMG contiene elementos inesperados:\n%s\n' "$unexpected_entries" >&2
    exit 1
fi

hdiutil detach "$VERIFY_MOUNT" -quiet
ATTACHED=0

mkdir -p "$(dirname "$OUTPUT_DMG")"
mv -f "$FINAL_DMG" "$OUTPUT_DMG"
(
    cd "$(dirname "$OUTPUT_DMG")"
    shasum -a 256 "$(basename "$OUTPUT_DMG")" > "$(basename "$OUTPUT_DMG").sha256"
)

printf 'DMG verificado: %s\n' "$OUTPUT_DMG"
printf 'SHA-256: %s\n' "${OUTPUT_DMG}.sha256"
