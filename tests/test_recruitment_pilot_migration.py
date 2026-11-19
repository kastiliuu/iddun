"""Migration a74c1r2p2026 — piloto de recrutamento e permissão de gerentes.

V1-CONV-D05 (Notion 08, 19/11/2026). Roda a migration real numa base SQLite
descartável: empresas e acessos existentes ficam com recrutamento desligado
e sem permissão (padrão negado), vagas existentes não mudam, o registro só
aceita ações conhecidas e a descida remove só o que a subida criou.
"""

import sqlite3

import pytest

from tests.test_identity_follow_migration import NOW, _flask

BEFORE = "z63b0k1e2026"


def test_upgrade_defaults_to_deny_and_keeps_jobs(tmp_path):
    db_path = tmp_path / "recruitment.db"
    assert _flask(db_path, "upgrade", BEFORE).returncode == 0
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO users (id, name, email, username, password_hash, role, is_active_account, created_at, updated_at) "
            f"VALUES (3, 'Gerente', 'g@example.com', 'gerente', 'x', 'client', 1, {NOW}, {NOW})"
        )
        conn.execute(
            "INSERT INTO establishments (id, name, slug, is_verified, is_active, created_at, updated_at) "
            f"VALUES (7, 'Studio', 'studio', 0, 1, {NOW}, {NOW})"
        )
        conn.execute(
            "INSERT INTO establishment_user_accesses (id, user_id, establishment_id, role, status, created_at) "
            f"VALUES (5, 3, 7, 'manager', 'active', {NOW})"
        )
        conn.execute(
            "INSERT INTO job_posts (id, establishment_id, title, description, status, created_at, updated_at) "
            f"VALUES (9, 7, 'Vaga', 'Texto', 'published', {NOW}, {NOW})"
        )

    upgrade = _flask(db_path, "upgrade")
    assert upgrade.returncode == 0, upgrade.stderr

    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT recruitment_enabled FROM establishments WHERE id = 7").fetchone() == (0,)
        assert conn.execute("SELECT can_recruit FROM establishment_user_accesses WHERE id = 5").fetchone() == (0,)
        assert conn.execute("SELECT status FROM job_posts WHERE id = 9").fetchone() == ("published",)
        columns = {row[1] for row in conn.execute("PRAGMA table_info(recruitment_audit_events)")}
        assert columns == {"id", "establishment_id", "actor_user_id", "subject_user_id", "action", "reason", "created_at"}
        conn.execute("PRAGMA foreign_keys = OFF")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO recruitment_audit_events (establishment_id, action, created_at) VALUES (7, 'hired', 'x')"
            )
        conn.execute(
            "INSERT INTO recruitment_audit_events (establishment_id, action, reason, created_at) "
            "VALUES (7, 'pilot_enabled', 'Piloto', 'x')"
        )

    downgrade = _flask(db_path, "downgrade", BEFORE)
    assert downgrade.returncode == 0, downgrade.stderr
    with sqlite3.connect(db_path) as conn:
        assert "recruitment_enabled" not in {row[1] for row in conn.execute("PRAGMA table_info(establishments)")}
        assert "can_recruit" not in {row[1] for row in conn.execute("PRAGMA table_info(establishment_user_accesses)")}
        assert conn.execute("SELECT name FROM sqlite_master WHERE name = 'recruitment_audit_events'").fetchall() == []
        assert conn.execute("SELECT title FROM job_posts WHERE id = 9").fetchone() == ("Vaga",)
        assert conn.execute("SELECT role FROM establishment_user_accesses WHERE id = 5").fetchone() == ("manager",)

    again = _flask(db_path, "upgrade")
    assert again.returncode == 0, again.stderr
