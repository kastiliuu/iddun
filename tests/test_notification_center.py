"""PR 6a do programa IDDUN 2.0 — central de notificações (D-SOC-21 a 23).

- Quem é avisado de quê: reservas (Cliente e Pro), social e vínculos.
- O mesmo evento não avisa duas vezes; curtidas viram um aviso só.
- Falha ao avisar nunca desfaz a ação.
- Central Web: abas, só não lidas, abrir marca como lido e revalida o
  destino, marcar todas é explícito, preferências com reservas essenciais.
"""

import re
from datetime import timedelta

import pytest
from flask import g
from sqlalchemy import select

from app.extensions import db
from app.models.booking import ExperienceSlot, SlotStatus
from app.models.establishment import (
    Establishment,
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
    EstablishmentUserAccess,
    MembershipStatus,
    ProfessionalEstablishmentMembership,
)
from app.models.experience import Experience, ExperienceStatus
from app.models.notification import Notification, NotificationPreference
from app.models.professional import ProfessionalProfile
from app.models.profile import ClientProfile
from app.models.user import User, UserRole
from app.models.work_post import WorkPost, WorkPostAuthorType, WorkPostStatus
from app.services import notification_events
from app.services.time_service import utcnow


def _user(email, name):
    user = User(name=name, email=email, role=UserRole.CLIENT)
    user.set_password("senha-forte-123")
    db.session.add(user)
    db.session.flush()
    db.session.add(ClientProfile(user=user))
    db.session.flush()
    return user


@pytest.fixture
def world(app):
    """Pro com conta, empresa com dona, Cliente e um horário livre."""
    with app.app_context():
        pro_user = _user("pro-notif@example.com", "Marina Pro")
        owner = _user("dona-notif@example.com", "Dona Studio")
        client_user = _user("cliente-notif@example.com", "Ana Cliente")
        pro = ProfessionalProfile(
            user=pro_user, display_name="Marina Pro", slug="marina-notif",
            primary_specialty="Colorista", city="Curitiba", state="PR", is_active=True,
        )
        business = Establishment(name="Studio Notif", slug="studio-notif", city="Curitiba", state="PR", is_active=True)
        db.session.add_all([pro, business])
        db.session.flush()
        db.session.add(EstablishmentUserAccess(
            user=owner, establishment=business,
            role=EstablishmentAccessRole.OWNER, status=EstablishmentAccessStatus.ACTIVE,
        ))
        experience = Experience(
            professional=pro, establishment=business, title="Mechas Notif", slug="mechas-notif",
            category="cabelo", short_description="Teste de notificações.", regular_price="300.00",
            price="250.00", duration_minutes=60, status=ExperienceStatus.PUBLISHED,
        )
        db.session.add(experience)
        db.session.flush()
        start = utcnow() + timedelta(days=3)
        slot = ExperienceSlot(
            experience=experience, professional=pro, establishment=business,
            starts_at=start, ends_at=start + timedelta(hours=1), status=SlotStatus.AVAILABLE,
        )
        db.session.add(slot)
        db.session.commit()
        return {
            "pro_user": pro_user.id, "owner": owner.id, "client_user": client_user.id,
            "pro": pro.id, "business": business.id, "slot": slot.id,
            "client_profile": client_user.client_profile.id,
        }


def _notices(app, user_id, **filters):
    with app.app_context():
        query = select(Notification).where(Notification.user_id == user_id, **{}).order_by(Notification.id)
        rows = db.session.scalars(query).all()
        return [
            (row.kind, row.category, row.title, row.context_type, row.group_count)
            for row in rows
            if all(getattr(row, key) == value for key, value in filters.items())
        ]


def _confirmed_booking(app, world):
    from app.services.booking_service import confirm_booking, hold_slot

    with app.app_context():
        profile = db.session.get(ClientProfile, world["client_profile"])
        booking = confirm_booking(hold_slot(world["slot"], profile).id, profile)
        return booking.id


def _login(client, user_id):
    g.pop("_login_user", None)
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


# ----------------------------------------------------------- reservas


