"""PR #252: real Alembic upgrade/downgrade and atomic personal media.

Run against disposable SQLite as well as the normal Flask test database.
No production data, upload or external services are used.
"""

import sqlite3

from app.extensions import db
from app.models.profile import ClientProfile
from app.models.professional import ProfessionalProfile
from app.models.user import User, UserRole
from app.services.personal_media_service import (
    set_personal_avatar,
    set_personal_cover,
)
from tests.test_identity_follow_migration import NOW, _flask


BEFORE = "a74c1r2p2026"


def test_additive_migration_backfills_without_erasing_old_profiles(tmp_path):
    db_path = tmp_path / "personal-media.db"
    before = _flask(db_path, "upgrade", BEFORE)
    assert before.returncode == 0, before.stderr

    with sqlite3.connect(db_path) as conn:
        for number, name in ((1, "Pessoa Um"), (2, "Pessoa Dois"), (3, "Pessoa Três")):
            conn.execute(
                "INSERT INTO users "
                "(id, name, email, username, password_hash, role, "
                "is_active_account, created_at, updated_at) "
                f"VALUES (?, ?, ?, ?, 'x', 'client', 1, {NOW}, {NOW})",
                (number, name, f"p{number}@example.com", f"pessoa{number}"),
            )
        for number, avatar in (
            (1, "uploads/clients/preferida.jpg"),
            (2, None),
            (3, None),
        ):
            conn.execute(
                "INSERT INTO client_profiles "
                "(id, user_id, avatar_url, onboarding_completed, created_at, updated_at) "
                f"VALUES (?, ?, ?, 0, {NOW}, {NOW})",
                (number, number, avatar),
            )
        for number, user_id, avatar, cover in (
            (11, 1, "uploads/professionals/outra.jpg", "uploads/professionals/capa.jpg"),
            (12, 2, "uploads/professionals/fallback.jpg", None),
            (13, None, "uploads/professionals/catalogo.jpg", None),
        ):
            conn.execute(
                "INSERT INTO professional_profiles "
                "(id, user_id, display_name, slug, avatar_url, cover_url, "
                "whatsapp_enabled, avatar_focus_x, avatar_focus_y, "
                "cover_focus_x, cover_focus_y, visual_theme, plan_tier, "
                "onboarding_completed, is_verified, is_active, timezone, "
                "default_booking_cutoff_minutes, created_at, updated_at) "
                f"VALUES (?, ?, ?, ?, ?, ?, 1, 50, 50, 50, 50, "
                f"'beauty', 'free', 0, 0, 1, 'America/Sao_Paulo', 60, {NOW}, {NOW})",
                (number, user_id, f"Pro {number}", f"pro-{number}", avatar, cover),
            )

    upgraded = _flask(db_path, "upgrade")
    assert upgraded.returncode == 0, upgraded.stderr
    with sqlite3.connect(db_path) as conn:
        actual = conn.execute(
            "SELECT id, avatar_url, cover_url FROM users ORDER BY id"
        ).fetchall()
        assert actual == [
            (1, "uploads/clients/preferida.jpg", "uploads/professionals/capa.jpg"),
            (2, "uploads/professionals/fallback.jpg", None),
            (3, None, None),
        ]
        # Dados de origem e catálogo permanecem intactos após o backfill.
        assert conn.execute(
            "SELECT avatar_url FROM professional_profiles WHERE id = 11"
        ).fetchone() == ("uploads/professionals/outra.jpg",)
        assert conn.execute(
            "SELECT avatar_url FROM professional_profiles WHERE id = 13"
        ).fetchone() == ("uploads/professionals/catalogo.jpg",)

        # Simula a política de dual-write do código após o upgrade.
        new_avatar = "uploads/clients/atualizada.jpg"
        new_cover = "uploads/professionals/capa-nova.jpg"
        conn.execute(
            "UPDATE users SET avatar_url = ?, cover_url = ? WHERE id = 1",
            (new_avatar, new_cover),
        )
        conn.execute(
            "UPDATE client_profiles SET avatar_url = ? WHERE user_id = 1",
            (new_avatar,),
        )
        conn.execute(
            "UPDATE professional_profiles SET avatar_url = ?, cover_url = ? WHERE user_id = 1",
            (new_avatar, new_cover),
        )

    down = _flask(db_path, "downgrade", BEFORE)
    assert down.returncode == 0, down.stderr
    with sqlite3.connect(db_path) as conn:
        columns = {item[1] for item in conn.execute("PRAGMA table_info(users)")}
        assert "avatar_url" not in columns and "cover_url" not in columns
        assert conn.execute(
            "SELECT avatar_url FROM client_profiles WHERE user_id = 1"
        ).fetchone() == ("uploads/clients/atualizada.jpg",)
        assert conn.execute(
            "SELECT avatar_url, cover_url FROM professional_profiles WHERE user_id = 1"
        ).fetchone() == (
            "uploads/clients/atualizada.jpg",
            "uploads/professionals/capa-nova.jpg",
        )

    again = _flask(db_path, "upgrade")
    assert again.returncode == 0, again.stderr
    with sqlite3.connect(db_path) as conn:
        assert conn.execute(
            "SELECT avatar_url, cover_url FROM users WHERE id = 1"
        ).fetchone() == (
            "uploads/clients/atualizada.jpg",
            "uploads/professionals/capa-nova.jpg",
        )


def test_personal_media_writers_are_atomic_and_keep_legacy_readers(app):
    with app.app_context():
        user = User(name="Pessoa", email="media-atomic@example.com", role=UserRole.CLIENT)
        user.set_password("senha-forte-123")
        db.session.add(user)
        db.session.flush()
        client_profile = ClientProfile(user=user, avatar_url="uploads/clients/antiga.jpg")
        professional = ProfessionalProfile(
            user=user,
            display_name="Pessoa Pro",
            slug="pessoa-pro-media",
            avatar_url="uploads/professionals/antiga.jpg",
            cover_url="uploads/professionals/capa-antiga.jpg",
        )
        db.session.add_all([client_profile, professional])
        db.session.commit()
        user_id = user.id

        set_personal_avatar(user, "uploads/clients/nova.jpg")
        set_personal_cover(user, "uploads/professionals/capa-nova.jpg")
        db.session.flush()
        db.session.rollback()

        user = db.session.get(User, user_id)
        assert user.avatar_url is None and user.cover_url is None
        assert user.client_profile.avatar_url == "uploads/clients/antiga.jpg"
        assert user.professional_profile.avatar_url == "uploads/professionals/antiga.jpg"
        assert user.professional_profile.cover_url == "uploads/professionals/capa-antiga.jpg"

        set_personal_avatar(user, "uploads/clients/nova.jpg")
        set_personal_cover(user, "uploads/professionals/capa-nova.jpg")
        db.session.commit()

        user = db.session.get(User, user_id)
        assert user.avatar_url == user.client_profile.avatar_url
        assert user.avatar_url == user.professional_profile.avatar_url
        assert user.cover_url == user.professional_profile.cover_url
