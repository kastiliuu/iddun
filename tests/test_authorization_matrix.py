"""SEC-INTEGRITY-01a — matriz de autorização entre identidades.

Cada rota que recebe o identificador de um recurso privado é chamada por
identidades que NÃO são donas desse recurso (Cliente B, Pro B, proprietário
de outro estabelecimento) e por um visitante anônimo. Para todas elas a
matriz exige, ao mesmo tempo:

1. resposta de recusa (redirecionamento ou 4xx, nunca 2xx de sucesso nem 5xx);
2. nenhum dado privado da vítima no corpo da resposta;
3. banco de dados idêntico antes e depois da chamada.

Regras cobertas: DEC-ID-012/013 (papéis locais ao estabelecimento),
DEC-ID-017 (agenda privada), DEC-ID-022 (ações exclusivas do executor),
DEC-ID-170 (a API autoriza links diretos) e o gate P0 da página 79
(isolamento multitenant).

Os testes não alteram comportamento: eles travam o isolamento atual contra
regressões. Rotas de /admin ficam fora desta matriz (papel global, ver
pergunta Q1 da auditoria de 27/10/2026).
"""

from datetime import date, timedelta
import hashlib
import json

import pytest
from flask import g
from sqlalchemy import select

from app.extensions import db, limiter
from app.models.api_session import ApiSession
from app.models.booking import (
    Booking,
    BookingStatus,
    ExperienceSlot,
    SlotStatus,
)
from app.models.cancellation_request import CancellationRequest
from app.models.certification import ProfessionalCertification
from app.models.establishment import (
    Establishment,
    EstablishmentAccessRole,
    EstablishmentGalleryItem,
    EstablishmentUserAccess,
    MembershipStatus,
    ProfessionalEstablishmentMembership,
)
from app.models.experience import Experience, ExperienceStatus
from app.models.job import JobPost
from app.models.notification import Notification
from app.models.professional import (
    ProfessionalPortfolioItem,
    ProfessionalProfile,
)
from app.models.professional_experience import ProfessionalExperience
from app.models.profile import ClientProfile
from app.models.reschedule_request import RescheduleRequest
from app.models.user import User, UserRole
from app.models.work_post import (
    WorkPost,
    WorkPostAuthorType,
    WorkPostStatus,
)
from app.services.api_auth import issue_session
from app.services.time_service import utcnow


# Textos que só existem em dados privados da vítima. Nenhum deles pode
# aparecer em resposta destinada a outra identidade.
SECRET_CLIENT_NAME = "Vitima Cliente Alfa"
SECRET_CLIENT_EMAIL = "vitima.cliente.alfa@example.com"
SECRET_MARKERS = (
    SECRET_CLIENT_NAME,
    SECRET_CLIENT_EMAIL,
    "SEGREDO-NOTIFICACAO",
    "SEGREDO-RASCUNHO-POST",
    "SEGREDO-VAGA-RASCUNHO",
    "SEGREDO-MOTIVO-CANCELAMENTO",
    "SEGREDO-CREDENCIAL",
)

# Colunas que registram apenas uso da própria sessão do ator (não são
# dados da vítima e mudam legitimamente a cada requisição autenticada).
VOLATILE_COLUMNS = {
    "api_sessions": {"last_used_at", "last_seen_at"},
}


# ---------------------------------------------------------------------------
# Mundo de teste: recursos privados da vítima (A) e três intrusos (B).
# ---------------------------------------------------------------------------


def _user(email, name, role=UserRole.CLIENT):
    user = User(name=name, email=email, role=role)
    user.set_password("senha-forte-123")
    db.session.add(user)
    db.session.flush()
    return user


def _professional(user, slug, name):
    profile = ProfessionalProfile(
        user_id=user.id,
        display_name=name,
        slug=slug,
        primary_specialty="Cabeleireira",
        city="Curitiba",
        state="PR",
    )
    db.session.add(profile)
    db.session.flush()
    return profile


