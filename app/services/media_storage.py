from abc import ABC, abstractmethod
from io import BytesIO
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urljoin
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


class MediaStorage(ABC):
    backend_name = "unknown"

    @abstractmethod
    def save_upload(
        self,
        file_storage,
        stored_path,
        *,
        max_bytes,
    ):
        raise NotImplementedError

    @abstractmethod
    def exists(self, stored_path):
        raise NotImplementedError

    @abstractmethod
    def list_stored_paths(self):
        raise NotImplementedError

    @abstractmethod
    def delete(self, stored_path):
        raise NotImplementedError

    @abstractmethod
    def public_url(
        self,
        stored_path,
        *,
        external=False,
    ):
        raise NotImplementedError


class LocalMediaStorage(MediaStorage):
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

    def exists(self, stored_path):
        try:
            target_path = self._target_path(
                stored_path
            )
        except ValueError:
            return False

        return target_path.is_file()

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


def _create_s3_client(
    *,
    region,
    endpoint_url,
    access_key_id,
    secret_access_key,
):
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError(
            (
                "O backend s3 requer a dependência "
                "boto3 instalada."
            )
        ) from exc

    kwargs = {}

    if region:
        kwargs["region_name"] = region

    if endpoint_url:
        kwargs["endpoint_url"] = endpoint_url

    if access_key_id:
        kwargs[
            "aws_access_key_id"
        ] = access_key_id

    if secret_access_key:
        kwargs[
            "aws_secret_access_key"
        ] = secret_access_key

    return boto3.client(
        "s3",
        **kwargs,
    )


def _bounded_upload_stream(
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
        raise MediaStorageFileTooLargeError(
            max_bytes
        )

    return BytesIO(content)


class S3MediaStorage(MediaStorage):
    backend_name = "s3"

    def __init__(
        self,
        *,
        bucket,
        public_base_url,
        region=None,
        endpoint_url=None,
        access_key_id=None,
        secret_access_key=None,
        client=None,
    ):
        if not bucket:
            raise RuntimeError(
                "MEDIA_S3_BUCKET é obrigatório para o backend s3."
            )

        if not public_base_url:
            raise RuntimeError(
                (
                    "MEDIA_S3_PUBLIC_BASE_URL é obrigatório "
                    "para o backend s3."
                )
            )

        self.bucket = bucket
        self.public_base_url = (
            public_base_url.rstrip("/")
        )
        self.client = (
            client
            or _create_s3_client(
                region=region,
                endpoint_url=endpoint_url,
                access_key_id=access_key_id,
                secret_access_key=secret_access_key,
            )
        )

    def _key(self, stored_path):
        normalized = normalize_media_key(
            stored_path
        )

        if normalized is None:
            raise ValueError(
                "Caminho de mídia inválido."
            )

        return normalized

    def save_upload(
        self,
        file_storage,
        stored_path,
        *,
        max_bytes,
    ):
        key = self._key(
            stored_path
        )
        body = _bounded_upload_stream(
            file_storage,
            max_bytes,
        )

        content_type = (
            getattr(
                file_storage,
                "content_type",
                None,
            )
            or "application/octet-stream"
        )

        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
        )

        return stored_path

    def exists(self, stored_path):
        try:
            key = self._key(
                stored_path
            )
        except ValueError:
            return False

        try:
            self.client.head_object(
                Bucket=self.bucket,
                Key=key,
            )
            return True
        except Exception as exc:
            response = getattr(
                exc,
                "response",
                None,
            )

            if isinstance(response, dict):
                error = response.get(
                    "Error",
                    {},
                )
                code = str(
                    error.get(
                        "Code",
                        "",
                    )
                )

                if code in {
                    "404",
                    "NoSuchKey",
                    "NotFound",
                }:
                    return False

            raise

    def list_stored_paths(self):
        items = []
        continuation_token = None

        while True:
            kwargs = {
                "Bucket": self.bucket,
                "Prefix": MEDIA_UPLOAD_PREFIX,
            }

            if continuation_token:
                kwargs[
                    "ContinuationToken"
                ] = continuation_token

            response = (
                self.client.list_objects_v2(
                    **kwargs
                )
            )

            for item in response.get(
                "Contents",
                [],
            ):
                key = normalize_media_key(
                    item.get(
                        "Key"
                    )
                )

                if key is not None:
                    items.append(
                        key
                    )

            if not response.get(
                "IsTruncated"
            ):
                break

            continuation_token = (
                response.get(
                    "NextContinuationToken"
                )
            )

            if not continuation_token:
                break

        return sorted(
            set(items)
        )

    def delete(self, stored_path):
        try:
            key = self._key(
                stored_path
            )
        except ValueError:
            return False

        try:
            self.client.delete_object(
                Bucket=self.bucket,
                Key=key,
            )
        except Exception:
            current_app.logger.warning(
                (
                    "Não foi possível remover "
                    "o objeto %s do storage s3."
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
        del external

        key = self._key(
            stored_path
        )

        return (
            f"{self.public_base_url}/"
            f"{quote(key, safe='/')}"
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

    if backend in {
        "s3",
        "s3-compatible",
        "object-storage",
    }:
        return S3MediaStorage(
            bucket=current_app.config.get(
                "MEDIA_S3_BUCKET"
            ),
            public_base_url=(
                current_app.config.get(
                    "MEDIA_S3_PUBLIC_BASE_URL"
                )
            ),
            region=current_app.config.get(
                "MEDIA_S3_REGION"
            ),
            endpoint_url=(
                current_app.config.get(
                    "MEDIA_S3_ENDPOINT_URL"
                )
            ),
            access_key_id=(
                current_app.config.get(
                    "MEDIA_S3_ACCESS_KEY_ID"
                )
            ),
            secret_access_key=(
                current_app.config.get(
                    "MEDIA_S3_SECRET_ACCESS_KEY"
                )
            ),
        )

    raise RuntimeError(
        (
            "Backend de mídia não suportado: "
            f"{backend}. "
            "Use MEDIA_STORAGE_BACKEND=local "
            "ou MEDIA_STORAGE_BACKEND=s3."
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


def resolve_image_url(
    value,
    *,
    external=False,
    fallback_static="img/category-hair.jpg",
):
    fallback_url = url_for(
        "static",
        filename=fallback_static,
        _external=external,
    )

    if not value:
        return fallback_url

    if value.startswith(
        ("http://", "https://", "data:")
    ):
        return value

    normalized = normalize_media_key(
        value
    )

    if normalized is not None:
        storage = get_media_storage()

        if (
            storage.backend_name == "local"
            and not storage.exists(
                normalized
            )
        ):
            return fallback_url

        return storage.public_url(
            normalized,
            external=external,
        )

    return resolve_media_url(
        value,
        external=external,
    )
