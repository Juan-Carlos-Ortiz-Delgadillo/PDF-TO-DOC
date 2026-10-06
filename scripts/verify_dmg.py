"""Verifica Finder metadata written into a mounted PDF2Word DMG."""

from __future__ import annotations

import plistlib
import sys
from pathlib import Path

from ds_store import DSStore


def verify_dmg(mount_point: Path, app_name: str) -> None:
    """Raise an error if the mounted disk image is missing the expected layout."""

    with DSStore.open(str(mount_point / ".DS_Store"), "r") as store:
        window = store["."]["bwsp"]
        icon_view = store["."]["icvp"]
        app_position = store[f"{app_name}.app"]["Iloc"]
        applications_position = store["Applications"]["Iloc"]

    expected_bounds = "{{100, 100}, {700, 450}}"
    if window.get("WindowBounds") != expected_bounds:
        raise ValueError(f"WindowBounds incorrectos: {window.get('WindowBounds')!r}")
    if app_position != (175, 225):
        raise ValueError(f"Posición de la aplicación incorrecta: {app_position!r}")
    if applications_position != (525, 225):
        raise ValueError(f"Posición de Applications incorrecta: {applications_position!r}")
    if icon_view.get("iconSize") != 96 or icon_view.get("textSize") != 14:
        raise ValueError("El tamaño de iconos o etiquetas no coincide con el diseño.")
    if not icon_view.get("showIconPreview"):
        raise ValueError("Finder no tiene habilitada la vista previa de iconos.")
    if icon_view.get("arrangeBy") != "none":
        raise ValueError("Los iconos del DMG deben permanecer en posiciones manuales.")
    if icon_view.get("backgroundType") != 2:
        raise ValueError("Finder no tiene configurada la imagen de fondo.")
    if not icon_view.get("backgroundImageAlias"):
        raise ValueError("Falta el alias del fondo en la configuración de Finder.")
    if not (mount_point / ".background.png").is_file():
        raise FileNotFoundError("No se encontró el fondo integrado en el DMG.")

    app_resources = mount_point / f"{app_name}.app/Contents/Resources"
    info_plist = mount_point / f"{app_name}.app/Contents/Info.plist"
    if not info_plist.is_file():
        raise FileNotFoundError(f"No se encontró el Info.plist de {app_name}.app.")
    app_icon_name = plistlib.loads(info_plist.read_bytes()).get("CFBundleIconFile")
    if not isinstance(app_icon_name, str) or not app_icon_name:
        raise ValueError(f"{app_name}.app no declara un icono en Info.plist.")
    app_icon = app_resources / app_icon_name
    if not app_icon.is_file() and not Path(app_icon_name).suffix:
        app_icon = app_resources / f"{app_icon_name}.icns"
    if not app_icon.is_file():
        raise FileNotFoundError(f"No se encontró el icono declarado por {app_name}.app.")


def main() -> int:
    if len(sys.argv) != 3:
        print("Uso: verify_dmg.py <punto-de-montaje> <nombre-app>", file=sys.stderr)
        return 2

    verify_dmg(Path(sys.argv[1]), sys.argv[2])
    print("Configuración de Finder verificada: ventana 700x450, iconos y fondo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
