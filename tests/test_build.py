from __future__ import annotations

import tarfile
import tomllib
import zipfile
from pathlib import Path
from runpy import run_path

_archive = run_path(Path(__file__).resolve().parents[1] / "build.py")["_archive"]
_packaged_paths = run_path(Path(__file__).resolve().parents[1] / "build.py")[
    "_packaged_paths"
]
PROJECT_FILE = Path(__file__).resolve().parents[1] / "pyproject.toml"


def test_archive_includes_onedir_tree_in_zip(tmp_path: Path) -> None:
    payload = tmp_path / "PDF2Word"
    internal = payload / "_internal"
    internal.mkdir(parents=True)
    (payload / "PDF2Word.exe").write_bytes(b"exe")
    (internal / "QtCore.dll").write_bytes(b"qt")
    destination = tmp_path / "package.zip"

    _archive(payload, destination)

    with zipfile.ZipFile(destination) as archive:
        assert archive.namelist() == [
            "PDF2Word/PDF2Word.exe",
            "PDF2Word/_internal/QtCore.dll",
        ]


def test_archive_includes_onedir_tree_in_tarball(tmp_path: Path) -> None:
    payload = tmp_path / "PDF2Word.app"
    contents = payload / "Contents" / "MacOS"
    contents.mkdir(parents=True)
    (contents / "PDF2Word").write_bytes(b"app")
    destination = tmp_path / "package.tar.gz"

    _archive(payload, destination)

    with tarfile.open(destination, "r:gz") as archive:
        assert archive.getnames() == [
            "PDF2Word.app",
            "PDF2Word.app/Contents",
            "PDF2Word.app/Contents/MacOS",
            "PDF2Word.app/Contents/MacOS/PDF2Word",
        ]


def test_packaged_paths_match_pyinstaller_output_layout(tmp_path: Path) -> None:
    cases = [
        ("linux", "onedir", "PDF2Word", "PDF2Word/PDF2Word"),
        ("windows", "onedir", "PDF2Word", "PDF2Word/PDF2Word.exe"),
        ("linux", "onefile", "PDF2Word", "PDF2Word"),
        ("windows", "onefile", "PDF2Word.exe", "PDF2Word.exe"),
        (
            "macos",
            "onedir",
            "PDF2Word.app",
            "PDF2Word.app/Contents/MacOS/PDF2Word",
        ),
    ]

    for system, mode, expected_payload, expected_executable in cases:
        payload, executable = _packaged_paths(
            tmp_path,
            system=system,
            mode=mode,
        )
        assert payload == tmp_path / expected_payload
        assert executable == tmp_path / expected_executable


def test_critical_conversion_distributions_remain_declared() -> None:
    with PROJECT_FILE.open("rb") as project_file:
        project = tomllib.load(project_file)["project"]
    dependency_names = {
        requirement.partition("==")[0].casefold().replace("_", "-")
        for requirement in project["dependencies"]
    }

    assert dependency_names >= {
        "pdf2docx",
        "pymupdf",
        "python-docx",
        "numpy",
        "opencv-python-headless",
        "fonttools",
        "fire",
        "lxml",
    }