def test_confirmed_booking_notifies_client_and_pro_once(app, world, monkeypatch):
    sent = []
    monkeypatch.setattr(notification_events, "send_transactional_email", lambda **kw: sent.append(kw) or True)
    booking_id = _confirmed_booking(app, world)

    assert _notices(app, world["client_user"]) == [("booking", "bookings", "Reserva confirmada", "client", 1)]
    assert _notices(app, world["pro_user"]) == [("booking", "bookings", "Nova reserva", "professional", 1)]
    assert [item["to_email"] for item in sent] == ["cliente-notif@example.com"]  # e-mail essencial (D-SOC-23)

    # O mesmo evento de novo não duplica aviso nem e-mail (DEC-ID-219).
    with app.app_context():
        from app.models.booking import Booking

        notification_events.booking_confirmed(db.session.get(Booking, booking_id))
    assert len(_notices(app, world["client_user"])) == 1
    assert len(sent) == 1


def test_cancel_complete_and_requests_reach_the_right_side(app, world, monkeypatch):
    monkeypatch.setattr(notification_events, "send_transactional_email", lambda **kw: True)
    booking_id = _confirmed_booking(app, world)
    from app.models.booking import Booking
    from app.services.cancellation_request_service import request_cancellation
    from app.services.booking_service import cancel_booking

    with app.app_context():
        booking = db.session.get(Booking, booking_id)
        request_cancellation(booking, db.session.get(User, world["client_user"]))
        assert ("booking", "bookings", "Pedido de cancelamento", "professional", 1) in _notices(app, world["pro_user"])
        cancel_booking(db.session.get(Booking, booking_id), reason="Cancelada pelo profissional")

    assert ("booking", "bookings", "Reserva cancelada", "client", 1) in _notices(app, world["client_user"])
    assert ("booking", "bookings", "Reserva cancelada", "professional", 1) in _notices(app, world["pro_user"])

    with app.app_context():
        booking = db.session.get(Booking, booking_id)
        notification_events.booking_completed(booking)
    assert ("booking", "bookings", "Como foi o atendimento?", "client", 1) in _notices(app, world["client_user"])


def test_notification_failure_never_undoes_the_booking(app, world, monkeypatch):
    def boom(**kwargs):
        raise RuntimeError("serviço de avisos fora do ar")

    monkeypatch.setattr(notification_events, "create_notification", boom)
    booking_id = _confirmed_booking(app, world)
    with app.app_context():
        from app.models.booking import Booking, BookingStatus

        assert db.session.get(Booking, booking_id).status == BookingStatus.CONFIRMED
    assert _notices(app, world["client_user"]) == []


# ------------------------------------------------------------- social


def test_likes_become_one_notice_and_comments_reach_author_and_parent(app, world):
    from app.services.post_interactions import add_comment, set_like

    with app.app_context():
        post = WorkPost(
            author_type=WorkPostAuthorType.PROFESSIONAL, professional_id=world["pro"],
            status=WorkPostStatus.PUBLISHED, published_at=utcnow(), caption="Loiro iluminado com tonalização",
        )
        db.session.add(post)
        fans = [_user(f"fa{index}@example.com", f"Fã{index} Teste") for index in range(3)]
        db.session.commit()
        post_id, fan_ids = post.id, [fan.id for fan in fans]

        set_like(db.session.get(User, world["pro_user"]), post_id, True)  # a própria autora
        for fan_id in fan_ids:
            set_like(db.session.get(User, fan_id), post_id, True)

    likes = _notices(app, world["pro_user"], kind="like")
    assert likes == [("like", "social", "Fã2 e mais 2 pessoas curtiram sua publicação", "professional", 3)]

    with app.app_context():
        first = add_comment(db.session.get(User, fan_ids[0]), post_id, "Que lindo!")
        add_comment(db.session.get(User, fan_ids[1]), post_id, "Concordo", parent_id=first.id)

    assert [item[2] for item in _notices(app, world["pro_user"], kind="comment")] == [
        "Fã0 comentou sua publicação", "Fã1 comentou sua publicação",
    ]
    assert [item[2] for item in _notices(app, fan_ids[0], kind="comment")] == ["Fã1 respondeu ao seu comentário"]


def test_follow_and_membership_reach_pro_and_owners(app, world):
    from app.models.beauty_graph import FollowTarget
    from app.services.beauty_graph_service import follow_target
    from app.services.establishment_team_service import accept_invitation

    with app.app_context():
        client_user = db.session.get(User, world["client_user"])
        follow_target(user=client_user, target_type=FollowTarget.PROFESSIONAL, target_id=world["pro"])
        follow_target(user=client_user, target_type=FollowTarget.ESTABLISHMENT, target_id=world["business"])
        membership = ProfessionalEstablishmentMembership(
            professional_id=world["pro"], establishment_id=world["business"], status=MembershipStatus.PENDING,
        )
        db.session.add(membership)
        db.session.commit()
        notification_events.membership_invited(membership)
        accept_invitation(user=db.session.get(User, world["pro_user"]), membership_id=membership.id)

    assert ("follow", "social", "Novo seguidor", "professional", 1) in _notices(app, world["pro_user"])
    assert ("membership", "work", "Convite de vínculo", "professional", 1) in _notices(app, world["pro_user"])
    owner = _notices(app, world["owner"])
    assert ("follow", "social", "Novo seguidor", "establishment", 1) in owner
    assert ("membership", "work", "Convite aceito", "establishment", 1) in owner


