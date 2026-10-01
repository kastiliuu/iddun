from io import BytesIO
from pathlib import Path

import pytest
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.datastructures import FileStorage

from app.extensions import db
from app.models.profile import ClientProfile
from app.models.user import User, UserRole
from app.services.media_service import (
    UploadBatch,
    delete_uploaded_file,
    save_uploaded_image,
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


def _upload_files(app):
    upload_root = Path(
        app.config["UPLOAD_FOLDER"]
    )

    if not upload_root.exists():
        return []

    return sorted(
        path
        for path in upload_root.rglob("*")
        if path.is_file()
    )


def _create_user(
    app,
    email="media@example.com",
):
    with app.app_context():
        user = User(
            name="Profissional de mídia",
            email=email,
            role=UserRole.CLIENT,
        )
        user.set_password("senha-forte-123")

        db.session.add(user)
        db.session.flush()

        db.session.add(
            ClientProfile(user=user)
        )
        db.session.commit()

        return user.id


def _login_session(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


def _onboarding_payload():
    return {
        "display_name": "Profissional de mídia",
        "primary_specialty": "Hair Stylist",
        "bio": (
            "Profissional com experiência em "
            "atendimento, beleza e cuidado "
            "personalizado."
        ),
        "city": "Curitiba",
        "state": "PR",
        "visual_theme": "beauty",
        "avatar_file": (
            BytesIO(b"avatar"),
            "avatar.jpg",
        ),
        "portfolio_files": [
            (
                BytesIO(b"portfolio-1"),
                "portfolio-1.jpg",
            ),
            (
                BytesIO(b"portfolio-2"),
                "portfolio-2.jpg",
            ),
            (
                BytesIO(b"portfolio-3"),
                "portfolio-3.jpg",
            ),
        ],
    }


def test_upload_batch_commit_preserves_saved_files(
    app,
):
    with app.app_context():
        with UploadBatch() as uploads:
            stored_path = uploads.save_image(
                _file(),
                "professionals/portfolio",
            )
            uploads.commit()

        saved_files = _upload_files(app)

    assert stored_path.startswith(
        "uploads/professionals/portfolio/"
    )
    assert len(saved_files) == 1
    assert (
        saved_files[0].name
        == Path(stored_path).name
    )


def test_upload_batch_without_commit_removes_saved_files(
    app,
):
    with app.app_context():
        with UploadBatch() as uploads:
            uploads.save_image(
                _file(),
                "professionals/portfolio",
            )

        saved_files = _upload_files(app)

    assert saved_files == []


def test_upload_batch_rolls_back_previous_files_when_later_file_is_invalid(
    app,
):
    with app.app_context():
        with pytest.raises(
            ValueError,
            match="JPG, PNG ou WEBP",
        ):
            with UploadBatch() as uploads:
                uploads.save_image(
                    _file("valid.jpg"),
                    "professionals/portfolio",
                )
                uploads.save_image(
                    _file("invalid.exe"),
                    "professionals/portfolio",
                )

        saved_files = _upload_files(app)

    assert saved_files == []


def test_interrupted_save_removes_temporary_and_destination_files(
    app,
    monkeypatch,
):
    def interrupted_save(
        file_storage,
        destination,
    ):
        Path(destination).write_bytes(
            b"partial-content"
        )
        raise OSError(
            "storage unavailable"
        )

    monkeypatch.setattr(
        FileStorage,
        "save",
        interrupted_save,
    )

    with app.app_context():
        with pytest.raises(
            OSError,
            match="storage unavailable",
        ):
            save_uploaded_image(
                _file(),
                "professionals/portfolio",
            )

        saved_files = _upload_files(app)

    assert saved_files == []


def test_delete_uploaded_file_only_removes_local_uploads(
    app,
    tmp_path,
):
    outside_file = (
        tmp_path / "outside.jpg"
    )
    outside_file.write_bytes(b"outside")

    with app.app_context():
        stored_path = save_uploaded_image(
            _file(),
            "professionals/portfolio",
        )

        local_file = (
            Path(app.config["UPLOAD_FOLDER"])
            / stored_path.removeprefix(
                "uploads/"
            )
        )

        assert local_file.exists()
        assert (
            delete_uploaded_file(
                stored_path
            )
            is True
        )
        assert local_file.exists() is False

        assert (
            delete_uploaded_file(
                "https://example.com/image.jpg"
            )
            is False
        )
        assert (
            delete_uploaded_file(
                "uploads/../outside.jpg"
            )
            is False
        )

    assert outside_file.exists()


def test_onboarding_database_failure_rolls_back_new_uploads(
    app,
    client,
    monkeypatch,
):
    user_id = _create_user(app)
    _login_session(client, user_id)

    def fail_commit():
        raise SQLAlchemyError(
            "database unavailable"
        )

    monkeypatch.setattr(
        db.session,
        "commit",
        fail_commit,
    )

    response = client.post(
        "/pro/onboarding",
        data=_onboarding_payload(),
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert (
        "Não foi possível publicar seu perfil "
        "agora. Tente novamente."
        in response.get_data(as_text=True)
    )

    with app.app_context():
        saved_files = _upload_files(app)

    assert saved_files == []