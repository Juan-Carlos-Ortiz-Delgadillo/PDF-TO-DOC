"""Bootstrapping mínimo de la aplicación PDF2Word."""

from __future__ import annotations

import logging
from pathlib import Path

from app.core.config import ConfigRepository
from app.core.logger import configure_logging, get_logger


def bootstrap_application(*, config_path: str | Path | None = None) -> logging.Logger:
    """Prepara el entorno local de la aplicación."""

    repository = ConfigRepository(config_path) if config_path is not None else ConfigRepository()
    repository.load()
    logger = configure_logging(level=logging.INFO)
    logger.info("PDF2Word inicializado")
    return logger


def get_app_logger() -> logging.Logger:
    return get_logger("bootstrap")
