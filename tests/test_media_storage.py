from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from flask import url_for
from werkzeug.datastructures import FileStorage

from app.services.media_service import (
    delete_uploaded_file,
    save_uploaded_image,
)
from app.services.media_storage import (
    MediaStorageFileTooLargeError,
    S3MediaStorage,
    get_media_storage,
    normalize_media_key,
    resolve_image_url,
    resolve_media_url,
)


def _file(
    filename="image.jpg",
    content=None,
):
    if content is None:
        output = BytesIO()
        Image.new(
            "RGB",
            (8, 8),
            (120, 80, 160),
        ).save(
            output,
            format="JPEG",
        )
        content = output.getvalue()

    return FileStorage(
        stream=BytesIO(content),
        filename=filename,
        content_type="image/jpeg",
    )


def test_normalize_media_key_accepts_only_upload_namespace():
    assert (
        normalize_media_key(
            "uploads/professionals/avatar.jpg"
        )
        == "uploads/professionals/avatar.jpg"
    )

    assert normalize_media_key(
        "img/category-hair.jpg"
    ) is None

    assert normalize_media_key(
        "uploads/../outside.jpg"
    ) is None

    assert normalize_media_key(
        "../uploads/outside.jpg"
    ) is None


def test_local_storage_keeps_existing_database_contract(
    app,
):
    with app.test_request_context("/"):
        stored_path = save_uploaded_image(
            _file(),
            "professionals/portfolio",
        )

        assert stored_path.startswith(
            "uploads/professionals/portfolio/"
        )

        disk_path = (
            Path(app.config["UPLOAD_FOLDER"])
            / stored_path.removeprefix(
                "uploads/"
            )
        )

        assert disk_path.exists()

        assert (
            resolve_media_url(stored_path)
            == url_for(
                "static",
                filename=stored_path,
            )
        )

        assert (
            delete_uploaded_file(
                stored_path
            )
            is True
        )

        assert disk_path.exists() is False


def test_media_url_can_be_absolute_for_mobile_api(
    app,
):
    with app.test_request_context(
        "/",
        base_url="https://iddun.example",
    ):
        url = resolve_media_url(
            "uploads/professionals/avatar.jpg",
            external=True,
        )

    assert (
        url
        == (
            "https://iddun.example/"
            "static/uploads/professionals/avatar.jpg"
        )
    )


def test_external_media_url_is_preserved(
    app,
):
    with app.test_request_context("/"):
        assert (
            resolve_media_url(
                "https://cdn.example.com/avatar.webp"
            )
            == "https://cdn.example.com/avatar.webp"
        )


def test_unknown_storage_backend_fails_explicitly(
    app,
):
    app.config[
        "MEDIA_STORAGE_BACKEND"
    ] = "future-provider"

    with app.app_context():
        with pytest.raises(
            RuntimeError,
            match="Backend de mídia não suportado",
        ):
            get_media_storage()



def test_local_storage_reports_file_existence(
    app,
):
    with app.test_request_context("/"):
        stored_path = save_uploaded_image(
            _file(),
            "professionals/avatar",
        )
        storage = get_media_storage()

        assert storage.exists(
            stored_path
        ) is True

        assert storage.exists(
            "uploads/professionals/missing.jpg"
        ) is False

        assert storage.exists(
            "uploads/../outside.jpg"
        ) is False


def test_missing_uploaded_image_uses_safe_fallback(
    app,
):
    with app.test_request_context(
        "/",
        base_url="https://iddun.example",
    ):
        url = resolve_image_url(
            "uploads/professionals/missing.jpg",
            external=True,
        )

    assert url == (
        "https://iddun.example/"
        "static/img/category-hair.jpg"
    )


def test_existing_uploaded_image_keeps_public_url(
    app,
):
    with app.test_request_context(
        "/",
        base_url="https://iddun.example",
    ):
        stored_path = save_uploaded_image(
            _file(),
            "professionals/avatar",
        )

        url = resolve_image_url(
            stored_path,
            external=True,
        )

    assert url.startswith(
        "https://iddun.example/"
        "static/uploads/professionals/avatar/"
    )


def test_external_image_url_skips_storage_lookup(
    app,
):
    with app.test_request_context("/"):
        assert (
            resolve_image_url(
                "https://cdn.example.com/avatar.webp"
            )
            == "https://cdn.example.com/avatar.webp"
        )


def test_local_storage_removes_oversized_partial_file(
    app,
):
    with app.app_context():
        storage = get_media_storage()
        stored_path = (
            "uploads/tests/oversized.jpg"
        )

        with pytest.raises(
            MediaStorageFileTooLargeError
        ):
            storage.save_upload(
                _file(
                    content=b"x" * 32
                ),
                stored_path,
                max_bytes=8,
            )

        assert storage.exists(
            stored_path
        ) is False



class _FakeNotFound(Exception):
    def __init__(self):
        self.response = {
            "Error": {
                "Code": "404",
            }
        }


