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
