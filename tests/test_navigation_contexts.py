"""D-SOC-01 / AUD-15 — contextos da conta para a troca pelo avatar.

A lista monta só os menus: Cliente sempre; Profissional quando há perfil;
cada estabelecimento com acesso ativo, com papel e estado de publicação.
"""

from datetime import datetime, timezone

from sqlalchemy import select

from app.extensions import db
from app.models.establishment import (
    Establishment,
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
    EstablishmentUserAccess,
)
from app.models.professional import ProfessionalProfile
from app.models.profile import ClientProfile
from app.models.user import User, UserRole
from app.services.api_auth import issue_session
from app.services.navigation_context import account_contexts

WHEN = datetime(2026, 9, 1, tzinfo=timezone.utc)


def _user(email="contextos@example.com", name="Conta Contextos"):
    user = User(name=name, email=email, role=UserRole.CLIENT)
    user.set_password("senha-forte-123")
    db.session.add(user)
    db.session.flush()
    db.session.add(ClientProfile(user=user))
    db.session.commit()
    return user


def _establishment(user, name, *, role=EstablishmentAccessRole.OWNER,
                   status=EstablishmentAccessStatus.ACTIVE, active=True, published_at=WHEN):
    item = Establishment(
        name=name, slug=name.lower().replace(" ", "-"), category="salao",
        city="Curitiba", state="PR", is_active=active, published_at=published_at,
    )
    db.session.add(item)
    db.session.flush()
    db.session.add(EstablishmentUserAccess(
        establishment_id=item.id, user_id=user.id, role=role, status=status,
    ))
    db.session.commit()
    return item


def _professional(user, *, active, published_at):
    profile = ProfessionalProfile(
        user_id=user.id, display_name="Ana Contextos", slug="ana-contextos",
        city="Curitiba", state="PR", is_active=active, published_at=published_at,
    )
    db.session.add(profile)
    db.session.commit()
    return profile


def test_client_only_account_has_one_context(app):
    user = _user()
    assert account_contexts(user) == [{"kind": "client", "name": "Conta Contextos"}]


def test_professional_states_are_told_apart(app):
    user = _user()
    profile = _professional(user, active=False, published_at=None)
    assert account_contexts(user)[1]["state"] == "draft"

    profile.is_active, profile.published_at = True, WHEN
    db.session.commit()
    assert account_contexts(user)[1]["state"] == "published"

    profile.is_active = False
    db.session.commit()
    assert account_contexts(user)[1]["state"] == "locked"


def test_every_active_establishment_appears_sorted_with_role(app):
    # Acesso inativo e página desativada pela moderação ficam de fora,
    # como em Minha conta.
    user = _user()
    _establishment(user, "Studio Zeta")
    _establishment(user, "Atelier Alfa", role=EstablishmentAccessRole.MANAGER)
    _establishment(user, "Antigo", status=EstablishmentAccessStatus.INACTIVE)
    _establishment(user, "Rascunho Beta", active=False, published_at=None)
    _establishment(user, "Moderado", active=False, published_at=WHEN)

    contexts = account_contexts(user)
    names = [item["name"] for item in contexts if item["kind"] == "establishment"]
    assert names == ["Atelier Alfa", "Rascunho Beta", "Studio Zeta"]
    by_name = {item["name"]: item for item in contexts if item["kind"] == "establishment"}
    assert by_name["Atelier Alfa"]["role"] == "manager"
    assert by_name["Rascunho Beta"]["state"] == "draft"
    assert by_name["Studio Zeta"]["role"] == "owner"


def test_auth_me_lists_contexts_and_keeps_role(app, client):
    user = _user()
    _professional(user, active=True, published_at=WHEN)
    first = _establishment(user, "Studio Um")
    second = _establishment(user, "Studio Dois")
    token = issue_session(user).access_token

    body = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).get_json()
    payload = body.get("user", body)
    assert payload["role"] == "professional"
    kinds = [item["kind"] for item in payload["contexts"]]
    assert kinds == ["client", "professional", "establishment", "establishment"]
    ids = {item["id"] for item in payload["contexts"] if item["kind"] == "establishment"}
    assert ids == {str(first.id), str(second.id)}
    assert all("state" in item for item in payload["contexts"][1:])


def _me(client, token):
    return client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )


def test_client_identity_remains_after_professional_activation(app, client):
    """QA-001-UX-03: legacy role and Pro must not replace the Cliente context."""
    user = _user(email="qa001-pro@example.com")
    client_profile_id = user.client_profile.id
    original_user_id = user.id
    # Legacy accounts can still have a professional role alongside their
    # client identity. No new user or client profile is created on activation.
    user.role = UserRole.PROFESSIONAL
    professional = _professional(user, active=True, published_at=WHEN)
    token = issue_session(user).access_token

    response = _me(client, token)
    assert response.status_code == 200
    assert "no-store" in response.headers["Cache-Control"]
    payload = response.get_json()
    assert payload["role"] == "professional"  # legacy API compatibility
    assert payload["contexts"][0] == {"kind": "client", "name": user.name}
    assert payload["contexts"][1] == {
        "kind": "professional",
        "id": str(professional.id),
        "name": "Ana Contextos",
        "slug": "ana-contextos",
        "state": "published",
    }
    assert user.id == original_user_id
    assert user.client_profile.id == client_profile_id


def test_business_owner_without_pro_still_has_client_context(app, client):
    """DEC-ID-069/073/077: owning a business does not require acting as Pro."""
    user = _user(email="qa001-owner@example.com")
    business = _establishment(user, "Studio Propriedade")
    token = issue_session(user).access_token

    response = _me(client, token)
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["role"] == "establishment"  # old mobile consumers
    assert [item["kind"] for item in payload["contexts"]] == [
        "client", "establishment",
    ]
    assert payload["contexts"][1]["id"] == str(business.id)
    assert payload["contexts"][1]["role"] == "owner"
    assert user.professional_profile is None
    assert user.client_profile is not None


def test_contexts_are_isolated_and_update_after_grant_revocation(app, client):
    """QA-001-UX-02: two owners cannot discover each other's private contexts."""
    owner = _user(email="qa001-owner-a@example.com", name="Pessoa A")
    other = _user(email="qa001-owner-b@example.com", name="Pessoa B")
    business_a = _establishment(owner, "Studio A")
    business_a2 = _establishment(owner, "Studio Extra")
    business_b = _establishment(other, "Studio B")
    token_a = issue_session(owner).access_token
    token_b = issue_session(other).access_token

    def establishment_ids(response):
        assert response.status_code == 200
        return {
            item["id"]
            for item in response.get_json()["contexts"]
            if item["kind"] == "establishment"
        }

    assert establishment_ids(_me(client, token_a)) == {
        str(business_a.id), str(business_a2.id),
    }
    assert establishment_ids(_me(client, token_b)) == {str(business_b.id)}

    access = db.session.scalar(
        select(EstablishmentUserAccess).where(
            EstablishmentUserAccess.user_id == owner.id,
            EstablishmentUserAccess.establishment_id == business_a.id,
        )
    )
    access.status = EstablishmentAccessStatus.INACTIVE
    db.session.commit()

    assert establishment_ids(_me(client, token_a)) == {str(business_a2.id)}
    assert establishment_ids(_me(client, token_b)) == {str(business_b.id)}
    assert _me(client, "invalid-token").status_code == 401
    assert client.get("/api/v1/auth/me").status_code == 401