def _establishment(slug, name, owner):
    establishment = Establishment(
        name=name,
        slug=slug,
        city="Curitiba",
        state="PR",
    )
    db.session.add(establishment)
    db.session.flush()
    db.session.add(
        EstablishmentUserAccess(
            user_id=owner.id,
            establishment_id=establishment.id,
            role=EstablishmentAccessRole.OWNER,
        )
    )
    db.session.flush()
    return establishment


def _slot(experience, professional, establishment, starts_at, status):
    slot = ExperienceSlot(
        experience=experience,
        professional=professional,
        establishment=establishment,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
        status=status,
    )
    db.session.add(slot)
    db.session.flush()
    return slot


def _booking(client, experience, slot, status):
    booking = Booking(
        client_id=client.id,
        experience_id=experience.id,
        professional_id=slot.professional_id,
        establishment_id=slot.establishment_id,
        slot_id=slot.id,
        status=status,
        price_at_booking="180.00",
        confirmed_at=utcnow(),
    )
    db.session.add(booking)
    db.session.flush()
    return booking


def _build_world():
    now = utcnow()

    # --- Vítima -----------------------------------------------------------
    client_a_user = _user(SECRET_CLIENT_EMAIL, SECRET_CLIENT_NAME)
    client_a = ClientProfile(user=client_a_user)
    db.session.add(client_a)

    pro_a_user = _user("pro.alfa@example.com", "Pro Alfa", UserRole.PROFESSIONAL)
    pro_a = _professional(pro_a_user, "pro-alfa", "Pro Alfa")

    owner_a = _user("dono.alfa@example.com", "Dono Alfa")
    est_a = _establishment("studio-alfa", "Studio Alfa", owner_a)

    other_owner = _user("dono.gama@example.com", "Dono Gama")
    est_invite = _establishment("studio-gama", "Studio Gama", other_owner)

    membership_active = ProfessionalEstablishmentMembership(
        professional_id=pro_a.id,
        establishment_id=est_a.id,
        status=MembershipStatus.ACTIVE,
        role_name="Cabeleireira",
    )
    membership_pending = ProfessionalEstablishmentMembership(
        professional_id=pro_a.id,
        establishment_id=est_invite.id,
        status=MembershipStatus.PENDING,
    )
    db.session.add_all([membership_active, membership_pending])

    service = Experience(
        professional=pro_a,
        establishment=est_a,
        title="Corte Alfa",
        slug="corte-alfa",
        category="cabelo",
        short_description="Serviço da vítima",
        regular_price="180.00",
        price="180.00",
        duration_minutes=60,
        status=ExperienceStatus.PUBLISHED,
    )
    db.session.add(service)
    db.session.flush()

    future = now + timedelta(days=3)
    slot_future = _slot(service, pro_a, est_a, future, SlotStatus.BOOKED)
    slot_future_2 = _slot(
        service, pro_a, est_a, future + timedelta(hours=2), SlotStatus.BOOKED
    )
    slot_available = _slot(
        service, pro_a, est_a, future + timedelta(hours=4), SlotStatus.AVAILABLE
    )
    slot_blocked = _slot(
        service, pro_a, est_a, future + timedelta(hours=6), SlotStatus.BLOCKED_MANUAL
    )
    slot_past = _slot(
        service, pro_a, est_a, now - timedelta(hours=3), SlotStatus.BOOKED
    )
    slot_done = _slot(
        service, pro_a, est_a, now - timedelta(days=2), SlotStatus.BOOKED
    )

    booking_future = _booking(client_a, service, slot_future, BookingStatus.CONFIRMED)
    booking_reschedule = _booking(
        client_a, service, slot_future_2, BookingStatus.CONFIRMED
    )
    booking_past = _booking(client_a, service, slot_past, BookingStatus.CONFIRMED)
    booking_done = _booking(client_a, service, slot_done, BookingStatus.COMPLETED)
    booking_done.completed_at = now - timedelta(days=2)

    db.session.add(
        CancellationRequest(
            booking_id=booking_future.id,
            client_user_id=client_a_user.id,
            reason="SEGREDO-MOTIVO-CANCELAMENTO",
            status="pending",
        )
    )
    db.session.add(
        RescheduleRequest(
            booking_id=booking_reschedule.id,
            requested_slot_id=slot_available.id,
            original_slot_id=slot_future_2.id,
            requested_by_user_id=client_a_user.id,
            status="pending",
        )
    )

    portfolio = ProfessionalPortfolioItem(
        professional_id=pro_a.id,
        image_url="/static/img/portfolio-alfa.jpg",
        caption="Portfólio Alfa",
    )
    certification = ProfessionalCertification(
        professional_id=pro_a.id,
        title="Colorimetria",
        issuer="Escola Alfa",
        credential_id="SEGREDO-CREDENCIAL",
    )
    work_experience = ProfessionalExperience(
        professional_id=pro_a.id,
        company_name="Salão Alfa",
        role_title="Cabeleireira",
        started_at=date(2020, 1, 1),
    )
    draft_post = WorkPost(
        author_type=WorkPostAuthorType.PROFESSIONAL,
        professional_id=pro_a.id,
        caption="SEGREDO-RASCUNHO-POST",
        image_url="/static/img/post-alfa.jpg",
        status=WorkPostStatus.DRAFT,
    )
    gallery = EstablishmentGalleryItem(
        establishment_id=est_a.id,
        image_url="/static/img/galeria-alfa.jpg",
        caption="Galeria Alfa",
    )
    job = JobPost(
        establishment_id=est_a.id,
        title="SEGREDO-VAGA-RASCUNHO",
        specialty="Cabeleireira",
        description="Vaga ainda não publicada.",
        city="Curitiba",
        state="PR",
    )
    notification = Notification(
        user_id=client_a_user.id,
        kind="booking",
        title="SEGREDO-NOTIFICACAO",
        body="Sua reserva foi confirmada.",
    )
    db.session.add_all(
        [
            portfolio,
            certification,
            work_experience,
            draft_post,
            gallery,
            job,
            notification,
        ]
    )
    db.session.flush()

    client_a_session = issue_session(client_a_user, device_name="Vítima")

    # --- Intrusos ---------------------------------------------------------
    client_b_user = _user("cliente.beta@example.com", "Cliente Beta")
    db.session.add(ClientProfile(user=client_b_user))

    pro_b_user = _user("pro.beta@example.com", "Pro Beta", UserRole.PROFESSIONAL)
    _professional(pro_b_user, "pro-beta", "Pro Beta")

    owner_b = _user("dono.beta@example.com", "Dono Beta")
    _establishment("studio-beta", "Studio Beta", owner_b)

    # Toda conta começa como Cliente (contexto mestre, seção 2). Criar o
    # perfil já aqui evita que `ensure_client_profile` conte como mudança.
    for user in (pro_a_user, owner_a, other_owner, pro_b_user, owner_b):
        db.session.add(ClientProfile(user=user))

    db.session.commit()

    client_a_api_session = db.session.scalar(
        select(ApiSession).where(ApiSession.user_id == client_a_user.id)
    )

    ids = {
        "booking": booking_future.id,
        "booking_reschedule": booking_reschedule.id,
        "booking_past": booking_past.id,
        "booking_done": booking_done.id,
        "slot_available": slot_available.id,
        "slot_blocked": slot_blocked.id,
        "service": service.id,
        "service_slug": service.slug,
        "portfolio": portfolio.id,
        "certification": certification.id,
        "work_experience": work_experience.id,
        "post": draft_post.id,
        "gallery": gallery.id,
        "job": job.id,
        "notification": notification.id,
        "session": client_a_api_session.id,
        "membership_active": membership_active.id,
        "membership_pending": membership_pending.id,
        "est_slug": est_a.slug,
        "est_id": est_a.id,
    }

    actors = {}
    for label, user in (
        ("cliente_b", client_b_user),
        ("pro_b", pro_b_user),
        ("dono_b", owner_b),
    ):
        actors[label] = {
            "user_id": user.id,
            "token": issue_session(user).access_token,
        }
    actors["anonimo"] = None

    owners = {
        "cliente_a": {
            "user_id": client_a_user.id,
            "token": client_a_session.access_token,
        },
        "pro_a": {
            "user_id": pro_a_user.id,
            "token": issue_session(pro_a_user).access_token,
        },
        "dono_a": {
            "user_id": owner_a.id,
            "token": issue_session(owner_a).access_token,
        },
    }
    return ids, actors, owners


