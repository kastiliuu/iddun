from uuid import uuid4

from werkzeug.utils import secure_filename

from app.services.media_storage import (
    MediaStorageFileTooLargeError,
    get_media_storage,
    normalize_media_key,
)


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


def _maximum_size_error(max_bytes):
    max_megabytes = (
        max_bytes
        // (1024 * 1024)
    )

    return ValueError(
        "O arquivo deve ter no máximo "
        f"{max_megabytes} MB."
    )


def _stored_path(folder, filename):
    value = (
        f"uploads/{folder}/{filename}"
        .replace("\\", "/")
    )

    normalized = normalize_media_key(
        value
    )

    if normalized is None:
        raise ValueError(
            "Destino de upload inválido."
        )

    return normalized


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
        raise _maximum_size_error(
            max_bytes
        )

    filename = (
        f"{uuid4().hex}.{extension}"
    )

    stored_path = _stored_path(
        folder,
        filename,
    )

    storage = get_media_storage()

    try:
        storage.save_upload(
            file_storage,
            stored_path,
            max_bytes=max_bytes,
        )
    except MediaStorageFileTooLargeError as exc:
        raise _maximum_size_error(
            exc.max_bytes
        ) from exc

    return stored_path


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
    if normalize_media_key(
        stored_path
    ) is None:
        return False

    return get_media_storage().delete(
        stored_path
    )


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
