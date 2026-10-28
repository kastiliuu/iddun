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


def test_audit_missing_finds_upload_and_strict_fails(app):
    missing = "uploads/clients/lost.jpg"
    _create_referenced_avatar(app, missing)
    result = app.test_cli_runner().invoke(args=["media", "audit-missing"])
    assert result.exit_code == 0
    assert "client_profiles" in result.output
    assert "avatar_url" in result.output
    assert missing in result.output
    strict = app.test_cli_runner().invoke(args=["media", "audit-missing", "--strict"])
    assert strict.exit_code != 0
    assert missing in strict.output


def test_audit_missing_skips_static_and_external_urls(app):
    from sqlalchemy import select

    with app.app_context():
        user = User(name="Cliente estático", email="static@example.com", role=UserRole.CLIENT)
        user.set_password("senha-forte-123")
        db.session.add_all([
            user,
            ClientProfile(user=user, avatar_url="/static/img/default.jpg"),
        ])
        db.session.commit()
        profile = db.session.scalar(select(ClientProfile).where(ClientProfile.user_id == user.id))
        profile.avatar_url = "https://cdn.example.com/avatar.jpg"
        db.session.commit()
    result = app.test_cli_runner().invoke(args=["media", "audit-missing", "--strict"])
    assert result.exit_code == 0
    assert "Nenhuma mídia ausente" in result.output


def test_audit_missing_uses_s3_exists(app, monkeypatch):
    from app.services import media_maintenance

    missing = "uploads/clients/remote-lost.jpg"
    _create_referenced_avatar(app, missing)

    class FakeS3:
        backend_name = "s3"
        def exists(self, path):
            assert path == missing
            return False

    monkeypatch.setattr(media_maintenance, "get_media_storage", lambda: FakeS3())
    result = app.test_cli_runner().invoke(args=["media", "audit-missing", "--strict"])
    assert result.exit_code != 0
    assert missing in result.output
