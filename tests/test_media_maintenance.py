from pathlib import Path

from app.extensions import db
from app.models.profile import ClientProfile
from app.models.user import User, UserRole


def _write_upload(
    app,
    relative_path,
    content=b"file",
):
    path = (
        Path(app.config["UPLOAD_FOLDER"])
        / relative_path
    )
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_bytes(content)

    return path


def _create_referenced_avatar(
    app,
    stored_path,
):
    with app.app_context():
        user = User(
            name="Cliente mídia",
            email="media-cleanup@example.com",
            role=UserRole.CLIENT,
        )
        user.set_password(
            "senha-forte-123"
        )

        profile = ClientProfile(
            user=user,
            avatar_url=stored_path,
        )

        db.session.add_all(
            [user, profile]
        )
        db.session.commit()


def test_cleanup_media_dry_run_does_not_delete(
    app,
):
    referenced = (
        "uploads/clients/referenced.jpg"
    )
    orphan = (
        "uploads/clients/orphan.jpg"
    )

    referenced_file = _write_upload(
        app,
        "clients/referenced.jpg",
    )
    orphan_file = _write_upload(
        app,
        "clients/orphan.jpg",
    )
    _create_referenced_avatar(
        app,
        referenced,
    )

    runner = app.test_cli_runner()
    result = runner.invoke(
        args=["cleanup-media"]
    )

    assert result.exit_code == 0
    assert orphan in result.output
    assert referenced not in result.output
    assert "Nenhum arquivo foi removido" in result.output
    assert referenced_file.exists()
    assert orphan_file.exists()


def test_cleanup_media_delete_removes_only_orphans(
    app,
):
    referenced = (
        "uploads/clients/referenced.jpg"
    )
    orphan = (
        "uploads/clients/orphan.jpg"
    )

    referenced_file = _write_upload(
        app,
        "clients/referenced.jpg",
    )
    orphan_file = _write_upload(
        app,
        "clients/orphan.jpg",
    )
    _create_referenced_avatar(
        app,
        referenced,
    )

    runner = app.test_cli_runner()
    result = runner.invoke(
        args=[
            "cleanup-media",
            "--delete",
        ]
    )

    assert result.exit_code == 0
    assert referenced_file.exists()
    assert orphan_file.exists() is False
    assert "1 arquivo(s) removido(s)" in result.output


def test_cleanup_media_requires_explicit_production_override(
    app,
):
    orphan_file = _write_upload(
        app,
        "clients/orphan.jpg",
    )
    app.config["APP_ENV"] = "production"

    runner = app.test_cli_runner()
    result = runner.invoke(
        args=[
            "cleanup-media",
            "--delete",
        ]
    )

    assert result.exit_code != 0
    assert "Ambiente de produção bloqueado" in result.output
    assert orphan_file.exists()
