from io import BytesIO
from uuid import uuid4
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError
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

IMAGE_FORMAT_BY_EXTENSION = {
    "jpg": "JPEG",
    "jpeg": "JPEG",
    "png": "PNG",
    "webp": "WEBP",
}

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_CERTIFICATE_BYTES = 8 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
MAX_IMAGE_SIDE = 8_192


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


def _read_upload_bytes(
    file_storage,
    max_bytes,
):
    stream = getattr(
        file_storage,
        "stream",
        None,
    )

    if stream is None:
        raise ValueError(
            "Não foi possível ler o arquivo enviado."
        )

    try:
        stream.seek(0)
        content = stream.read(
            max_bytes + 1
        )
        stream.seek(0)
    except (OSError, AttributeError) as exc:
        raise ValueError(
            "Não foi possível ler o arquivo enviado."
        ) from exc

    if len(content) > max_bytes:
        raise _maximum_size_error(
            max_bytes
        )

    return content


def _normalized_image_bytes(
    content,
    extension,
):
    expected_format = (
        IMAGE_FORMAT_BY_EXTENSION[
            extension
        ]
    )

    try:
        with warnings.catch_warnings():
            warnings.simplefilter(
                "error",
                Image.DecompressionBombWarning,
            )

            with Image.open(
                BytesIO(content)
            ) as probe:
                actual_format = probe.format

                if (
                    actual_format
                    != expected_format
                ):
                    raise ValueError(
                        (
                            "O conteúdo da imagem não "
                            "corresponde à extensão "
                            f".{extension}."
                        )
                    )

                if getattr(
                    probe,
                    "is_animated",
                    False,
                ):
                    raise ValueError(
                        (
                            "Imagens animadas não são "
                            "aceitas."
                        )
                    )

                width, height = probe.size

                if (
                    width <= 0
                    or height <= 0
                    or width > MAX_IMAGE_SIDE
                    or height > MAX_IMAGE_SIDE
                    or (
                        width * height
                        > MAX_IMAGE_PIXELS
                    )
                ):
                    raise ValueError(
                        (
                            "A imagem possui dimensões "
                            "maiores que o permitido."
                        )
                    )

                probe.verify()

            with Image.open(
                BytesIO(content)
            ) as source:
                image = ImageOps.exif_transpose(
                    source
                )
                image.load()

                if expected_format == "JPEG":
                    if image.mode not in (
                        "RGB",
                        "L",
                    ):
                        image = image.convert(
                            "RGB"
                        )

                output = BytesIO()

                save_options = {
                    "format": expected_format,
                }

                if expected_format == "JPEG":
                    save_options.update(
                        {
                            "quality": 88,
                            "optimize": True,
                            "progressive": True,
                        }
                    )
                elif expected_format == "PNG":
                    save_options.update(
                        {
                            "optimize": True,
                        }
                    )
                elif expected_format == "WEBP":
                    save_options.update(
                        {
                            "quality": 88,
                            "method": 4,
                        }
                    )

                image.save(
                    output,
                    **save_options,
                )

                return output.getvalue()
    except ValueError:
        raise
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        UnidentifiedImageError,
        OSError,
        SyntaxError,
    ) as exc:
        raise ValueError(
            (
                "O arquivo enviado não é uma "
                "imagem válida."
            )
        ) from exc


def _prepare_image_upload(
    file_storage,
    extension,
    max_bytes,
):
    content = _read_upload_bytes(
        file_storage,
        max_bytes,
    )

    normalized = _normalized_image_bytes(
        content,
        extension,
    )

    if len(normalized) > max_bytes:
        raise _maximum_size_error(
            max_bytes
        )

    file_storage.stream = BytesIO(
        normalized
    )


def _validate_pdf_upload(
    file_storage,
    max_bytes,
):
    content = _read_upload_bytes(
        file_storage,
        max_bytes,
    )

    if not content.startswith(
        b"%PDF-"
    ):
        raise ValueError(
            "O arquivo enviado não é um PDF válido."
        )


def save_uploaded_file(
    file_storage,
    folder,
    *,
    allowed_extensions,
    max_bytes,
    error_message,
    validate_content=True,
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

    if validate_content:
        if extension in (
            ALLOWED_IMAGE_EXTENSIONS
        ):
            _prepare_image_upload(
                file_storage,
                extension,
                max_bytes,
            )
        elif extension == "pdf":
            _validate_pdf_upload(
                file_storage,
                max_bytes,
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
