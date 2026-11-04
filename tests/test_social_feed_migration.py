"""Migration v29s8o1p2026 (D-SOC-08): posts antigos continuam válidos.

Roda as migrations reais numa base SQLite descartável: cria um post na
revisão anterior, aplica a nova, confere o backfill e as restrições e
volta, garantindo que o post antigo não muda.
"""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _flask(db_path, *args):
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{db_path}",
        "SECRET_KEY": "migration-test-secret",
        "APP_ENV": "development",
    }
    result = subprocess.run(
        [sys.executable, "-m", "flask", "--app", "run:app", "db", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return result


def test_upgrade_backfills_media_and_downgrade_restores_legacy_posts(tmp_path):
    db_path = tmp_path / "migration.db"
    assert _flask(db_path, "upgrade", "u18n7a1m2026").returncode == 0

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO work_posts (id, author_type, professional_id, caption, image_url, "
            "image_focus_x, image_focus_y, status, published_at, created_at, updated_at) "
            "VALUES (1, 'professional', 1, 'Antigo', 'uploads/a.jpg', 30, 70, 'published', "
            "'2026-10-01', '2026-10-01', '2026-10-01')"
        )

    upgrade = _flask(db_path, "upgrade")
    assert upgrade.returncode == 0, upgrade.stderr

    with sqlite3.connect(db_path) as conn:
        assert conn.execute(
            "SELECT id, author_type, caption, image_url, status FROM work_posts"
        ).fetchall() == [(1, "professional", "Antigo", "uploads/a.jpg", "published")]
        assert conn.execute(
            "SELECT post_id, position, image_url, focus_x, focus_y FROM work_post_media"
        ).fetchall() == [(1, 0, "uploads/a.jpg", 30, 70)]

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO work_posts (author_type, professional_id, client_profile_id, "
                "image_focus_x, image_focus_y, status, created_at, updated_at) "
                "VALUES ('professional', 1, 1, 50, 50, 'published', 'x', 'x')"
            )
        conn.execute(
            "INSERT INTO work_post_likes (post_id, user_id, created_at) VALUES (1, 1, 'x')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO work_post_likes (post_id, user_id, created_at) VALUES (1, 1, 'x')"
            )
        conn.execute("DELETE FROM work_post_likes")

    downgrade = _flask(db_path, "downgrade", "u18n7a1m2026")
    assert downgrade.returncode == 0, downgrade.stderr
    with sqlite3.connect(db_path) as conn:
        assert conn.execute(
            "SELECT id, image_url, image_focus_x FROM work_posts"
        ).fetchall() == [(1, "uploads/a.jpg", 30)]


def test_downgrade_refuses_when_client_posts_exist(tmp_path):
    db_path = tmp_path / "blocked.db"
    assert _flask(db_path, "upgrade").returncode == 0
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO work_posts (author_type, client_profile_id, caption, "
            "image_focus_x, image_focus_y, status, created_at, updated_at) "
            "VALUES ('client', 1, 'Texto', 50, 50, 'published', 'x', 'x')"
        )

    result = _flask(db_path, "downgrade", "u18n7a1m2026")
    assert result.returncode != 0
    assert "Downgrade bloqueado" in result.stderr + result.stdout
