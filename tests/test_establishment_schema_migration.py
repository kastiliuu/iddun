"""NV-07A1-M: additive Business schema and safe legacy data preservation.

Runs against a disposable SQLite database; never queries production.
PostgreSQL JSONB representation is verified with the PostgreSQL dialect.
"""

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.dialects import postgresql

from app.models.establishment import Establishment


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations/versions/u18n7a1m2026_business_operation_hours.py"
)
NEW_COLUMNS = {"operation_mode", "business_hours_mode", "business_hours"}


def _migration_module():
    spec = importlib.util.spec_from_file_location("nv07a1m", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_schema_uses_nullable_fields_and_postgresql_jsonb():
    columns = Establishment.__table__.columns
    assert NEW_COLUMNS.issubset(set(columns.keys()))
    assert all(columns[name].nullable for name in NEW_COLUMNS)
    assert all(columns[name].server_default is None for name in NEW_COLUMNS)
    assert columns["operation_mode"].type.length == 16
    assert columns["business_hours_mode"].type.length == 16
    assert isinstance(
        columns["business_hours"].type.dialect_impl(postgresql.dialect()),
        postgresql.JSONB,
    )
    # SQLite is used in the existing pytest/Playwright suite.
    assert columns["business_hours"].type.compile(
        dialect=sa.create_engine("sqlite://").dialect
    ) == "JSON"


def test_expansion_preserves_published_legacy_rows_and_downgrade(monkeypatch):
    module = _migration_module()
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        # Representative pre-migration table, including real publication flags.
        connection.execute(sa.text("""
            CREATE TABLE establishments (
                id INTEGER PRIMARY KEY,
                name VARCHAR(160) NOT NULL,
                onboarding_completed BOOLEAN NOT NULL,
                published_at DATETIME,
                is_active BOOLEAN NOT NULL
            )
        """))
        connection.execute(sa.text("""
            INSERT INTO establishments
                (id, name, onboarding_completed, published_at, is_active)
            VALUES
                (1, 'Empresa publicada', 1, '2026-10-15 10:00:00', 1),
                (2, 'Rascunho', 0, NULL, 0)
        """))
        operations = Operations(MigrationContext.configure(connection))
        monkeypatch.setattr(module, "op", operations)
        original = connection.execute(sa.text("""
            SELECT id, name, onboarding_completed, published_at, is_active
            FROM establishments ORDER BY id
        """)).all()

        module.upgrade()
        expanded = {c["name"]: c for c in sa.inspect(connection).get_columns("establishments")}
        assert NEW_COLUMNS.issubset(expanded)
        assert all(expanded[name]["nullable"] for name in NEW_COLUMNS)
        rows = connection.execute(sa.text("""
            SELECT id, name, onboarding_completed, published_at, is_active,
                   operation_mode, business_hours_mode, business_hours
            FROM establishments ORDER BY id
        """)).all()
        assert [tuple(row[:5]) for row in rows] == [tuple(row) for row in original]
        assert all(tuple(row[5:]) == (None, None, None) for row in rows)

        # New optional data round-trips without changing existing flags.
        connection.execute(sa.text("""
            UPDATE establishments
            SET operation_mode='physical', business_hours_mode='scheduled',
                business_hours='{"monday": []}'
            WHERE id=1
        """))
        values = connection.execute(sa.text("""
            SELECT operation_mode, business_hours_mode, business_hours
            FROM establishments WHERE id=1
        """)).one()
        assert values.operation_mode == "physical"
        assert values.business_hours_mode == "scheduled"
        assert values.business_hours is not None

        # Downgrade is verified only on disposable data. In production it is
        # destructive for the three new columns and requires prior backup.
        module.downgrade()
        reduced = {c["name"] for c in sa.inspect(connection).get_columns("establishments")}
        assert not NEW_COLUMNS.intersection(reduced)
        restored = connection.execute(sa.text("""
            SELECT id, name, onboarding_completed, published_at, is_active
            FROM establishments ORDER BY id
        """)).all()
        assert [tuple(row) for row in restored] == [tuple(row) for row in original]
