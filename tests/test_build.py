from __future__ import annotations

import tarfile
import zipfile
from pathlib import Path
from runpy import run_path

_archive = run_path(Path(__file__).resolve().parents[1] / "build.py")["_archive"]


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