def test_preferences_silence_social_but_never_bookings(app, world, monkeypatch):
    monkeypatch.setattr(notification_events, "send_transactional_email", lambda **kw: True)
    from app.models.beauty_graph import FollowTarget
    from app.services.beauty_graph_service import follow_target

    with app.app_context():
        db.session.add(NotificationPreference(
            user_id=world["pro_user"], social_enabled=False, booking_enabled=False,
        ))
        db.session.commit()
        follow_target(user=db.session.get(User, world["client_user"]), target_type=FollowTarget.PROFESSIONAL, target_id=world["pro"])
    _confirmed_booking(app, world)

    kinds = [item[0] for item in _notices(app, world["pro_user"])]
    assert kinds == ["booking"]  # reserva essencial chega; seguidor não


# --------------------------------------------------------------- Web


def _seed_notices(app, world):
    from app.services.notification_service import create_notification

    with app.app_context():
        pro = db.session.get(User, world["pro_user"])
        ids = {}
        ids["booking"] = create_notification(
            user=pro, kind="booking", title="Nova reserva", body="Ana reservou Mechas.",
            action_type="pro_booking", action_id="999999", context_type="professional", context_id=world["pro"],
        ).id
        ids["follow"] = create_notification(
            user=pro, kind="follow", title="Novo seguidor", body="Ana começou a seguir você.",
            action_type="followers", action_id=world["pro"], context_type="professional", context_id=world["pro"],
        ).id
        ids["team"] = create_notification(
            user=pro, kind="membership", title="Convite aceito", body="Studio.",
            action_type="business_team", action_id="studio-notif",
            context_type="establishment", context_id=world["business"],
        ).id
        return ids


def test_center_tabs_unread_filter_and_explicit_read(app, client, world):
    ids = _seed_notices(app, world)
    _login(client, world["pro_user"])

    html = client.get("/notificacoes").get_data(as_text=True)
    counts = dict(re.findall(r">(Todas|Reservas|Social|Profissional e Empresa) <span class=\"notifications-tabs__count\">(\d+)<", html))
    assert counts == {"Todas": "3", "Reservas": "1", "Social": "1", "Profissional e Empresa": "1"}
    assert "3 não lidas" in html
    # Abrir a central não marca nada (DEC-ID-220).
    with app.app_context():
        assert db.session.scalar(select(Notification.read_at).where(Notification.id == ids["follow"])) is None

    social = client.get("/notificacoes?aba=social").get_data(as_text=True)
    assert "Novo seguidor" in social and "Nova reserva" not in social

    client.post(f"/notificacoes/{ids['follow']}/lida", data={"aba": "social"})
    unread = client.get("/notificacoes?nao_lidas=1").get_data(as_text=True)
    assert "Novo seguidor" not in unread and "Nova reserva" in unread

    response = client.post("/notificacoes/lidas")
    assert response.status_code == 302
    assert "Nada novo por enquanto" in client.get("/notificacoes").get_data(as_text=True)


def test_opening_marks_read_and_revalidates_the_destination(app, client, world):
    ids = _seed_notices(app, world)
    _login(client, world["pro_user"])

    follow = client.get(f"/notificacoes/{ids['follow']}/abrir")
    assert follow.headers["Location"].endswith("/profissionais/marina-notif")

    # Reserva que não é desta conta: nada é aberto.
    booking = client.get(f"/notificacoes/{ids['booking']}/abrir")
    assert booking.headers["Location"].endswith("/notificacoes")

    # Empresa sem acesso: o rótulo não mostra o nome e o destino não abre.
    html = client.get("/notificacoes?aba=profissional").get_data(as_text=True)
    assert "Studio Notif" not in html
    team = client.get(f"/notificacoes/{ids['team']}/abrir")
    assert team.headers["Location"].endswith("/notificacoes")

    with app.app_context():
        reads = db.session.scalars(select(Notification.read_at).where(Notification.user_id == world["pro_user"])).all()
        assert all(value is not None for value in reads)

    # Aviso de outra pessoa: 404.
    _login(client, world["client_user"])
    assert client.get(f"/notificacoes/{ids['follow']}/abrir").status_code == 404


