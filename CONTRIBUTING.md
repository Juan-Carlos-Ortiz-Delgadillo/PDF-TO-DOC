# Contribuir

Usa Python 3.12. Instala el proyecto y las herramientas de desarrollo con `python -m pip install -e ".[dev]"`.

Antes de enviar cambios, ejecuta:

```bash
ruff check app tests build.py
mypy
pytest --cov=app.core --cov=app.models --cov=app.services --cov=app.utils --cov-fail-under=80
bandit -q -r app -ll
pip-audit --skip-editable
```

Para probar la construcción nativa de tu plataforma, ejecuta `python build.py`. Conserva el nombre `PDF2Word` y los iconos de `assets/`; no los cambies sin una decisión explícita del mantenedor. El mantenedor confirma haber creado el icono y autoriza su redistribución pública con la aplicación.

En macOS, `./scripts/build-dmg.sh` construye la app, crea un DMG de arrastrar
a Applications y verifica su contenido. Usa `--skip-build` para empaquetar un
bundle existente. El fondo fuente está en `assets/dmg-background.svg`; la
distribución de Finder está en `scripts/dmgbuild_settings.py`. Tras editar el
fondo SVG, regenera `assets/dmg-background.png` con
`sips -s format png assets/dmg-background.svg --out assets/dmg-background.png`.
