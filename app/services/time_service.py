from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


DEFAULT_TIMEZONE = "America/Sao_Paulo"


def timezone_or_default(name=None):
    timezone_name = name or DEFAULT_TIMEZONE

    try:
        return ZoneInfo(timezone_name)

    except ZoneInfoNotFoundError:
        if timezone_name != DEFAULT_TIMEZONE:
            try:
                return ZoneInfo(DEFAULT_TIMEZONE)
            except ZoneInfoNotFoundError:
                pass

        raise RuntimeError(
            "Base de fusos horários indisponível. "
            "Instale a dependência 'tzdata'."
        )


def utcnow():
    """
    Retorna o horário atual em UTC com timezone.
    """
    return datetime.now(timezone.utc)


def as_utc(value):
    """
    Garante que um datetime esteja representado em UTC.

    Valores sem timezone são considerados UTC, pois timestamps
    persistidos pelo IDDUN são tratados internamente em UTC.
    """
    if value is None:
        return None

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def to_local(value, timezone_name=None):
    """
    Converte um datetime UTC para o fuso horário do profissional
    ou estabelecimento.
    """
    if value is None:
        return None

    return as_utc(value).astimezone(
        timezone_or_default(timezone_name)
    )


def local_naive_to_utc(value, timezone_name=None):
    """
    Recebe um datetime local sem timezone, como:

        2026-09-18 14:00

    interpreta esse horário no timezone informado e converte para UTC
    antes de persistir no banco.
    """
    if value is None:
        return None

    if value.tzinfo is not None:
        return value.astimezone(timezone.utc)

    local_timezone = timezone_or_default(timezone_name)

    localized = value.replace(
        tzinfo=local_timezone
    )

    return localized.astimezone(timezone.utc)