"""Servicio de configuración persistente para la aplicación."""

from __future__ import annotations

from app.core.config import AppSettings, ConfigRepository


class SettingsService:
    """Abstracción ligera para recuperar y guardar la configuración local."""

    def __init__(self, repository: ConfigRepository | None = None) -> None:
        self._repository = repository or ConfigRepository()

    @property
    def repository(self) -> ConfigRepository:
        return self._repository

    def load(self) -> AppSettings:
        return self._repository.load()

    def save(self, settings: AppSettings) -> AppSettings:
        self._repository.save(settings)
        return settings

    def update(self, **updates: object) -> AppSettings:
        return self._repository.update(**updates)
