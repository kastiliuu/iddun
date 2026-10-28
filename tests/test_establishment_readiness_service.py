"""DEC-ID-100–108: independent domain readiness, no publication side effects."""

from types import SimpleNamespace

import pytest

from app.models.establishment import Establishment
from app.services.establishment_readiness_service import (
    EstablishmentReadiness,
    evaluate_establishment_readiness,
    valid_business_hours,
)


WEEK = {"monday": [{"start": "09:00", "end": "12:00"}, {"start": "13:00", "end": "17:00"}]}


def company(**overrides):
    fields = dict(
        name="Studio Exemplo",
        category="salao",
        description="Empresa com serviços de beleza e bem-estar.",
        city="Curitiba",
        state="PR",
        phone="(41) 99999-9999",
        email=None,
        operation_mode="physical",
        business_hours_mode="scheduled",
        business_hours=None,
        address_line1="Rua Comercial, 100",
        logo_url=None,
        cover_url=None,
        published_at=None,
        is_active=False,
        onboarding_completed=False,
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


@pytest.mark.parametrize("mode,address,expected", [
    ("physical", None, False),
    ("physical", "Rua Comercial, 100", True),
    ("mobile", None, True),
    ("hybrid", None, False),
    ("hybrid", "Rua Comercial, 100", True),
    (None, "Rua Comercial, 100", False),
    ("other", "Rua Comercial, 100", False),
])
def test_operation_modes_and_conditional_address(mode, address, expected):
    result = evaluate_establishment_readiness(
        company(operation_mode=mode, address_line1=address)
    )
    assert result.ready_to_publish is expected
    assert ("business_address" in result.missing_requirements) is (
        mode in {"physical", "hybrid"} and not address
    )


def test_scheduled_hours_are_explicit_and_need_no_weekly_schedule():
    result = evaluate_establishment_readiness(company())
    assert result == EstablishmentReadiness(
        percentage=100, ready_to_publish=True, missing_requirements=()
    )


@pytest.mark.parametrize("schedule", [
    None, {}, [],
    {"unknown": [{"start": "09:00", "end": "17:00"}]},
    {"monday": []},
    {"monday": "09:00-17:00"},
    {"monday": [{"start": "9:00", "end": "17:00"}]},
    {"monday": [{"start": "09:00", "end": "25:00"}]},
    {"monday": [{"start": "17:00", "end": "09:00"}]},
    {"monday": [{"start": "12:00", "end": "12:00"}]},
    {"monday": [{"start": "09:00", "end": "12:00", "id": 1}]},
    {"monday": [{"start": "11:00", "end": "14:00"},
                {"start": "09:00", "end": "10:00"}]},
    {"monday": [{"start": "09:00", "end": "12:00"},
                {"start": "11:59", "end": "16:00"}]},
])
def test_invalid_weekly_hours_are_rejected(schedule):
    assert valid_business_hours(schedule) is False
    result = evaluate_establishment_readiness(
        company(business_hours_mode="fixed_hours", business_hours=schedule)
    )
    assert "business_hours" in result.missing_requirements
    assert result.ready_to_publish is False


def test_valid_weekly_hours_and_touching_intervals():
    assert valid_business_hours(WEEK) is True
    assert valid_business_hours({
        "saturday": [{"start": "08:00", "end": "11:30"},
                     {"start": "11:30", "end": "13:00"}],
        "sunday": [],
    }) is True
    result = evaluate_establishment_readiness(
        company(business_hours_mode="fixed_hours", business_hours=WEEK)
    )
    assert result.ready_to_publish is True
    assert result.percentage == 100


@pytest.mark.parametrize("changes,missing", [
    ({"name": "  "}, "name"),
    ({"category": ""}, "category"),
    ({"description": None}, "description"),
    ({"city": " "}, "location"),
    ({"state": "P"}, "location"),
    ({"phone": None, "email": None}, "commercial_contact"),
    ({"phone": "123", "email": "invalid"}, "commercial_contact"),
    ({"operation_mode": None}, "operation_mode"),
    ({"business_hours_mode": None}, "business_hours_mode"),
    ({"business_hours_mode": "24h"}, "business_hours_mode"),
])
def test_missing_requirements(changes, missing):
    result = evaluate_establishment_readiness(company(**changes))
    assert missing in result.missing_requirements
    assert 0 <= result.percentage < 100
    assert result.ready_to_publish is False


def test_business_email_qualifies_without_phone():
    assert evaluate_establishment_readiness(
        company(phone=None, email="contato@studio.example")
    ).ready_to_publish is True


def test_optional_media_team_and_catalog_not_in_readiness():
    result = evaluate_establishment_readiness(
        company(logo_url=None, cover_url=None, memberships=[], experiences=[])
    )
    assert result.ready_to_publish is True


@pytest.mark.parametrize("published,active", [
    (None, False), ("2026-10-01", True),
])
def test_legacy_readiness_does_not_mutate_publication(published, active):
    item = company(
        operation_mode=None, business_hours_mode=None,
        published_at=published, is_active=active, onboarding_completed=active,
    )
    before = dict(vars(item))
    a = evaluate_establishment_readiness(item)
    b = evaluate_establishment_readiness(item)
    assert a == b
    assert a.ready_to_publish is False
    assert vars(item) == before


def test_real_establishment_model_readiness_has_no_side_effects():
    item = Establishment(
        name="Studio Real", slug="studio-real", category="salao",
        description="Atendimento com horário agendado.",
        city="Curitiba", state="PR", phone="41999999999",
        operation_mode="mobile", business_hours_mode="scheduled",
        address_line1=None, published_at=None, is_active=False,
        onboarding_completed=False,
    )
    result = evaluate_establishment_readiness(item)
    assert result.ready_to_publish is True
    assert result.percentage == 100
    assert item.published_at is None
    assert item.onboarding_completed is False
    assert item.is_active is False
