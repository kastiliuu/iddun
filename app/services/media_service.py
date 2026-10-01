from pathlib import Path
from uuid import uuid4

from flask import current_app
from werkzeug.utils import secure_filename


ALLOWED_IMAGE_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp",
}

ALLOWED_CERTIFICATE_EXTENSIONS = (
    ALLOWED_IMAGE_EXTENSIONS
    | {"pdf"}
)

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_CERTIFICATE_BYTES = 8 * 1024 * 1024


def _stream_size(file_storage):
    stream = getattr(
        file_storage,
        "stream",
        None,
    )

    if (
        stream is None
        or not hasattr(stream, "seek")
    ):
        return None

    try:
        current = stream.tell()

        stream.seek(0, 2)
        size = stream.tell()
        stream.seek(current)

        return size
    except (OSError, AttributeError):
        return None


def _upload_root():
    return Path(
        current_app.config["UPLOAD_FOLDER"]
    ).resolve()


def _safe_upload_directory(folder):
    upload_root = _upload_root()

    target_dir = (
        upload_root
        / folder
    ).resolve()

    try:
        target_dir.relative_to(upload_root)
    except ValueError as exc:
        raise ValueError(
            "Destino de upload inválido."
        ) from exc

    return target_dir


def _stored_path_to_file(stored_path):
    if not isinstance(stored_path, str):
        return None

    normalized = (
        stored_path
        .replace("\\", "/")
        .strip()
    )

    if not normalized.startswith("uploads/"):
        return None

    relative_path = normalized.removeprefix(
        "uploads/"
    )

    if not relative_path:
        return None

    upload_root = _upload_root()

    candidate = (
        upload_root
        / relative_path
    ).resolve()

    try:
        candidate.relative_to(upload_root)
    except ValueError:
        return None

    return candidate


def save_uploaded_file(
    file_storage,
    folder,
    *,
    allowed_extensions,
    max_bytes,
    error_message,
):
    if (
        not file_storage
        or not getattr(
            file_storage,
            "filename",
            None,
        )
    ):
        return None

    original = secure_filename(
        file_storage.filename
    )

    extension = (
        original.rsplit(".", 1)[-1].lower()
        if "." in original
        else ""
    )

    if extension not in allowed_extensions:
        raise ValueError(error_message)

    size = _stream_size(file_storage)

    if (
        size is not None
        and size > max_bytes
    ):
        max_megabytes = (
            max_bytes
            // (1024 * 1024)
        )

        raise ValueError(
            "O arquivo deve ter no máximo "
            f"{max_megabytes} MB."
        )

    target_dir = _safe_upload_directory(
        folder
    )

    target_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    filename = (
        f"{uuid4().hex}.{extension}"
    )

    target_path = (
        target_dir
        / filename
    )

    temporary_path = (
        target_dir
        / (
            f".{filename}."
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
            max_megabytes = (
                max_bytes
                // (1024 * 1024)
            )

            raise ValueError(
                "O arquivo deve ter no máximo "
                f"{max_megabytes} MB."
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

    return (
        f"uploads/{folder}/{filename}"
    )


def save_uploaded_image(
    file_storage,
    folder,
):
    return save_uploaded_file(
        file_storage,
        folder,
        allowed_extensions=(
            ALLOWED_IMAGE_EXTENSIONS
        ),
        max_bytes=MAX_IMAGE_BYTES,
        error_message=(
            "Use uma imagem JPG, PNG ou WEBP."
        ),
    )


def save_uploaded_certificate(
    file_storage,
    folder="professionals/certificates",
):
    return save_uploaded_file(
        file_storage,
        folder,
        allowed_extensions=(
            ALLOWED_CERTIFICATE_EXTENSIONS
        ),
        max_bytes=MAX_CERTIFICATE_BYTES,
        error_message=(
            "Use PDF, JPG, PNG ou WEBP "
            "para o certificado."
        ),
    )


def delete_uploaded_file(stored_path):
    target_path = _stored_path_to_file(
        stored_path
    )

    if target_path is None:
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


def delete_uploaded_files(stored_paths):
    removed = []

    for stored_path in reversed(
        list(stored_paths or [])
    ):
        if delete_uploaded_file(stored_path):
            removed.append(stored_path)

    return removed


class UploadBatch:
    def __init__(self):
        self._stored_paths = []
        self._committed = False

    @property
    def stored_paths(self):
        return tuple(
            self._stored_paths
        )

    def track(self, stored_path):
        if stored_path:
            self._stored_paths.append(
                stored_path
            )

        return stored_path

    def save_image(
        self,
        file_storage,
        folder,
    ):
        return self.track(
            save_uploaded_image(
                file_storage,
                folder,
            )
        )

    def save_certificate(
        self,
        file_storage,
        folder="professionals/certificates",
    ):
        return self.track(
            save_uploaded_certificate(
                file_storage,
                folder,
            )
        )

    def save_many_images(
        self,
        files,
        folder,
        max_files=8,
    ):
        selected = [
            item
            for item in (files or [])
            if (
                item
                and getattr(
                    item,
                    "filename",
                    "",
                )
            )
        ][:max_files]

        return [
            self.save_image(
                item,
                folder,
            )
            for item in selected
        ]

    def commit(self):
        self._committed = True

    def rollback(self):
        delete_uploaded_files(
            self._stored_paths
        )

        self._stored_paths.clear()
        self._committed = False

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        _exc_value,
        _traceback,
    ):
        if (
            exc_type is not None
            or not self._committed
        ):
            self.rollback()

        return False