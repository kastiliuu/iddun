import click
from flask import current_app
from flask.cli import with_appcontext
from sqlalchemy import func, inspect, select, text

from app.extensions import db
from app.models.user import User, UserRole


@click.command("make-admin")
@click.argument("email")
@with_appcontext
def make_admin(email):
    """Promove um usuário existente para administrador."""
    normalized = email.strip().lower()
    user = db.session.scalar(select(User).where(User.email == normalized))
    if user is None:
        raise click.ClickException(f"Usuário não encontrado: {normalized}")

    user.role = UserRole.ADMIN
    db.session.commit()
    click.echo(f"{normalized} agora é administrador do IDDUN.")


@click.command("sync-calendars")
@with_appcontext
def sync_calendars():
    """Sincroniza conexões Google Calendar ativas."""
    from app.services.google_calendar_service import sync_all_enabled_connections

    summary = sync_all_enabled_connections()
    click.echo(
        f"{summary['success']}/{summary['connections']} agenda(s) sincronizada(s); "
        f"{summary['blocked']} slot(s) bloqueado(s); {summary['restored']} reaberto(s); "
        f"{summary['errors']} erro(s)."
    )


def _application_tables():
    """Return application tables in child-first order, excluding migration state."""
    return [
        table
        for table in reversed(db.metadata.sorted_tables)
        if table.name != "alembic_version"
    ]


def _table_counts(tables):
    return {
        table.name: db.session.scalar(select(func.count()).select_from(table)) or 0
        for table in tables
    }


def _clear_application_data(tables):
    dialect = db.engine.dialect.name
    preparer = db.engine.dialect.identifier_preparer

    if dialect == "postgresql":
        table_names = ", ".join(preparer.format_table(table) for table in tables)
        if table_names:
            db.session.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))
        db.session.commit()
        return

    if dialect == "sqlite":
        for table in tables:
            db.session.execute(table.delete())
        if inspect(db.session.connection()).has_table("sqlite_sequence"):
            db.session.execute(text("DELETE FROM sqlite_sequence"))
        db.session.commit()
        return

    if dialect in {"mysql", "mariadb"}:
        connection = db.session.connection()
        try:
            connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            for table in tables:
                connection.execute(table.delete())
                connection.execute(
                    text(f"ALTER TABLE {preparer.format_table(table)} AUTO_INCREMENT = 1")
                )
            connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            db.session.commit()
        except Exception:
            connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            db.session.rollback()
            raise
        return

    for table in tables:
        db.session.execute(table.delete())
    db.session.commit()


@click.command("reset-data")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Mostra o que seria removido sem alterar o banco.",
)
@click.option(
    "--yes",
    "confirmed",
    is_flag=True,
    help="Confirma a limpeza sem pergunta interativa.",
)
@click.option(
    "--allow-production",
    is_flag=True,
    help="Libera explicitamente a execução quando APP_ENV=production.",
)
@with_appcontext
def reset_data(dry_run, confirmed, allow_production):
    """Remove todos os registros e preserva schema, índices e migrations."""
    tables = _application_tables()
    counts = _table_counts(tables)
    populated = [(name, count) for name, count in sorted(counts.items()) if count]
    total = sum(counts.values())
    target = db.engine.url.render_as_string(hide_password=True)

    click.echo(f"Banco alvo: {target}")
    click.echo(f"Registros encontrados: {total}")
    for table_name, count in populated:
        click.echo(f"  {table_name}: {count}")

    if dry_run:
        click.echo("Simulação concluída. Nenhum registro foi removido.")
        return

    if total == 0:
        click.echo("O banco já está vazio. Estrutura preservada.")
        return

    if current_app.config.get("APP_ENV") == "production" and not allow_production:
        raise click.ClickException(
            "Ambiente de produção bloqueado. Faça backup e repita com --allow-production."
        )

    if not confirmed and not click.confirm(
        "Apagar definitivamente todos os registros da aplicação?",
        default=False,
    ):
        click.echo("Limpeza cancelada. Nenhum registro foi removido.")
        return

    try:
        _clear_application_data(tables)
    except Exception as exc:
        db.session.rollback()
        raise click.ClickException(f"A limpeza falhou e foi revertida: {exc}") from exc

    remaining = sum(_table_counts(tables).values())
    if remaining:
        raise click.ClickException(
            f"A limpeza terminou com {remaining} registro(s) restante(s). Verifique o banco."
        )

    click.echo(
        f"Limpeza concluída: {total} registro(s) removido(s). "
        "Tabelas, índices e migrations foram preservados."
    )


def register_cli(app):
    app.cli.add_command(make_admin)
    app.cli.add_command(sync_calendars)
    app.cli.add_command(reset_data)
