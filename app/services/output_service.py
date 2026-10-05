"""Validación y publicación segura de documentos DOCX."""

from __future__ import annotations

import errno
import os
import shutil
import tempfile
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO

from app.core.exceptions import OutputPermissionError, OutputValidationError


class OutputService:
    """Crea, valida y publica resultados DOCX sin sobrescrituras accidentales.

    Los archivos temporales se crean en la carpeta de destino. Eso permite
    validar por completo el DOCX antes de una publicación atómica (o una
    publicación exclusiva cuando no se autorizó sobrescribir un resultado).
    """

    _REQUIRED_DOCX_MEMBERS = frozenset({"[Content_Types].xml", "word/document.xml"})

    def __init__(self, *, minimum_size_bytes: int = 32) -> None:
        if minimum_size_bytes < 4:
            raise ValueError("minimum_size_bytes debe ser al menos 4")
        self._minimum_size_bytes = minimum_size_bytes
        self._temporary_paths: set[Path] = set()

    def ensure_output_directory(self, directory: Path, *, create: bool = False) -> Path:
        """Comprueba que una carpeta de salida existe y es utilizable.

        ``create`` se reserva para una acción explícita de la interfaz; no se
        crean carpetas implícitamente al convertir un documento.
        """

        output_directory = Path(directory).expanduser()
        try:
            if output_directory.exists():
                if not output_directory.is_dir():
                    raise OutputValidationError(
                        "La ubicación de salida no es una carpeta.",
                        diagnostic_message="La ruta de salida existe pero no es un directorio.",
                        error_code="output_directory_not_directory",
                    )
            elif create:
                output_directory.mkdir(parents=True, exist_ok=False)
            else:
                raise OutputValidationError(
                    "La carpeta de salida no existe.",
                    diagnostic_message=(
                        "No se creó una carpeta de salida sin autorización "
                        "explícita."
                    ),
                    error_code="output_directory_missing",
                )
        except OutputValidationError:
            raise
        except (OSError, ValueError) as error:
            raise OutputPermissionError(
                "No se pudo preparar la carpeta de salida.",
                diagnostic_message=self._diagnostic_for(error),
                error_code="output_directory_unavailable",
            ) from error
        return output_directory

    def validate_destination(
        self,
        destination: Path,
        *,
        overwrite_confirmed: bool = False,
        create_directory: bool = False,
    ) -> Path:
        """Valida una ruta final sin escribir ni sobrescribir archivos."""

        output_path = Path(destination).expanduser()
        if not output_path.name or output_path.name in {".", ".."}:
            raise OutputValidationError(
                "Indica un nombre válido para el documento Word.",
                diagnostic_message="La ruta de salida no contiene un nombre de archivo válido.",
                error_code="invalid_output_name",
            )
        if output_path.suffix.lower() != ".docx":
            raise OutputValidationError(
                "El archivo de salida debe usar la extensión .docx.",
                diagnostic_message="La extensión de salida no es .docx.",
                error_code="invalid_output_extension",
            )

        self.ensure_output_directory(output_path.parent, create=create_directory)
        try:
            if output_path.exists():
                if not output_path.is_file():
                    raise OutputValidationError(
                        "La ruta de salida ya está ocupada por una carpeta u otro tipo de archivo.",
                        diagnostic_message=(
                            "La ruta de destino existe pero no es un archivo regular."
                        ),
                        error_code="output_destination_not_file",
                    )
                if not overwrite_confirmed:
                    raise OutputValidationError(
                        "Ya existe un archivo con ese nombre. Confirma si deseas sobrescribirlo.",
                        diagnostic_message=(
                            "Se rechazó una sobrescritura sin autorización explícita."
                        ),
                        error_code="output_exists",
                    )
        except OutputValidationError:
            raise
        except (OSError, ValueError) as error:
            raise OutputPermissionError(
                "No se pudo comprobar la ubicación de salida.",
                diagnostic_message=self._diagnostic_for(error),
                error_code="output_destination_unavailable",
            ) from error
        return output_path

    def create_temporary_output(
        self,
        destination: Path,
        *,
        overwrite_confirmed: bool = False,
        create_directory: bool = False,
    ) -> Path:
        """Reserva un DOCX temporal, en la misma carpeta del destino final."""

        output_path = self.validate_destination(
            destination,
            overwrite_confirmed=overwrite_confirmed,
            create_directory=create_directory,
        )
        prefix = f".{output_path.stem}.pdf2word-"
        try:
            descriptor, raw_path = tempfile.mkstemp(
                prefix=prefix,
                suffix=".docx",
                dir=output_path.parent,
            )
            os.close(descriptor)
        except (OSError, ValueError) as error:
            raise OutputPermissionError(
                "No se pudo crear un archivo temporal en la carpeta de salida.",
                diagnostic_message=self._diagnostic_for(error),
                error_code="output_temp_create_failed",
            ) from error

        temporary_path = Path(raw_path)
        self._temporary_paths.add(temporary_path)
        return temporary_path

    @contextmanager
    def temporary_output(
        self,
        destination: Path,
        *,
        overwrite_confirmed: bool = False,
        create_directory: bool = False,
    ) -> Iterator[Path]:
        """Expone un temporal y lo elimina si no llega a publicarse."""

        temporary_path = self.create_temporary_output(
            destination,
            overwrite_confirmed=overwrite_confirmed,
            create_directory=create_directory,
        )
        try:
            yield temporary_path
        finally:
            self.cleanup_temporary(temporary_path)

    def validate_docx(self, path: Path) -> Path:
        """Comprueba estructura ZIP y legibilidad mediante ``python-docx``."""

        docx_path = Path(path).expanduser()
        try:
            if not docx_path.exists() or not docx_path.is_file():
                raise OutputValidationError(
                    "No se generó el documento Word esperado.",
                    diagnostic_message="El archivo DOCX temporal no existe o no es regular.",
                    error_code="docx_missing",
                )
            if docx_path.stat().st_size < self._minimum_size_bytes:
                raise OutputValidationError(
                    "El documento Word generado está incompleto.",
                    diagnostic_message=(
                        "El tamaño del DOCX es menor que el mínimo estructural "
                        "esperado."
                    ),
                    error_code="docx_too_small",
                )
            with docx_path.open("rb") as document_file:
                if document_file.read(4) != b"PK\x03\x04":
                    raise OutputValidationError(
                        "El resultado generado no es un documento Word válido.",
                        diagnostic_message=(
                            "El archivo no empieza con la firma ZIP esperada para DOCX."
                        ),
                        error_code="docx_invalid_signature",
                    )
            with zipfile.ZipFile(docx_path) as archive:
                member_names = set(archive.namelist())
                if not self._REQUIRED_DOCX_MEMBERS.issubset(member_names):
                    raise OutputValidationError(
                        "El resultado generado no contiene la estructura esperada de Word.",
                        diagnostic_message=(
                            "Faltan miembros obligatorios dentro del contenedor DOCX."
                        ),
                        error_code="docx_missing_required_members",
                    )
                invalid_member = archive.testzip()
                if invalid_member is not None:
                    raise OutputValidationError(
                        "El documento Word generado está dañado.",
                        diagnostic_message="El CRC ZIP falló para un miembro del DOCX.",
                        error_code="docx_zip_crc_error",
                    )
        except OutputValidationError:
            raise
        except (OSError, ValueError, zipfile.BadZipFile, zipfile.LargeZipFile) as error:
            raise OutputValidationError(
                "No se pudo validar el documento Word generado.",
                diagnostic_message=self._diagnostic_for(error),
                error_code="docx_structure_invalid",
            ) from error

        self._validate_with_python_docx(docx_path)
        return docx_path

    def publish(
        self,
        temporary_path: Path,
        destination: Path,
        *,
        overwrite_confirmed: bool = False,
    ) -> Path:
        """Valida y publica un DOCX temporal de forma controlada.

        Con sobrescritura confirmada se usa ``os.replace`` después de validar
        el temporal. Sin esa autorización, intenta publicar mediante enlace
        exclusivo para no reemplazar un archivo que aparezca entre la
        comprobación inicial y la publicación.
        """

        output_path = self.validate_destination(
            destination,
            overwrite_confirmed=overwrite_confirmed,
        )
        source_path = Path(temporary_path).expanduser()
        if source_path == output_path:
            raise OutputValidationError(
                "El archivo temporal no puede ser el mismo que el destino final.",
                diagnostic_message="La ruta temporal y la ruta de publicación coinciden.",
                error_code="output_temp_equals_destination",
            )

        try:
            same_directory = source_path.parent.resolve() == output_path.parent.resolve()
        except (OSError, RuntimeError):
            same_directory = source_path.parent == output_path.parent
        if not same_directory:
            raise OutputValidationError(
                "El archivo temporal debe estar en la carpeta de salida.",
                diagnostic_message=(
                    "No se publica un resultado temporal desde otro sistema de archivos."
                ),
                error_code="output_temp_wrong_directory",
            )

        try:
            self.validate_docx(source_path)
            if overwrite_confirmed:
                os.replace(source_path, output_path)
            else:
                self._publish_exclusively(source_path, output_path)
        except OutputValidationError:
            self.cleanup_temporary(source_path)
            raise
        except PermissionError as error:
            self.cleanup_temporary(source_path)
            raise OutputPermissionError(
                "No se pudo escribir el documento Word en la carpeta seleccionada.",
                diagnostic_message=self._diagnostic_for(error),
                error_code="output_permission_denied",
            ) from error
        except OSError as error:
            self.cleanup_temporary(source_path)
            raise OutputValidationError(
                "No se pudo publicar el documento Word generado.",
                diagnostic_message=self._diagnostic_for(error),
                error_code="output_publish_failed",
            ) from error

        self._temporary_paths.discard(source_path)
        return output_path

    def validate_and_publish(
        self,
        temporary_path: Path,
        destination: Path,
        *,
        overwrite_confirmed: bool = False,
    ) -> Path:
        """Alias explícito para el flujo normal de validación y publicación."""

        return self.publish(
            temporary_path,
            destination,
            overwrite_confirmed=overwrite_confirmed,
        )

    def cleanup_temporary(self, path: Path) -> None:
        """Elimina un temporal creado por este servicio, si sigue presente."""

        temporary_path = Path(path)
        if temporary_path not in self._temporary_paths:
            return
        try:
            temporary_path.unlink(missing_ok=True)
        except (OSError, ValueError):
            # Un fallo de limpieza no debe borrar ni sustituir el resultado
            # principal. El orquestador puede registrarlo como incidencia.
            return
        finally:
            self._temporary_paths.discard(temporary_path)

    def _validate_with_python_docx(self, docx_path: Path) -> None:
        try:
            from docx import Document
            from docx.opc.exceptions import PackageNotFoundError
        except ImportError as error:
            raise OutputValidationError(
                "No se puede validar el documento Word porque falta python-docx.",
                diagnostic_message="No fue posible importar python-docx.",
                error_code="python_docx_unavailable",
            ) from error

        try:
            Document(docx_path)
        except (PackageNotFoundError, OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
            raise OutputValidationError(
                "El documento Word generado no se puede abrir correctamente.",
                diagnostic_message=self._diagnostic_for(error),
                error_code="docx_python_docx_unreadable",
            ) from error

    def _publish_exclusively(self, source_path: Path, output_path: Path) -> None:
        """Publica sin sobrescribir mediante enlace, con copia exclusiva como respaldo."""

        try:
            os.link(source_path, output_path)
        except FileExistsError as error:
            raise OutputValidationError(
                "Ya existe un archivo con ese nombre. Confirma si deseas sobrescribirlo.",
                diagnostic_message="La publicación exclusiva detectó un destino ya existente.",
                error_code="output_exists",
            ) from error
        except OSError as error:
            unsupported_link_errors = {
                errno.EPERM,
                errno.EOPNOTSUPP,
                errno.ENOTSUP,
                errno.EXDEV,
            }
            if error.errno not in unsupported_link_errors:
                raise
            self._copy_exclusively(source_path, output_path)
        else:
            source_path.unlink()

    @staticmethod
    def _copy_exclusively(source_path: Path, output_path: Path) -> None:
        """Copia a un nombre reservado de forma exclusiva cuando no hay enlaces."""

        descriptor: int | None = None
        created_stat: os.stat_result | None = None
        try:
            descriptor = os.open(output_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            created_stat = os.fstat(descriptor)
            with source_path.open("rb") as source, os.fdopen(
                descriptor,
                "wb",
                closefd=True,
            ) as target:
                descriptor = None
                OutputService._copy_stream(source, target)
                target.flush()
                os.fsync(target.fileno())
            source_path.unlink()
        except FileExistsError as error:
            raise OutputValidationError(
                "Ya existe un archivo con ese nombre. Confirma si deseas sobrescribirlo.",
                diagnostic_message="No se pudo reservar el destino de forma exclusiva.",
                error_code="output_exists",
            ) from error
        except BaseException:
            if descriptor is not None:
                os.close(descriptor)
            if created_stat is not None:
                try:
                    current_stat = output_path.stat()
                    if (
                        current_stat.st_dev == created_stat.st_dev
                        and current_stat.st_ino == created_stat.st_ino
                    ):
                        output_path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise

    @staticmethod
    def _copy_stream(source: BinaryIO, target: BinaryIO) -> None:
        shutil.copyfileobj(source, target, length=1024 * 1024)

    @staticmethod
    def _diagnostic_for(error: BaseException) -> str:
        return f"{type(error).__name__}: {str(error)[:300]}"