def _database_digest():
    """Impressão digital de todas as linhas de todas as tabelas."""
    digest = hashlib.sha256()
    for table in db.metadata.sorted_tables:
        skip = VOLATILE_COLUMNS.get(table.name, set())
        columns = [column for column in table.columns if column.name not in skip]
        rows = db.session.execute(
            select(*columns).order_by(*table.primary_key.columns)
        ).all()
        digest.update(table.name.encode())
        for row in rows:
            digest.update(json.dumps(list(row), default=str).encode())
    return digest.hexdigest()


def _send(app, actor, method, path, body):
    # A fixture mantém um app context aberto e o Flask-Login guarda o
    # usuário em `g`: sem limpar, a requisição herdaria o ator anterior.
    g.pop("_login_user", None)
    # Um 429 também é 4xx sem mudança no banco e mascararia a checagem.
    # Zerar os contadores mantém o limitador ativo para o resto da suíte.
    limiter.reset()
    client = app.test_client()
    headers = {}
    if actor is not None:
        with client.session_transaction() as session:
            session["_user_id"] = str(actor["user_id"])
            session["_fresh"] = True
        headers["Authorization"] = f"Bearer {actor['token']}"

    kwargs = {"headers": headers}
    if body is not None:
        if path.startswith("/api/"):
            kwargs["json"] = body
        else:
            kwargs["data"] = body
    elif path.startswith("/api/") and method in {"POST", "PUT", "PATCH"}:
        kwargs["json"] = {}

    return client.open(path, method=method, **kwargs)


