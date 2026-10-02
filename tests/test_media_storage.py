from io import BytesIO
from pathlib import Path

import pytest
from flask import url_for
from werkzeug.datastructures import FileStorage

from app.services.media_service import (
    delete_uploaded_file,
    save_uploaded_image,
)
from app.services.media_storage import (
    get_media_storage,
    normalize_media_key,
    resolve_media_url,
)


def _file(
    filename="image.jpg",
    content=b"image-content",
):
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
