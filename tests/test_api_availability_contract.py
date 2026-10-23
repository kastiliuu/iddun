"""Contract regression tests for public availability and private creation boundaries.

These tests intentionally never create a real booking or availability slot.
They protect request validation and authorization without changing business rules.
"""

import pytest

from app.routes import api_availability


@pytest.mark.parametrize(
    "query",
    [
        "?limit=0",
        "?limit=-1",
        "?limit=51",
        "?limit=abc",
        "?limit=1.5",
        "?limit=",
        "?limit=%20",
    ],
)
def test_iddun_now_rejects_invalid_limits_without_querying_slots(
    client, monkeypatch, query
):
    def unexpected_query(**_kwargs):
        pytest.fail("Invalid limit must not query availability")

    monkeypatch.setattr(api_availability, "iddun_now_slots", unexpected_query)

    response = client.get("/api/v1/iddun-now" + query)

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_query_parameter"


@pytest.mark.parametrize(
    ("query", "expected_limit", "expected_mode"),
    [
        ("", 20, "all"),
        ("?limit=1", 1, "all"),
        ("?limit=50", 50, "all"),
        ("?filter=URGENT", 20, "urgent"),
        ("?filter=%20all%20", 20, "all"),
        ("?filter=", 20, "all"),
    ],
)
def test_iddun_now_forwards_normalized_arguments(
    client, monkeypatch, query, expected_limit, expected_mode
):
    calls = []

    def fake_slots(*, limit, mode):
        calls.append((limit, mode))
        return []

    monkeypatch.setattr(api_availability, "iddun_now_slots", fake_slots)

    response = client.get("/api/v1/iddun-now" + query)

    assert response.status_code == 200
    assert response.get_json()["items"] == []
    assert calls == [(expected_limit, expected_mode)]
    assert "public" in response.headers["Cache-Control"]


def test_iddun_now_maps_availability_error_to_bad_request(client, monkeypatch):
    def reject_slots(**_kwargs):
        raise api_availability.AvailabilityError("Filtro inválido.")

    monkeypatch.setattr(api_availability, "iddun_now_slots", reject_slots)

    response = client.get("/api/v1/iddun-now?filter=invalid")

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_availability_request"


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("get", "/api/v1/availability/options", {}),
        ("post", "/api/v1/availability", {"json": {}}),
        ("post", "/api/v1/availability", {"data": "not-json"}),
    ],
)
def test_private_availability_endpoints_require_authentication(
    client, method, path, kwargs
):
    response = getattr(client, method)(path, **kwargs)

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "authentication_required"


@pytest.mark.parametrize(
    ("content_type", "body", "expected_status", "expected_code"),
    [
        ("text/plain", "hello", 415, "json_required"),
        ("application/json", "{invalid", 400, "invalid_json"),
        ("application/json", "[]", 400, "invalid_json"),
        ("application/json", "null", 400, "invalid_json"),
    ],
)
def test_slot_creation_validates_body_before_service_call(
    client, monkeypatch, content_type, body, expected_status, expected_code
):
    monkeypatch.setattr(
        api_availability,
        "_require_user",
        lambda: (object(), None),
    )

    def unexpected_create(**_kwargs):
        pytest.fail("Invalid input must not create a slot")

    monkeypatch.setattr(
        api_availability, "create_availability", unexpected_create
    )

    response = client.post(
        "/api/v1/availability",
        data=body,
        content_type=content_type,
    )

    assert response.status_code == expected_status
    assert response.get_json()["error"]["code"] == expected_code


def test_slot_creation_rejects_oversized_payload_before_service_call(
    client, monkeypatch
):
    monkeypatch.setattr(
        api_availability,
        "_require_user",
        lambda: (object(), None),
    )

    def unexpected_create(**_kwargs):
        pytest.fail("Oversized input must not create a slot")

    monkeypatch.setattr(
        api_availability, "create_availability", unexpected_create
    )

    response = client.post(
        "/api/v1/availability",
        data="x" * (api_availability.MAX_BODY_BYTES + 1),
        content_type="application/json",
    )

    assert response.status_code == 413
    assert response.get_json()["error"]["code"] == "request_too_large"
