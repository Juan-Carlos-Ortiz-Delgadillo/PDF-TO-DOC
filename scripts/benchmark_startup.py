"""Mide el tiempo desde el lanzamiento del proceso hasta el primer paint de Qt."""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def _bundle_path(executable: Path) -> Path:
    if executable.parent.name == "MacOS" and executable.parent.parent.name == "Contents":
        return executable.parent.parent.parent
    if executable.is_dir():
        return executable
    if (executable.parent / "_internal").is_dir():
        return executable.parent
    return executable


def _path_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    seen_files: set[tuple[int, int]] = set()
    total_size = 0
    for item in path.rglob("*"):
        if not item.is_file():
            continue
        metadata = item.stat()
        identity = (metadata.st_dev, metadata.st_ino)
        if identity not in seen_files:
            seen_files.add(identity)
            total_size += metadata.st_size
    return total_size


def _measure_launch(executable: Path, *, timeout: float) -> tuple[float, float]:
    with tempfile.TemporaryDirectory(prefix="pdf2word-startup-") as temporary_directory:
        marker_path = Path(temporary_directory) / "first-paint.txt"
        ready_marker_path = Path(temporary_directory) / "main-window-ready.txt"
        environment = os.environ.copy()
        environment["PDF2WORD_STARTUP_MARKER"] = str(marker_path)
        environment["PDF2WORD_READY_MARKER"] = str(ready_marker_path)
        environment["QT_QPA_PLATFORM"] = "offscreen"
        started_ns = time.monotonic_ns()
        process = subprocess.Popen(
            [str(executable)],
            cwd=Path(__file__).resolve().parents[1],
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            marker_deadline = time.monotonic() + timeout
            first_paint_seconds: float | None = None
            while time.monotonic() < marker_deadline:
                if first_paint_seconds is None and marker_path.is_file():
                    marker = marker_path.read_text(encoding="ascii").strip()
                    if marker:
                        painted_ns = int(marker)
                        first_paint_seconds = (painted_ns - started_ns) / 1_000_000_000
                if first_paint_seconds is not None and ready_marker_path.is_file():
                    marker = ready_marker_path.read_text(encoding="ascii").strip()
                    if marker:
                        ready_ns = int(marker)
                        ready_seconds = (ready_ns - started_ns) / 1_000_000_000
                        return first_paint_seconds, ready_seconds
                return_code = process.poll()
                if return_code is not None:
                    stderr = process.stderr.read() if process.stderr is not None else ""
                    raise RuntimeError(
                        f"El ejecutable terminó antes de que la ventana principal "
                        f"estuviera lista (código {return_code}).\n{stderr}"
                    )
                time.sleep(0.005)
            if first_paint_seconds is None:
                raise TimeoutError(
                    f"No se detectó el primer paint en {timeout:.1f} s: {executable}"
                )
            raise TimeoutError(
                f"La ventana principal no estuvo lista en {timeout:.1f} s: {executable}"
            )
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            if process.stderr is not None:
                process.stderr.close()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path, help="Ejecutable GUI empaquetado.")
    parser.add_argument("--runs", type=int, default=10, help="Lanzamientos (mínimo 10).")
    parser.add_argument("--timeout", type=float, default=15.0, help="Timeout por lanzamiento.")
    parser.add_argument("--output", type=Path, help="Ruta de salida JSON.")
    parser.add_argument(
        "--cold-limit",
        type=float,
        default=1.0,
        help="Límite en segundos para el primer lanzamiento de proceso.",
    )
    parser.add_argument(
        "--warm-limit",
        type=float,
        default=0.5,
        help="Límite en segundos para la mediana de los lanzamientos restantes.",
    )
    arguments = parser.parse_args()
    if arguments.runs < 10:
        parser.error("--runs debe ser al menos 10.")
    if not arguments.executable.is_file():
        parser.error(f"No se encuentra el ejecutable: {arguments.executable}")
    return arguments


def main() -> int:
    arguments = _parse_args()
    executable = arguments.executable.resolve()
    sample_pairs = [
        _measure_launch(executable, timeout=arguments.timeout)
        for _ in range(arguments.runs)
    ]
    first_paint_samples = [sample[0] for sample in sample_pairs]
    ready_samples = [sample[1] for sample in sample_pairs]
    warm_first_paint_samples = first_paint_samples[1:]
    warm_ready_samples = ready_samples[1:]
    bundle_path = _bundle_path(executable)
    result = {
        "platform": platform.platform(),
        "platform_key": sys.platform,
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "executable": str(executable),
        "bundle": str(bundle_path),
        "bundle_size_bytes": _path_size(bundle_path),
        "executable_size_bytes": _path_size(executable),
        "metric": (
            "process launch to first completed Qt paint and main-window readiness "
            "(offscreen platform)"
        ),
        "cold_definition": (
            "first process launch after the build; operating-system filesystem cache "
            "is not guaranteed to be cold"
        ),
        "warm_definition": "subsequent independent launches of the same executable",
        "runs": len(sample_pairs),
        "first_paint_samples_seconds": first_paint_samples,
        "main_window_ready_samples_seconds": ready_samples,
        "cold_first_seconds": first_paint_samples[0],
        "warm_median_seconds": statistics.median(warm_first_paint_samples),
        "warm_p95_seconds": sorted(warm_first_paint_samples)[
            min(len(warm_first_paint_samples) - 1, int(0.95 * len(warm_first_paint_samples)))
        ],
        "main_window_ready_cold_seconds": ready_samples[0],
        "main_window_ready_warm_median_seconds": statistics.median(warm_ready_samples),
        "main_window_ready_warm_p95_seconds": sorted(warm_ready_samples)[
            min(len(warm_ready_samples) - 1, int(0.95 * len(warm_ready_samples)))
        ],
        "cold_limit_seconds": arguments.cold_limit,
        "warm_limit_seconds": arguments.warm_limit,
        "passed": first_paint_samples[0] < arguments.cold_limit
        and statistics.median(warm_first_paint_samples) < arguments.warm_limit,
    }
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if arguments.output is None:
        print(output, end="")
    else:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(output, encoding="utf-8")
        print(output, end="")
    if not result["passed"]:
        print(
            "Startup budget exceeded: "
            f"first={first_paint_samples[0]:.3f}s (limit {arguments.cold_limit:.3f}s), "
            f"warm median={result['warm_median_seconds']:.3f}s "
            f"(limit {arguments.warm_limit:.3f}s).",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
