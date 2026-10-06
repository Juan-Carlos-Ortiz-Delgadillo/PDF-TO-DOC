from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

from app.core.config import AppSettings, ConfigRepository, OverwritePolicy, Theme
from app.core.logger import (
    SanitizingFormatter,
    configure_logging,
    get_default_log_path,
    sanitize_log_value,
    sanitize_text,
)


def test_config_repository_round_trips_and_recovers_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    repository = ConfigRepository(path)
    settings = AppSettings(
        theme=Theme.DARK,
        overwrite_policy=OverwritePolicy.OVERWRITE,
        output_directory=tmp_path,
        ocr_enabled=True,
    )
    assert repository.save(settings) == path
    assert repository.load() == settings
    updated = repository.update(ocr_language="eng")
    assert updated.ocr_language == "eng"

    path.write_text("{invalid", encoding="utf-8")
    assert repository.load() == AppSettings()
    with pytest.raises(ValueError):
        AppSettings.from_dict(None)
    with pytest.raises(TypeError):
        AppSettings(ocr_enabled="yes")  # type: ignore[arg-type]


def test_config_defaults_are_platform_aware(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    assert "Application Support" in str(ConfigRepository.default_path())
    assert "Library/Logs" in str(get_default_log_path())

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    assert ConfigRepository.default_path() == tmp_path / "config" / "pdf2word" / "settings.json"
    assert get_default_log_path() == tmp_path / "state" / "pdf2word" / "logs" / "pdf2word.log"


def test_log_sanitizer_handles_formatted_arguments_and_nested_values(tmp_path: Path) -> None:
    secret = "not-for-logs"
    sanitized = sanitize_text(f"token={secret} /private/folder/report.pdf")
    assert secret not in sanitized
    assert "report.pdf" in sanitized
    assert sanitize_log_value({"api_key": secret, "path": Path("/tmp/report.pdf")}) == {
        "api_key": "[REDACTADO]",
        "path": "report.pdf",
    }

    logger = configure_logging(tmp_path / "application.log", level=logging.INFO)
    logger.info("token=%s", secret)
    for handler in logger.handlers:
        handler.flush()
    assert secret not in (tmp_path / "application.log").read_text(encoding="utf-8")

    record = logging.LogRecord("test", logging.INFO, "", 1, "secret=%s", ("value",), None)
    assert "value" not in SanitizingFormatter("%(message)s").format(record)


def test_logger_rejects_invalid_rotation_parameters(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        configure_logging(tmp_path / "log.txt", max_bytes=0)
    with pytest.raises(ValueError):
        configure_logging(tmp_path / "log.txt", backup_count=-1)