def test_preferences_form_keeps_bookings_essential(app, client, world):
    _login(client, world["pro_user"])
    response = client.post("/notificacoes/preferencias", data={"profissional": "1"})
    assert response.status_code == 302
    with app.app_context():
        preference = db.session.scalar(select(NotificationPreference).where(NotificationPreference.user_id == world["pro_user"]))
        assert (preference.social_enabled, preference.work_enabled) == (False, True)
    html = client.get("/notificacoes").get_data(as_text=True)
    assert "Sempre ativas" in html


def test_api_lists_by_category_with_counts_and_context(app, client, world):
    _seed_notices(app, world)
    _login(client, world["pro_user"])

    data = client.get("/api/v1/notifications?category=social").get_json()
    assert [item["title"] for item in data["items"]] == ["Novo seguidor"]
    assert data["items"][0]["category"] == "social"
    assert data["items"][0]["contextLabel"] == "Profissional"
    assert data["counts"] == {"all": 3, "bookings": 1, "social": 1, "work": 1}
    assert client.get("/api/v1/notifications?category=senha").status_code == 400


def test_bell_links_to_the_center(app, client, world):
    _login(client, world["pro_user"])
    html = client.get("/favoritos").get_data(as_text=True)
    assert 'href="/notificacoes"' in html


# ------------------------------------------------- PR 6b: abrir pelo app


def test_api_open_marks_read_and_returns_only_authorized_targets(app, client, world, monkeypatch):
    """PR 6b (DEC-ID-220, 221): o app recebe o destino só se o acesso vale."""
    monkeypatch.setattr(notification_events, "send_transactional_email", lambda **kw: True)
    ids = _seed_notices(app, world)
    booking_id = _confirmed_booking(app, world)
    _login(client, world["pro_user"])

    follow = client.put(f"/api/v1/notifications/{ids['follow']}/open", json={})
    assert follow.status_code == 200
    data = follow.get_json()
    assert data["notification"]["read"] is True
    assert data["notification"]["contextLabel"] == "Profissional"
    assert data["target"] == {"type": "professional", "id": "marina-notif", "webPath": "/profissionais/marina-notif"}
    assert follow.headers["Cache-Control"] == "private, no-store"

    # Reserva de outra conta e empresa sem acesso: marca como lido, sem destino.
    for key in ("booking", "team"):
        response = client.put(f"/api/v1/notifications/{ids[key]}/open", json={})
        assert response.status_code == 200
        assert response.get_json()["target"] is None
        assert response.get_json()["notification"]["read"] is True

    # A Cliente abre a própria reserva confirmada pelo app.
    _login(client, world["client_user"])
    with app.app_context():
        notice = db.session.scalar(select(Notification).where(
            Notification.user_id == world["client_user"], Notification.action_type == "booking",
        ))
    opened = client.put(f"/api/v1/notifications/{notice.id}/open", json={}).get_json()
    assert opened["target"]["type"] == "booking"
    assert opened["target"]["id"] == str(booking_id)

    # Aviso de outra pessoa: 404 e continua não lido para o dono.
    denied = client.put(f"/api/v1/notifications/{ids['follow']}/open", json={})
    assert denied.status_code == 404
    assert denied.get_json()["error"]["code"] == "notification_not_found"


def test_api_open_requires_login(client):
    assert client.put("/api/v1/notifications/1/open", json={}).status_code == 401


def test_api_open_gives_the_owner_the_business_team(app, client, world):
    from app.services.notification_service import create_notification

    with app.app_context():
        owner = db.session.get(User, world["owner"])
        notice = create_notification(
            user=owner, kind="membership", title="Convite aceito", body="Marina aceitou.",
            action_type="business_team", action_id="studio-notif",
            context_type="establishment", context_id=world["business"],
        ).id
    _login(client, world["owner"])
    data = client.put(f"/api/v1/notifications/{notice}/open", json={}).get_json()
    assert data["notification"]["contextLabel"] == "Studio Notif"
    assert data["target"]["type"] == "business_team"
    assert data["target"]["id"] == "studio-notif"
    assert data["target"]["webPath"].startswith("/business/studio-notif/")
