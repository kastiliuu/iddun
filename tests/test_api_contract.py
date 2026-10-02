from app.extensions import db
from app.models.experience import (
    Experience,
    ExperienceStatus,
)
from app.models.professional import (
    ProfessionalProfile,
)


def _catalog(app, count=3):
    with app.app_context():
        professional = ProfessionalProfile(
            display_name="Profissional API",
            slug="profissional-api",
            city="Curitiba",
        )
        db.session.add(professional)
        db.session.flush()

        for index in range(count):
            db.session.add(
                Experience(
                    professional=professional,
                    title=f"Experiência {index + 1}",
                    slug=f"experiencia-{index + 1}",
                    category="unhas",
                    short_description="Experiência publicada",
                    regular_price="150.00",
                    price=str(100 + index),
                    duration_minutes=60,
                    status=ExperienceStatus.PUBLISHED,
                )
            )

        db.session.commit()


def test_api_unknown_route_returns_json_contract(
    client,
):
    response = client.get(
        "/api/v1/recurso-inexistente"
    )

    assert response.status_code == 404
    assert response.is_json

    payload = response.get_json()

    assert payload["message"] == (
        "Recurso não encontrado."
    )
    assert payload["error"] == {
        "code": "not_found",
        "message": "Recurso não encontrado.",
    }
    assert "no-store" in response.headers[
        "Cache-Control"
    ]


def test_api_method_not_allowed_returns_json_contract(
    client,
):
    response = client.post(
        "/api/v1/experiences"
    )

    assert response.status_code == 405
    assert response.is_json
    assert (
        response.get_json()["error"]["code"]
        == "method_not_allowed"
    )


def test_experience_not_found_uses_domain_error(
    client,
):
    response = client.get(
        "/api/v1/experiences/inexistente"
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == {
        "code": "experience_not_found",
        "message": "Experiência não encontrada.",
    }


def test_catalog_rejects_invalid_pagination(
    client,
):
    cases = (
        ("limit", "0"),
        ("limit", "51"),
        ("limit", "abc"),
        ("offset", "-1"),
        ("offset", "abc"),
    )

    for parameter, value in cases:
        response = client.get(
            (
                "/api/v1/experiences"
                f"?{parameter}={value}"
            )
        )

        assert response.status_code == 400

        error = response.get_json()["error"]

        assert (
            error["code"]
            == "invalid_query_parameter"
        )
        assert (
            error["details"]["parameter"]
            == parameter
        )
        assert (
            error["details"]["value"]
            == value
        )


def test_catalog_rejects_unknown_sort(
    client,
):
    response = client.get(
        "/api/v1/experiences?sort=magic"
    )

    assert response.status_code == 400

    error = response.get_json()["error"]

    assert error["code"] == (
        "invalid_query_parameter"
    )
    assert error["details"]["parameter"] == "sort"
    assert error["details"]["value"] == "magic"


def test_catalog_rejects_oversized_filters(
    client,
):
    response = client.get(
        "/api/v1/experiences",
        query_string={
            "search": "x" * 121,
        },
    )

    assert response.status_code == 400

    details = response.get_json()[
        "error"
    ]["details"]

    assert details["parameter"] == "search"
    assert "120" in details["expected"]


def test_catalog_returns_compatible_and_structured_pagination(
    app,
    client,
):
    _catalog(app, count=3)

    response = client.get(
        "/api/v1/experiences",
        query_string={
            "limit": 2,
            "offset": 0,
        },
    )

    assert response.status_code == 200

    payload = response.get_json()

    assert len(payload["items"]) == 2
    assert payload["total"] == 3
    assert payload["nextOffset"] == 2
    assert payload["pagination"] == {
        "offset": 0,
        "limit": 2,
        "total": 3,
        "nextOffset": 2,
        "hasMore": True,
    }

    next_page = client.get(
        "/api/v1/experiences",
        query_string={
            "limit": 2,
            "offset": 2,
        },
    ).get_json()

    assert len(next_page["items"]) == 1
    assert next_page["nextOffset"] is None
    assert next_page["pagination"]["hasMore"] is False
