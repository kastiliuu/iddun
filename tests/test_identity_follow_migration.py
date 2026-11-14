"""Migrations x41u5n4m2026 (@username) e y52f0l1w2026 (seguir pessoas).

ID-SOC-R1-02/03 (Notion 08, 14/11/2026). Roda as migrations reais numa base
SQLite descartável: cria dados na revisão anterior, sobe, confere o
preenchimento do @ e a conversão dos seguidores sem perda, desce e confere
que os seguidores voltam ao formato antigo.
"""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BEFORE = "w30n1o2t2026"
NOW = "'2026-11-01'"


def _flask(db_path, *args):
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{db_path}",
        "SECRET_KEY": "migration-test-secret",
        "APP_ENV": "development",
    }
    return subprocess.run(
        [sys.executable, "-m", "flask", "--app", "run:app", "db", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _seed(conn):
    users = [
        (1, "Ana Côsta"),      # ana.costa
        (2, "Ana Costa"),      # ana.costa2 (colisão)
        (3, "Admin"),          # reservado -> pessoa
        (4, "Jo"),             # curto -> pessoa2
        (5, "Fã Um"),          # fa.um
        (6, "Fã Dois"),        # fa.dois
    ]
    for user_id, name in users:
        conn.execute(
            "INSERT INTO users (id, name, email, password_hash, role, is_active_account, created_at, updated_at) "
            f"VALUES (?, ?, ?, 'x', 'client', 1, {NOW}, {NOW})",
            (user_id, name, f"u{user_id}@example.com"),
        )
    # Perfil Pro da conta 1 e um perfil de catálogo sem conta.
    for profile_id, user_id, slug in [(10, 1, "ana-pro"), (11, None, "catalogo")]:
        conn.execute(
            "INSERT INTO professional_profiles (id, user_id, display_name, slug, is_verified, is_active, created_at, updated_at) "
            f"VALUES (?, ?, ?, ?, 0, 1, {NOW}, {NOW})",
            (profile_id, user_id, slug, slug),
        )
    conn.execute(
        "INSERT INTO establishments (id, name, slug, is_verified, is_active, created_at, updated_at) "
        f"VALUES (20, 'Studio', 'studio', 0, 1, {NOW}, {NOW})"
    )
    follows = [
        (100, 5, "professional", 10, None, "2026-10-01"),  # vira pessoa 1
        (101, 6, "professional", 10, None, "2026-10-02"),  # vira pessoa 1
        (102, 1, "professional", 10, None, "2026-10-03"),  # seguir a si mesmo: removido
        (103, 5, "professional", 11, None, "2026-10-04"),  # catálogo: fica igual
        (104, 5, "establishment", None, 20, "2026-10-05"),  # empresa: fica igual
    ]
    for row in follows:
        conn.execute(
            "INSERT INTO follows (id, user_id, target_type, professional_id, establishment_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            row,
        )


def test_upgrade_backfills_usernames_and_converts_follows_without_loss(tmp_path):
    db_path = tmp_path / "identity.db"
    assert _flask(db_path, "upgrade", BEFORE).returncode == 0
    with sqlite3.connect(db_path) as conn:
        _seed(conn)

    upgrade = _flask(db_path, "upgrade")
    assert upgrade.returncode == 0, upgrade.stderr

    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT id, username FROM users ORDER BY id").fetchall() == [
            (1, "ana.costa"), (2, "ana.costa2"), (3, "pessoa"), (4, "pessoa2"), (5, "fa.um"), (6, "fa.dois"),
        ]
        assert conn.execute(
            "SELECT id, user_id, target_type, professional_id, establishment_id, followed_user_id, created_at "
            "FROM follows ORDER BY id"
        ).fetchall() == [
            (100, 5, "person", None, None, 1, "2026-10-01"),
            (101, 6, "person", None, None, 1, "2026-10-02"),
            (103, 5, "professional", 11, None, None, "2026-10-04"),
            (104, 5, "establishment", None, 20, None, "2026-10-05"),
        ]
        # @ obrigatório e único; seguir a mesma pessoa duas vezes, recusado.
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE users SET username = 'ana.costa' WHERE id = 2")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"INSERT INTO users (name, email, password_hash, role, is_active_account, created_at, updated_at) "
                f"VALUES ('Sem @', 'sem@example.com', 'x', 'client', 1, {NOW}, {NOW})"
            )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO follows (user_id, target_type, followed_user_id, created_at) VALUES (5, 'person', 1, 'x')"
            )
        # Forma inválida: pessoa sem conta seguida.
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO follows (user_id, target_type, created_at) VALUES (6, 'person', 'x')")
        # Seguir uma Cliente sem perfil Pro passa a ser possível.
        conn.execute(
            "INSERT INTO follows (id, user_id, target_type, followed_user_id, created_at) VALUES (105, 6, 'person', 2, 'x')"
        )
        conn.execute("INSERT INTO username_history (user_id, username, created_at) VALUES (1, 'ana.old', 'x')")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO username_history (user_id, username, created_at) VALUES (2, 'ana.old', 'x')")

    downgrade = _flask(db_path, "downgrade", BEFORE)
    assert downgrade.returncode == 0, downgrade.stderr

    with sqlite3.connect(db_path) as conn:
        # Quem segue a pessoa com Pro volta a seguir o perfil Pro; o seguir da
        # Cliente sem Pro (105) não cabe no formato antigo e sai (documentado).
        assert conn.execute(
            "SELECT id, user_id, target_type, professional_id, establishment_id FROM follows ORDER BY id"
        ).fetchall() == [
            (100, 5, "professional", 10, None),
            (101, 6, "professional", 10, None),
            (103, 5, "professional", 11, None),
            (104, 5, "establishment", None, 20),
        ]
        columns = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
        assert "username" not in columns
        assert conn.execute(
            "SELECT name FROM sqlite_master WHERE name = 'username_history'"
        ).fetchall() == []

    # E sobe de novo, limpo.
    again = _flask(db_path, "upgrade")
    assert again.returncode == 0, again.stderr