# ---------------------------------------------------------------------------
# Matriz: (método, rota, corpo). Placeholders vêm de `ids`.
# Os corpos são válidos para o dono, para que uma falha de autorização
# apareça como mudança no banco e não seja mascarada por validação.
# ---------------------------------------------------------------------------

CANCEL_REASON = {"motivo": "Imprevisto do executor", "reason": "Imprevisto"}

ROUTES = [
    # Reservas do Cliente — API (consumida pelo app)
    ("GET", "/api/v1/bookings/{booking}", None),
    ("GET", "/api/v1/bookings/{booking}/actions", None),
    ("GET", "/api/v1/bookings/{booking}/timeline", None),
    ("GET", "/api/v1/bookings/{booking}/calendar", None),
    ("GET", "/api/v1/bookings/{booking}/share", None),
    ("GET", "/api/v1/bookings/{booking_past}/no-show-disputes", None),
    ("GET", "/api/v1/bookings/{booking_done}/review", None),
    ("POST", "/api/v1/bookings/{booking}/confirm", None),
    ("POST", "/api/v1/bookings/{booking_reschedule}/cancel", {"reason": "Imprevisto"}),
    ("POST", "/api/v1/bookings/{booking}/cancel-request/withdraw", None),
    (
        "POST",
        "/api/v1/bookings/{booking}/reschedule-request",
        {"slotId": "{slot_available}", "reason": "Outro horário"},
    ),
    ("POST", "/api/v1/bookings/{booking_reschedule}/reschedule-request/withdraw", None),
    (
        "POST",
        "/api/v1/bookings/{booking_past}/no-show-disputes",
        {"justification": "Eu compareci ao atendimento.", "evidenceReference": ""},
    ),
    (
        "POST",
        "/api/v1/bookings/{booking_done}/review",
        {"rating": 1, "comment": "Avaliação forjada", "recommended": False},
    ),
    # Reservas do Cliente — Web
    ("GET", "/reserva/{booking}/confirmar", None),
    ("GET", "/reserva/{booking}/calendario.ics", None),
    ("GET", "/reserva/{booking}/compartilhar", None),
    ("GET", "/reserva/{booking_done}/reservar-novamente", None),
    ("GET", "/reserva/{booking_done}/avaliar", None),
    ("POST", "/reserva/{booking}/confirmar", None),
    ("POST", "/reserva/{booking_reschedule}/cancelar", {"motivo": "Imprevisto"}),
    ("POST", "/reserva/{booking}/cancelamento/retirar", None),
    (
        "POST",
        "/reserva/{booking}/reagendar",
        {"slot_id": "{slot_available}", "motivo": "Outro horário"},
    ),
    ("POST", "/reserva/{booking_reschedule}/reagendamento/retirar", None),
    (
        "POST",
        "/reserva/{booking_past}/no-show/contestar",
        {"justificativa": "Eu compareci ao atendimento.", "justification": "Eu compareci."},
    ),
    (
        "POST",
        "/reserva/{booking_done}/avaliar",
        {"rating": "1", "comment": "Avaliação forjada"},
    ),
    # Ações exclusivas do executor (DEC-ID-022) — Web
    ("POST", "/reserva/{booking}/cancelamento/efetivar", CANCEL_REASON),
    (
        "POST",
        "/reserva/{booking_reschedule}/reagendamento/decidir",
        {"decision": "approve", "motivo": "Aprovado"},
    ),
    ("POST", "/pro/painel/reservas/{booking}/cancelar", CANCEL_REASON),
    ("POST", "/pro/painel/reservas/{booking_past}/concluir", None),
    ("POST", "/pro/painel/reservas/{booking_past}/no-show", None),
    ("POST", "/pro/painel/horarios/{slot_available}/bloquear", None),
    ("POST", "/pro/painel/horarios/{slot_blocked}/liberar", None),
    # Catálogo e agenda do Pro — Web
    ("GET", "/pro/servicos/{service}/editar", None),
    ("POST", "/pro/servicos/{service}/editar", {"title": "Serviço sequestrado", "price": "1.00"}),
    ("POST", "/pro/servicos/{service}/pausar", None),
    ("POST", "/pro/servicos/{service}/publicar", None),
    (
        "POST",
        "/pro/servicos/{service}/horarios",
        {"slot_date": "2030-01-10", "slot_time": "10:00"},
    ),
    (
        "POST",
        "/pro/servicos/{service}/horarios/lote",
        {"slot_date": "2030-01-10", "times": "10:00, 11:00"},
    ),
    ("POST", "/pro/servicos/{service}/horarios/jornada", {"days": "7"}),
    ("POST", "/pro/servicos/{service}/horarios/{slot_available}/bloquear", None),
    ("POST", "/pro/servicos/{service}/horarios/{slot_blocked}/liberar", None),
    # Perfil do Pro — Web
    ("POST", "/pro/portfolio/{portfolio}/remover", None),
    ("POST", "/pro/certificacoes/{certification}/remover", None),
    (
        "POST",
        "/pro/experiencia-profissional/{work_experience}/editar",
        {"company_name": "Empresa forjada", "role_title": "Forjado", "started_at": "2021-01-01"},
    ),
    ("POST", "/pro/experiencia-profissional/{work_experience}/remover", None),
    ("POST", "/pro/vinculos/{membership_pending}/aceitar", None),
    ("POST", "/pro/vinculos/{membership_pending}/recusar", None),
    # Catálogo e agenda do Pro — API (app)
    ("GET", "/api/v1/onboarding/professional/services/{service}", None),
    (
        "PATCH",
        "/api/v1/onboarding/professional/services/{service}",
        {"name": "Serviço sequestrado", "price": "1.00"},
    ),
    ("POST", "/api/v1/onboarding/professional/services/{service}/status", {"status": "paused"}),
    ("GET", "/api/v1/onboarding/professional/services/{service}/availability", None),
    (
        "POST",
        "/api/v1/onboarding/professional/services/{service}/availability",
        {"date": "2030-01-10", "time": "10:00"},
    ),
    (
        "POST",
        "/api/v1/onboarding/professional/services/{service}/availability/{slot_available}/status",
        {"action": "block"},
    ),
    (
        "POST",
        "/api/v1/onboarding/professional/services/{service}/availability/{slot_blocked}/status",
        {"action": "reopen"},
    ),
    (
        "POST",
        "/api/v1/onboarding/professional/services/{service}/availability/from-schedule",
        {"days": 7},
    ),
    ("DELETE", "/api/v1/onboarding/professional/experiences/{work_experience}", None),
    ("DELETE", "/api/v1/media/professional/portfolio/{portfolio}", None),
    # Conteúdo
    ("GET", "/api/v1/posts/{post}", None),
    ("PUT", "/api/v1/posts/{post}", {"caption": "Legenda forjada", "status": "published"}),
    ("DELETE", "/api/v1/posts/{post}", None),
    # Conta
    ("PUT", "/api/v1/notifications/{notification}/read", None),
    ("POST", "/api/v1/auth/sessions/{session}/revoke", None),
    ("POST", "/api/auth/sessions/{session}/revoke", None),
    # Vínculos — API
    ("PUT", "/api/v1/team/invitations/{membership_pending}/accept", None),
    ("PUT", "/api/v1/team/invitations/{membership_pending}/reject", None),
    # Business — Web (DEC-ID-012/017)
    ("GET", "/business/{est_slug}/painel", None),
    ("GET", "/business/{est_slug}/reservas", None),
    ("GET", "/business/{est_slug}/servicos", None),
    ("GET", "/business/{est_slug}/indicadores", None),
    ("GET", "/business/{est_slug}/editar", None),
    ("POST", "/business/{est_slug}/editar", {"name": "Studio sequestrado"}),
    ("POST", "/business/{est_slug}/painel", {"name": "Studio sequestrado"}),
    ("POST", "/business/{est_slug}/equipe/{membership_active}/remover", None),
    ("POST", "/business/{est_slug}/galeria/{gallery}/remover", None),
    # Business — API (equipe e recrutamento)
    ("GET", "/api/v1/establishments/{est_slug}/team", None),
    ("GET", "/api/v1/establishments/{est_id}/team", None),
    (
        "POST",
        "/api/v1/establishments/{est_slug}/team",
        {"email": "pro.beta@example.com", "roleName": "Infiltrada"},
    ),
    ("DELETE", "/api/v1/establishments/{est_slug}/team/{membership_active}", None),
    ("GET", "/api/v1/establishments/{est_slug}/jobs", None),
    (
        "POST",
        "/api/v1/establishments/{est_slug}/jobs",
        {"title": "Vaga forjada", "specialty": "Cabeleireira", "city": "Curitiba"},
    ),
    ("PUT", "/api/v1/establishments/{est_slug}/jobs/{job}", {"title": "Vaga sequestrada"}),
    ("PUT", "/api/v1/establishments/{est_slug}/jobs/{job}/publish", None),
    ("PUT", "/api/v1/establishments/{est_slug}/jobs/{job}/close", None),
    ("GET", "/api/v1/establishments/{est_slug}/jobs/{job}/applications", None),
]


