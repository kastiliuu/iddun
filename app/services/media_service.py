from pathlib import Path
from uuid import uuid4

from flask import current_app
from werkzeug.utils import secure_filename


ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
ALLOWED_CERTIFICATE_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | {"pdf"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_CERTIFICATE_BYTES = 8 * 1024 * 1024


def _stream_size(file_storage):
    stream = getattr(file_storage, "stream", None)
    if stream is None or not hasattr(stream, "seek"):
        return None
    try:
        current = stream.tell()
        stream.seek(0, 2)
        size = stream.tell()
        stream.seek(current)
        return size
    except (OSError, AttributeError):
        return None


def save_uploaded_file(file_storage, folder, *, allowed_extensions, max_bytes, error_message):
    if not file_storage or not getattr(file_storage, "filename", None):
        return None

    original = secure_filename(file_storage.filename)
    extension = original.rsplit(".", 1)[-1].lower() if "." in original else ""
    if extension not in allowed_extensions:
        raise ValueError(error_message)

    size = _stream_size(file_storage)
    if size is not None and size > max_bytes:
        raise ValueError(f"O arquivo deve ter no máximo {max_bytes // (1024 * 1024)} MB.")

    upload_root = Path(current_app.config["UPLOAD_FOLDER"])
    target_dir = upload_root / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}.{extension}"
    file_storage.save(target_dir / filename)
    return f"uploads/{folder}/{filename}"


def save_uploaded_image(file_storage, folder):
    return save_uploaded_file(
        file_storage,
        folder,
        allowed_extensions=ALLOWED_IMAGE_EXTENSIONS,
        max_bytes=MAX_IMAGE_BYTES,
        error_message="Use uma imagem JPG, PNG ou WEBP.",
    )


def save_uploaded_certificate(file_storage, folder="professionals/certificates"):
    return save_uploaded_file(
        file_storage,
        folder,
        allowed_extensions=ALLOWED_CERTIFICATE_EXTENSIONS,
        max_bytes=MAX_CERTIFICATE_BYTES,
        error_message="Use PDF, JPG, PNG ou WEBP para o certificado.",
    )
