"""Migration z63b0k1e2026 — trilha das reservas e tolerância de no-show.

V1-CONV-D02 (Notion 08, 17/11/2026). Roda a migration real numa base SQLite
descartável: empresas existentes recebem 15 min sem reescrever dados, a
faixa 0–60 é garantida no banco, a trilha só aceita ações e papéis
conhecidos, e a descida remove só o que a subida criou.
"""

import sqlite3

import pytest

from tests.test_identity_follow_migration import NOW, _flask

BEFORE = "y52f0l1w2026"


def test_upgrade_adds_trail_and_tolerance_without_touching_data(tmp_path):
    db_path = tmp_path / "bookings.db"
    assert _flask(db_path, "upgrade", BEFORE).returncode == 0
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO establishments (id, name, slug, is_verified, is_active, created_at, updated_at) "
            f"VALUES (7, 'Studio', 'studio', 0, 1, {NOW}, {NOW})"
        )

    upgrade = _flask(db_path, "upgrade")
    assert upgrade.returncode == 0, upgrade.stderr

    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT no_show_tolerance_minutes FROM establishments WHERE id = 7").fetchone() == (15,)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE establishments SET no_show_tolerance_minutes = 61 WHERE id = 7")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE establishments SET no_show_tolerance_minutes = -1 WHERE id = 7")
        conn.execute("UPDATE establishments SET no_show_tolerance_minutes = 60 WHERE id = 7")

        columns = {row[1] for row in conn.execute("PRAGMA table_info(booking_events)")}
        assert columns == {"id", "booking_id", "actor_user_id", "actor_role", "action", "reason", "created_at"}
        conn.execute("PRAGMA foreign_keys = OFF")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO booking_events (booking_id, actor_role, action, created_at) "
                "VALUES (1, 'executor', 'started', 'x')"
            )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO booking_events (booking_id, actor_role, action, created_at) "
                "VALUES (1, 'client', 'cancelled', 'x')"
            )

    downgrade = _flask(db_path, "downgrade", BEFORE)
    assert downgrade.returncode == 0, downgrade.stderr
    with sqlite3.connect(db_path) as conn:
        assert "no_show_tolerance_minutes" not in {row[1] for row in conn.execute("PRAGMA table_info(establishments)")}
        assert conn.execute("SELECT name FROM sqlite_master WHERE name = 'booking_events'").fetchall() == []
        assert conn.execute("SELECT name FROM establishments WHERE id = 7").fetchone() == ("Studio",)

    again = _flask(db_path, "upgrade")
    assert again.returncode == 0, again.stderr
