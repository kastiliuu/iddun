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
