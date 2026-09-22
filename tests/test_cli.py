from sqlalchemy import func, inspect, select

from app.extensions import db
from app.models.establishment import (
    Establishment,
    MembershipStatus,
    ProfessionalEstablishmentMembership,
)
from app.models.professional import ProfessionalProfile
from app.models.profile import ClientProfile
from app.models.user import User, UserRole


def _seed_application_data(app):
    with app.app_context():
        user = User(name="Conta para limpeza", email="reset@example.com", role=UserRole.CLIENT)
        user.set_password("senha-forte-123")
        client = ClientProfile(user=user)
        professional = ProfessionalProfile(
            user=user,
            display_name="Profissional para limpeza",
            slug="profissional-para-limpeza",
        )
        establishment = Establishment(
            name="Empresa para limpeza",
            slug="empresa-para-limpeza",
        )
        membership = ProfessionalEstablishmentMembership(
            professional=professional,
            establishment=establishment,
            status=MembershipStatus.ACTIVE,
        )
        db.session.add_all([user, client, professional, establishment, membership])
        db.session.commit()


def test_reset_data_dry_run_does_not_delete_records(app):
    _seed_application_data(app)

    result = app.test_cli_runner().invoke(args=["reset-data", "--dry-run"])

    assert result.exit_code == 0, result.output
    assert "Nenhum registro foi removido" in result.output
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(User)) == 1
        assert db.session.scalar(select(func.count()).select_from(Establishment)) == 1


def test_reset_data_clears_rows_and_preserves_schema(app):
    _seed_application_data(app)

    with app.app_context():
        tables_before = set(inspect(db.engine).get_table_names())

    result = app.test_cli_runner().invoke(args=["reset-data", "--yes"])

    assert result.exit_code == 0, result.output
    assert "Limpeza concluída" in result.output
    assert "Tabelas, índices e migrations foram preservados" in result.output

    with app.app_context():
        tables_after = set(inspect(db.engine).get_table_names())
        assert tables_after == tables_before
        for table in db.metadata.sorted_tables:
            assert db.session.scalar(select(func.count()).select_from(table)) == 0

        replacement = User(name="Primeira conta nova", email="novo@example.com")
        replacement.set_password("senha-forte-123")
        db.session.add(replacement)
        db.session.commit()
        assert replacement.id == 1


def test_reset_data_blocks_production_without_explicit_override(app):
    _seed_application_data(app)
    app.config["APP_ENV"] = "production"

    result = app.test_cli_runner().invoke(args=["reset-data", "--yes"])

    assert result.exit_code != 0
    assert "Ambiente de produção bloqueado" in result.output
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(User)) == 1