# Leituras públicas por natureza: o anônimo recebe 404 porque o recurso da
# vítima é rascunho, não por falta de login.
PUBLIC_READ_ROUTES = {
    ("GET", "/api/v1/posts/{post}"),
}


def _fill(template, ids):
    return template.format(**ids)


def _fill_body(body, ids):
    if body is None:
        return None
    filled = {}
    for key, value in body.items():
        if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
            value = ids[value[1:-1]]
        filled[key] = value
    return filled


def _route_id(route):
    method, path, _ = route
    return f"{method} {path}"


@pytest.mark.parametrize("route", ROUTES, ids=[_route_id(r) for r in ROUTES])
def test_route_denies_every_non_owner(app, route):
    ids, actors, _ = _build_world()
    method, template, body = route
    path = _fill(template, ids)
    payload = _fill_body(body, ids)

    for actor_label, actor in actors.items():
        before = _database_digest()
        response = _send(app, actor, method, path, payload)
        db.session.expire_all()
        after = _database_digest()

        context = f"{actor_label} -> {method} {path} ({response.status_code})"

        assert response.status_code != 429, f"rate limit mascarou o teste: {context}"
        assert response.status_code < 500, f"erro interno: {context}"
        assert not (200 <= response.status_code < 300), f"acesso concedido: {context}"
        if response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get("Location", "")
            assert path not in location, f"redirecionou para o próprio recurso: {context}"

        text = response.get_data(as_text=True)
        for marker in SECRET_MARKERS:
            assert marker not in text, f"vazou '{marker}': {context}"

        assert before == after, f"banco alterado: {context}"

        if actor is None:
            if (method, template) in PUBLIC_READ_ROUTES:
                assert response.status_code == 404, f"rascunho visível: {context}"
            elif path.startswith("/api/"):
                assert response.status_code == 401, f"anônimo sem 401: {context}"
            else:
                assert response.status_code in (302, 401), context


