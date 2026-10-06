"""Construye y prueba un ejecutable GUI autocontenido para la plataforma actual."""

from __future__ import annotations

import hashlib
import os
import platform
import subprocess
import tarfile
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP_NAME = "PDF2Word"
APP_ICONS = {
    "macos": ROOT / "assets" / "icon.icns",
    "windows": ROOT / "assets" / "icon.ico",
    "linux": ROOT / "assets" / "icon.png",
}


def _target_platform() -> tuple[str, str]:
    system = platform.system().lower()
    system_name = {"darwin": "macos", "windows": "windows", "linux": "linux"}.get(system)
    if system_name is None:
        raise RuntimeError(f"Plataforma no compatible con el empaquetado: {system}.")
    machine = platform.machine().lower()
    architecture = {"amd64": "x86_64", "aarch64": "arm64"}.get(machine, machine)
    if (system_name, architecture) not in {
        ("macos", "arm64"),
        ("macos", "x86_64"),
        ("windows", "x86_64"),
        ("linux", "x86_64"),
    }:
        raise RuntimeError(f"Arquitectura no configurada para distribución: {machine}.")
    return system_name, architecture


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as artifact:
        for chunk in iter(lambda: artifact.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _smoke_test(executable: Path) -> None:
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    process = subprocess.Popen(
        [str(executable)],
        cwd=ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        try:
            return_code = process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            return
        stdout, stderr = process.communicate()
        raise RuntimeError(
            "La aplicación empaquetada terminó inesperadamente "
            f"(código {return_code}).\n{stdout}{stderr}"
        )
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def _archive(payload: Path, destination: Path) -> None:
    if destination.suffix == ".zip":
        with zipfile.ZipFile(
            destination,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as bundle:
            bundle.write(payload, arcname=payload.name)
        return

    with tarfile.open(destination, mode="w:gz") as bundle:
        bundle.add(payload, arcname=payload.name)


def main() -> int:
    from PyInstaller.__main__ import run as run_pyinstaller

    with (ROOT / "pyproject.toml").open("rb") as project_file:
        version = tomllib.load(project_file)["project"]["version"]
    system, architecture = _target_platform()
    dist_directory = ROOT / "dist"
    build_directory = ROOT / "build"
    dist_directory.mkdir(parents=True, exist_ok=True)
    build_directory.mkdir(parents=True, exist_ok=True)

    arguments = [
        "--clean",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name",
        APP_NAME,
        "--distpath",
        str(dist_directory),
        "--workpath",
        str(build_directory / "pyinstaller"),
        "--specpath",
        str(build_directory),
        "--paths",
        str(ROOT),
    ]
    for stylesheet in ("styles.qss", "styles_dark.qss"):
        arguments.extend(
            [
                "--add-data",
                f"{ROOT / 'app' / 'ui' / stylesheet}{os.pathsep}.",
            ]
        )
    app_icon = APP_ICONS[system]
    if not app_icon.is_file():
        raise FileNotFoundError(f"No se encontró el icono de aplicación: {app_icon}")
    arguments.extend(["--icon", str(app_icon)])
    arguments.append(str(ROOT / "app" / "ui" / "main_window.py"))
    run_pyinstaller(arguments)

    executable_name = f"{APP_NAME}.exe" if system == "windows" else APP_NAME
    executable = dist_directory / executable_name
    payload = executable
    if system == "macos":
        payload = dist_directory / f"{APP_NAME}.app"
        executable = payload / "Contents" / "MacOS" / APP_NAME
    if not executable.is_file():
        raise FileNotFoundError(f"PyInstaller no creó el ejecutable esperado: {executable}")

    _smoke_test(executable)
    suffix = ".zip" if system == "windows" else ".tar.gz"
    artifact = dist_directory / f"{APP_NAME}-{version}-{system}-{architecture}{suffix}"
    _archive(payload, artifact)

    checksum_manifest = dist_directory / (
        f"SHA256SUMS-{APP_NAME}-{version}-{system}-{architecture}.txt"
    )
    checksum_manifest.write_text(
        f"{_sha256(artifact)}  {artifact.name}\n",
        encoding="utf-8",
    )
    if system == "macos":
        (dist_directory / APP_NAME).unlink(missing_ok=True)

    print(f"Aplicación verificada: {payload}")
    print(f"Artefacto de distribución: {artifact}")
    print(f"Checksum SHA-256: {checksum_manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
