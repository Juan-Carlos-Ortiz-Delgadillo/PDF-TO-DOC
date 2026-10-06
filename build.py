"""Construye y prueba un ejecutable GUI autocontenido para la plataforma actual."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
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


def _benchmark_startup(executable: Path, output: Path) -> bool:
    output.unlink(missing_ok=True)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "benchmark_startup.py"),
            str(executable),
            "--runs",
            "10",
            "--cold-limit",
            "0.9",
            "--warm-limit",
            "0.45",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=False,
    )
    if result.returncode not in (0, 1) or not output.is_file():
        raise RuntimeError("No se pudo generar una medición de arranque válida.")
    measurement = json.loads(output.read_text(encoding="utf-8"))
    return result.returncode == 0 and bool(measurement["passed"])


def _archive(payload: Path, destination: Path) -> None:
    if destination.suffix == ".zip":
        with zipfile.ZipFile(
            destination,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as bundle:
            if payload.is_dir():
                for item in sorted(payload.rglob("*")):
                    if item.is_file():
                        bundle.write(item, arcname=Path(payload.name) / item.relative_to(payload))
            else:
                bundle.write(payload, arcname=payload.name)
        return

    with tarfile.open(destination, mode="w:gz") as bundle:
        bundle.add(payload, arcname=payload.name)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("onedir", "onefile"),
        default="onedir",
        help="PyInstaller layout; onedir is the primary distribution format.",
    )
    parser.add_argument(
        "--dist-directory",
        type=Path,
        default=ROOT / "dist",
        help="Output directory for the app and release archive.",
    )
    parser.add_argument(
        "--skip-startup-benchmark",
        action="store_true",
        help="Only smoke-test the app; reserved for packaging-mode comparisons.",
    )
    return parser.parse_args()


def main() -> int:
    from PyInstaller.__main__ import run as run_pyinstaller

    options = _parse_args()
    with (ROOT / "pyproject.toml").open("rb") as project_file:
        version = tomllib.load(project_file)["project"]["version"]
    system, architecture = _target_platform()
    dist_directory = options.dist_directory.resolve()
    build_directory = ROOT / "build"
    dist_directory.mkdir(parents=True, exist_ok=True)
    build_directory.mkdir(parents=True, exist_ok=True)

    arguments = [
        "--clean",
        "--noconfirm",
        "--windowed",
        "--noupx",
        "--name",
        APP_NAME,
        "--distpath",
        str(dist_directory),
        "--workpath",
        str(build_directory / "pyinstaller" / options.mode),
        "--specpath",
        str(build_directory),
        "--paths",
        str(ROOT),
    ]
    arguments.append(f"--{options.mode}")
    for stylesheet in ("styles.qss", "styles_dark.qss"):
        arguments.extend(
            [
                "--add-data",
                f"{ROOT / 'app' / 'ui' / stylesheet}{os.pathsep}app/ui",
            ]
        )
    app_icon = APP_ICONS[system]
    if not app_icon.is_file():
        raise FileNotFoundError(f"No se encontró el icono de aplicación: {app_icon}")
    arguments.extend(["--icon", str(app_icon)])
    arguments.append(str(ROOT / "app" / "ui" / "launcher.py"))
    run_pyinstaller(arguments)

    executable_name = f"{APP_NAME}.exe" if system == "windows" else APP_NAME
    executable = dist_directory / executable_name
    payload = executable
    if system == "macos":
        payload = dist_directory / f"{APP_NAME}.app"
        executable = payload / "Contents" / "MacOS" / APP_NAME
    if not executable.is_file():
        raise FileNotFoundError(f"PyInstaller no creó el ejecutable esperado: {executable}")

    startup_passed = True
    if options.skip_startup_benchmark:
        _smoke_test(executable)
    else:
        startup_passed = _benchmark_startup(
            executable,
            dist_directory / "startup-benchmark.json",
        )
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
    benchmark_path = dist_directory / "startup-benchmark.json"
    if not options.skip_startup_benchmark:
        benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
        benchmark["archive"] = artifact.name
        benchmark["archive_size_bytes"] = artifact.stat().st_size
        benchmark_path.write_text(
            json.dumps(benchmark, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if system == "macos":
            app_launcher = dist_directory / APP_NAME
            if app_launcher.is_dir() and (app_launcher / "_internal").is_dir():
                shutil.rmtree(app_launcher)
            elif app_launcher.is_file() or app_launcher.is_symlink():
                app_launcher.unlink(missing_ok=True)

    print(f"Aplicación verificada: {payload}")
    print(f"Artefacto de distribución: {artifact}")
    print(f"Checksum SHA-256: {checksum_manifest}")
    if not options.skip_startup_benchmark:
        print(f"Benchmark de arranque: {benchmark_path}")
    if not startup_passed:
        print(
            "La aplicación se empaquetó, pero excedió el presupuesto de arranque.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