class _FakeS3Client:
    def __init__(self):
        self.objects = {}
        self.deleted = []
        self.put_calls = []

    def put_object(
        self,
        *,
        Bucket,
        Key,
        Body,
        ContentType,
    ):
        content = Body.read()
        self.objects[
            (Bucket, Key)
        ] = content
        self.put_calls.append(
            {
                "Bucket": Bucket,
                "Key": Key,
                "ContentType": ContentType,
            }
        )

    def head_object(
        self,
        *,
        Bucket,
        Key,
    ):
        if (
            Bucket,
            Key,
        ) not in self.objects:
            raise _FakeNotFound()

        return {
            "ContentLength": len(
                self.objects[
                    (Bucket, Key)
                ]
            )
        }

    def list_objects_v2(
        self,
        **kwargs,
    ):
        bucket = kwargs[
            "Bucket"
        ]
        prefix = kwargs.get(
            "Prefix",
            "",
        )

        contents = [
            {
                "Key": key,
            }
            for (
                object_bucket,
                key,
            ) in self.objects
            if (
                object_bucket == bucket
                and key.startswith(prefix)
            )
        ]

        return {
            "Contents": contents,
            "IsTruncated": False,
        }

    def delete_object(
        self,
        *,
        Bucket,
        Key,
    ):
        self.deleted.append(
            (
                Bucket,
                Key,
            )
        )
        self.objects.pop(
            (
                Bucket,
                Key,
            ),
            None,
        )


def _s3_storage(
    client=None,
):
    return S3MediaStorage(
        bucket="iddun-media",
        public_base_url=(
            "https://media.example.com"
        ),
        region="auto",
        endpoint_url=(
            "https://object.example.com"
        ),
        access_key_id="test-key",
        secret_access_key="test-secret",
        client=client or _FakeS3Client(),
    )


def test_s3_storage_preserves_database_key_contract():
    client = _FakeS3Client()
    storage = _s3_storage(
        client
    )
    stored_path = (
        "uploads/professionals/avatar/test.jpg"
    )

    result = storage.save_upload(
        _file(),
        stored_path,
        max_bytes=1024 * 1024,
    )

    assert result == stored_path
    assert (
        client.objects[
            (
                "iddun-media",
                stored_path,
            )
        ]
    )
    assert client.put_calls[0][
        "ContentType"
    ] == "image/jpeg"


def test_s3_storage_exists_list_delete_and_public_url():
    client = _FakeS3Client()
    storage = _s3_storage(
        client
    )
    first = (
        "uploads/professionals/avatar/a.jpg"
    )
    second = (
        "uploads/posts/b.jpg"
    )

    client.objects[
        (
            "iddun-media",
            first,
        )
    ] = b"a"
    client.objects[
        (
            "iddun-media",
            second,
        )
    ] = b"b"

    assert storage.exists(
        first
    ) is True
    assert storage.exists(
        "uploads/missing.jpg"
    ) is False

    assert storage.list_stored_paths() == [
        second,
        first,
    ]

    assert storage.public_url(
        "uploads/posts/espaco legal.jpg"
    ) == (
        "https://media.example.com/"
        "uploads/posts/espaco%20legal.jpg"
    )

    assert storage.delete(
        first
    ) is True
    assert storage.exists(
        first
    ) is False


def test_s3_storage_rejects_oversized_upload():
    storage = _s3_storage()

    with pytest.raises(
        MediaStorageFileTooLargeError
    ):
        storage.save_upload(
            _file(
                content=b"x" * 32
            ),
            "uploads/tests/oversized.jpg",
            max_bytes=8,
        )


def test_s3_backend_factory_reads_app_configuration(
    app,
    monkeypatch,
):
    fake_client = _FakeS3Client()

    monkeypatch.setattr(
        (
            "app.services.media_storage."
            "_create_s3_client"
        ),
        lambda **_kwargs:
            fake_client,
    )

    app.config.update(
        MEDIA_STORAGE_BACKEND="s3",
        MEDIA_S3_BUCKET="iddun-media",
        MEDIA_S3_REGION="auto",
        MEDIA_S3_ENDPOINT_URL=(
            "https://object.example.com"
        ),
        MEDIA_S3_ACCESS_KEY_ID="key",
        MEDIA_S3_SECRET_ACCESS_KEY="secret",
        MEDIA_S3_PUBLIC_BASE_URL=(
            "https://media.example.com"
        ),
    )

    with app.app_context():
        storage = get_media_storage()

    assert isinstance(
        storage,
        S3MediaStorage,
    )
    assert (
        storage.bucket
        == "iddun-media"
    )


def test_s3_backend_requires_bucket_and_public_base_url(
    app,
):
    app.config.update(
        MEDIA_STORAGE_BACKEND="s3",
        MEDIA_S3_BUCKET=None,
        MEDIA_S3_PUBLIC_BASE_URL=None,
    )

    with app.app_context():
        with pytest.raises(
            RuntimeError,
            match="MEDIA_S3_BUCKET",
        ):
            get_media_storage()


def test_resolve_image_url_does_not_head_remote_storage(
    app,
    monkeypatch,
):
    class _NoHeadClient(
        _FakeS3Client
    ):
        def head_object(
            self,
            **_kwargs,
        ):
            raise AssertionError(
                "resolve_image_url não deve fazer HEAD remoto"
            )

    fake_client = _NoHeadClient()

    monkeypatch.setattr(
        (
            "app.services.media_storage."
            "_create_s3_client"
        ),
        lambda **_kwargs:
            fake_client,
    )

    app.config.update(
        MEDIA_STORAGE_BACKEND="s3",
        MEDIA_S3_BUCKET="iddun-media",
        MEDIA_S3_PUBLIC_BASE_URL=(
            "https://media.example.com"
        ),
    )

    with app.test_request_context("/"):
        url = resolve_image_url(
            "uploads/posts/photo.jpg"
        )

    assert url == (
        "https://media.example.com/"
        "uploads/posts/photo.jpg"
    )