# ---------------------------------------------------------------------------
# Controles positivos: provam que os corpos acima são aceitos pelo dono e
# que a impressão digital do banco detecta a mudança. Sem eles, uma recusa
# por validação poderia passar como se fosse recusa por autorização.
# ---------------------------------------------------------------------------

OWNER_CONTROLS = [
    ("cliente_a", "POST", "/api/v1/bookings/{booking_reschedule}/cancel", {"reason": "Imprevisto"}),
    ("cliente_a", "PUT", "/api/v1/notifications/{notification}/read", None),
    ("cliente_a", "POST", "/api/v1/auth/sessions/{session}/revoke", None),
    ("cliente_a", "POST", "/reserva/{booking_reschedule}/cancelar", {"motivo": "Imprevisto"}),
    ("pro_a", "POST", "/reserva/{booking}/cancelamento/efetivar", CANCEL_REASON),
    ("pro_a", "POST", "/pro/painel/reservas/{booking_past}/concluir", None),
    ("pro_a", "POST", "/pro/painel/horarios/{slot_available}/bloquear", None),
    ("pro_a", "POST", "/pro/servicos/{service}/pausar", None),
    ("pro_a", "POST", "/pro/portfolio/{portfolio}/remover", None),
    ("pro_a", "POST", "/pro/certificacoes/{certification}/remover", None),
    ("pro_a", "DELETE", "/api/v1/media/professional/portfolio/{portfolio}", None),
    ("pro_a", "DELETE", "/api/v1/posts/{post}", None),
    (
        "pro_a",
        "POST",
        "/api/v1/onboarding/professional/services/{service}/availability/{slot_available}/status",
        {"action": "block"},
    ),
    ("pro_a", "PUT", "/api/v1/team/invitations/{membership_pending}/reject", None),
    ("dono_a", "POST", "/business/{est_slug}/galeria/{gallery}/remover", None),
    ("dono_a", "PUT", "/api/v1/establishments/{est_slug}/jobs/{job}/close", None),
]


@pytest.mark.parametrize(
    "control",
    OWNER_CONTROLS,
    ids=[f"{c[0]} {c[1]} {c[2]}" for c in OWNER_CONTROLS],
)
def test_owner_control_changes_database(app, control):
    ids, _, owners = _build_world()
    owner_label, method, template, body = control
    path = _fill(template, ids)

    before = _database_digest()
    response = _send(app, owners[owner_label], method, path, _fill_body(body, ids))
    db.session.expire_all()
    after = _database_digest()

    assert response.status_code < 400, f"{owner_label} {method} {path}: {response.status_code}"
    assert before != after, f"dono não alterou o banco: {owner_label} {method} {path}"
