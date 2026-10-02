from pathlib import Path, PurePosixPath
from urllib.parse import urljoin
from uuid import uuid4

from flask import current_app, request, url_for


MEDIA_UPLOAD_PREFIX = "uploads/"


class MediaStorageFileTooLargeError(ValueError):
    def __init__(self, max_bytes):
        self.max_bytes = max_bytes
        super().__init__("O arquivo ultrapassa o limite permitido.")


def normalize_media_key(value):
    if not isinstance(value, str):
        return None

    normalized = value.replace("\\", "/").strip()

    if not normalized.startswith(MEDIA_UPLOAD_PREFIX):
        return None

    path = PurePosixPath(normalized)

    if (
        path.is_absolute()
        or ".." in path.parts
        or len(path.parts) < 2
        or path.parts[0] != "uploads"
    ):
        return None

    return path.as_posix()


class LocalMediaStorage:
    backend_name = "local"

    def __init__(self, upload_root):
        self.upload_root = Path(upload_root).resolve()

    def _target_path(self, stored_path):
        normalized = normalize_media_key(stored_path)

        if normalized is None:
            raise ValueError("Destino de upload inválido.")

        relative_path = normalized.removeprefix(
            MEDIA_UPLOAD_PREFIX
        )

        target_path = (
            self.upload_root
            / relative_path
        ).resolve()

        try:
            target_path.relative_to(
                self.upload_root
            )
        except ValueError as exc:
            raise ValueError(
                "Destino de upload inválido."
            ) from exc

        return target_path

    def save_upload(
        self,
        file_storage,
        stored_path,
        *,
        max_bytes,
    ):
        target_path = self._target_path(
            stored_path
        )

        target_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = (
            target_path.parent
            / (
                f".{target_path.name}."
                f"{uuid4().hex}.part"
            )
        )

        try:
            file_storage.save(
                temporary_path
            )

            if (
                temporary_path.stat().st_size
                > max_bytes
            ):
                raise MediaStorageFileTooLargeError(
                    max_bytes
                )

            temporary_path.replace(
                target_path
            )
        except Exception:
            temporary_path.unlink(
                missing_ok=True
            )

            target_path.unlink(
                missing_ok=True
            )

            raise

        return stored_path

    def list_stored_paths(self):
        if not self.upload_root.exists():
            return []

        stored_paths = []

        for path in self.upload_root.rglob("*"):
            if (
                not path.is_file()
                or path.name.startswith(".")
            ):
                continue

            relative = path.relative_to(
                self.upload_root
            ).as_posix()

            normalized = normalize_media_key(
                f"uploads/{relative}"
            )

            if normalized is not None:
                stored_paths.append(
                    normalized
                )

        return sorted(stored_paths)

    def delete(self, stored_path):
        try:
            target_path = self._target_path(
                stored_path
            )
        except ValueError:
            return False

        try:
            target_path.unlink(
                missing_ok=True
            )
        except OSError:
            current_app.logger.warning(
                (
                    "Não foi possível remover "
                    "o upload %s."
                ),
                stored_path,
                exc_info=True,
            )

            return False

        return True

    def public_url(
        self,
        stored_path,
        *,
        external=False,
    ):
        normalized = normalize_media_key(
            stored_path
        )

        if normalized is None:
            raise ValueError(
                "Caminho de mídia inválido."
            )

        return url_for(
            "static",
            filename=normalized,
            _external=external,
        )


def get_media_storage():
    backend = (
        current_app.config.get(
            "MEDIA_STORAGE_BACKEND",
            "local",
        )
        or "local"
    ).strip().lower()

    if backend == "local":
        return LocalMediaStorage(
            current_app.config[
                "UPLOAD_FOLDER"
            ]
        )

    raise RuntimeError(
        (
            "Backend de mídia não suportado: "
            f"{backend}. "
            "Configure MEDIA_STORAGE_BACKEND=local "
            "até que um provider de object storage "
            "seja habilitado."
        )
    )


def resolve_media_url(
    value,
    *,
    external=False,
):
    if not value:
        return None

    if value.startswith(
        ("http://", "https://", "data:")
    ):
        return value

    if value.startswith("/"):
        if not external:
            return value

        return urljoin(
            request.host_url,
            value.lstrip("/"),
        )

    if normalize_media_key(value):
        return get_media_storage().public_url(
            value,
            external=external,
        )

    return url_for(
        "static",
        filename=value,
        _external=external,
    )
