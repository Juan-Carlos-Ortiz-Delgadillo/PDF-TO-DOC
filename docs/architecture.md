# Arquitectura de PDF2Word

## Principios

- Procesamiento local y sin telemetría.
- Separación entre UI, dominio y servicios externos.
- Dependencias inyectadas por constructor.
- Errores estructurados con mensajes seguros para la interfaz.

## Capas

1. UI: interacción con el usuario y presentación.
2. Servicios: validación, análisis, OCR y publicación de resultados.
3. Modelos: tipos inmutables para PDF, resultados y estados.
4. Core: configuración, logging y excepciones de dominio.
5. Utilidades: helpers de archivo/sistema y validación de entrada/salida.

## Decisiones principales

- Los servicios no dependen de cualquier widget de PySide6.
- La verificación de dependencias se hace localmente con comandos del sistema.
- El historial únicamente guarda metadatos y rutas, no contenido del documento.
- La salida final se valida con estructura DOCX antes de publicarse.
