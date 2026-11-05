"""Migration w30n1o2t2026 (D-SOC-21): avisos antigos continuam válidos.

Roda as migrations reais numa base SQLite descartável: cria avisos na
revisão anterior, aplica a nova, confere a categoria, a chave única e o
downgrade, que recusa quando já há avisos dos tipos novos.
"""

import sqlite3

import pytest

from tests.test_social_feed_migration import _flask


def test_upgrade_backfills_categories_and_downgrade_is_guarded(tmp_path):
    db_path = tmp_path / "notifications.db"
    assert _flask(db_path, "upgrade", "v29s8o1p2026").returncode == 0

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO users (id, name, email, password_hash, role, is_active_account, created_at, updated_at) "
            "VALUES (1, 'Ana', 'ana@example.com', 'x', 'client', 1, '2026-10-01', '2026-10-01')"
        )
        for nid, kind in ((1, "booking"), (2, "follow"), (3, "system"), (4, "iddun_now")):
            conn.execute(
                "INSERT INTO notifications (id, user_id, kind, title, body, created_at) "
                f"VALUES ({nid}, 1, '{kind}', 'Título', 'Texto', '2026-10-01')"
            )

    upgrade = _flask(db_path, "upgrade")
    assert upgrade.returncode == 0, upgrade.stderr

    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT id, kind, category, group_count FROM notifications ORDER BY id").fetchall() == [
            (1, "booking", "bookings", 1),
            (2, "follow", "social", 1),
            (3, "system", "system", 1),
            (4, "iddun_now", "bookings", 1),
        ]
        conn.execute(
            "INSERT INTO notifications (user_id, kind, category, title, body, dedupe_key, created_at) "
            "VALUES (1, 'booking', 'bookings', 'A', 'B', 'evento-1', '2026-10-02')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO notifications (user_id, kind, category, title, body, dedupe_key, created_at) "
                "VALUES (1, 'booking', 'bookings', 'A', 'B', 'evento-1', '2026-10-02')"
            )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO notifications (user_id, kind, category, title, body, created_at) "
                "VALUES (1, 'booking', 'qualquer', 'A', 'B', '2026-10-02')"
            )

    # Sem tipos novos: volta e os avisos antigos continuam iguais.
    downgrade = _flask(db_path, "downgrade", "v29s8o1p2026")
    assert downgrade.returncode == 0, downgrade.stderr
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT id, kind FROM notifications WHERE id <= 4 ORDER BY id").fetchall() == [
            (1, "booking"), (2, "follow"), (3, "system"), (4, "iddun_now"),
        ]

    assert _flask(db_path, "upgrade").returncode == 0
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO notifications (user_id, kind, category, title, body, created_at) "
            "VALUES (1, 'like', 'social', 'Curtida', 'Post', '2026-10-03')"
        )
    blocked = _flask(db_path, "downgrade", "v29s8o1p2026")
    assert blocked.returncode != 0
    assert "Downgrade bloqueado" in blocked.stderr
