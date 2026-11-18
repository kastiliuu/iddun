"""P-002 (Wizard A) e P-003 (Catálogo C) na Web — V1 PR 2.

O Wizard só reorganiza o formulário existente: um POST, CSRF, rascunho,
nenhum horário, reserva ou post criado. O catálogo mostra à direita só o
serviço selecionado do próprio profissional, com ações conforme o estado.
"""

import re
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select

from app.extensions import db
from app.models.booking import Booking, ExperienceSlot, SlotStatus
from app.models.experience import Experience, ExperienceStatus
from app.models.professional import ProfessionalProfile
from app.models.professional_schedule import ProfessionalWorkingHour
from app.models.user import User, UserRole
from app.models.work_post import WorkPost

STEPS = ["Básico", "Preço e duração", "Local e disponibilidade", "Imagem", "Revisão"]


def _login(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


def _pro(email, slug, *, timezone_name="America/Sao_Paulo"):
    user = User(name=f"Pro {slug}", email=email, role=UserRole.PROFESSIONAL)
    user.set_password("senha-forte-123")
    profile = ProfessionalProfile(
        user=user, display_name=f"Pro {slug}", slug=slug, city="Curitiba", state="PR",
        timezone=timezone_name, onboarding_completed=True, is_active=True,
    )
    db.session.add_all([user, profile])
    db.session.flush()
    return user, profile


def _service(profile, title, slug, status, *, created_at=None):
    item = Experience(
        professional=profile, title=title, slug=slug, category="unhas",
        short_description=f"Resumo de {title}.", regular_price=Decimal("120.00"),
        price=Decimal("100.00"), duration_minutes=60, status=status,
    )
    if created_at is not None:
        item.created_at = created_at
    db.session.add(item)
    db.session.flush()
    return item


def _slot(item, starts_at, status=SlotStatus.AVAILABLE):
    slot = ExperienceSlot(
        experience=item, professional=item.professional, starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=item.duration_minutes), status=status,
    )
    db.session.add(slot)
    db.session.flush()
    return slot


def _setup(app):
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with app.app_context():
        user, profile = _pro("pro-wizard@example.com", "pro-wizard")
        published = _service(profile, "Esmaltação em gel", "esmaltacao-wizard", ExperienceStatus.PUBLISHED, created_at=base)
        draft = _service(profile, "Spa dos pés", "spa-wizard", ExperienceStatus.DRAFT, created_at=base + timedelta(days=1))
        future = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) + timedelta(days=2)
        _slot(published, future)
        _slot(published, future + timedelta(hours=1), SlotStatus.BLOCKED_MANUAL)
        other_user, other = _pro("outra-wizard@example.com", "outra-wizard")
        foreign = _service(other, "Serviço de outra pessoa", "servico-outra-wizard", ExperienceStatus.PUBLISHED)
        _slot(foreign, future)
        db.session.commit()
        return {
            "user": user.id, "profile": profile.id, "published": published.id,
            "draft": draft.id, "foreign": foreign.id, "other_user": other_user.id,
        }


def _page(client, path):
    response = client.get(path)
    assert response.status_code == 200
    return response.get_data(as_text=True)


# ---------------------------------------------------------------- Wizard A

def test_wizard_has_five_steps_in_order_in_one_csrf_form(app, client):
    ids = _setup(app)
    _login(client, ids["user"])
    html = _page(client, "/pro/servicos/novo")

    assert html.count("data-service-wizard") == 1
    assert 'name="csrf_token"' in html
    assert 'enctype="multipart/form-data"' in html
    positions = [html.index(f'<span class="service-wizard__progress-label">{label}</span>') for label in STEPS]
    assert positions == sorted(positions)
    for key in ("basico", "preco", "local", "imagem", "revisao"):
        assert f'id="etapa-{key}"' in html
    # Sem JavaScript tudo aparece: o servidor não esconde etapas.
    assert not re.search(r'<fieldset[^>]*data-step="[a-z]+"[^>]*hidden', html)
    assert "Salvar rascunho" in html
    # Publicar é ato separado e não existe no Wizard.
    assert "Publicar" not in html
    assert "/publicar" not in html
    assert "js/service-wizard.js" in html


def test_wizard_location_step_only_informs_about_availability(app, client):
    ids = _setup(app)
    _login(client, ids["user"])
    html = _page(client, "/pro/servicos/novo")
    assert "Salvar não abre horários" in html
    assert "Sua jornada semanal ainda não está configurada." in html
    assert "/horarios" not in html

    with app.app_context():
        for weekday in (0, 2):
            db.session.add(ProfessionalWorkingHour(
                professional_id=ids["profile"], weekday=weekday,
                start_time=time(9), end_time=time(18),
            ))
        db.session.commit()
    html = _page(client, "/pro/servicos/novo")
    assert "Sua jornada semanal tem 2 dias configurados." in html


def test_saving_the_wizard_creates_only_a_private_draft(app, client):
    ids = _setup(app)
    _login(client, ids["user"])
    with app.app_context():
        before = {
            "slots": db.session.scalar(select(func.count(ExperienceSlot.id))),
            "bookings": db.session.scalar(select(func.count(Booking.id))),
            "posts": db.session.scalar(select(func.count(WorkPost.id))),
        }

    response = client.post("/pro/servicos/novo", data={
        "title": "Alongamento em fibra",
        "category": "unhas",
        "short_description": "Alongamento com acabamento natural.",
        "description": "",
        "regular_price": "180.00",
        "price": "160.00",
        "duration_minutes": "120",
        "establishment_id": "0",
    })
    assert response.status_code == 302

    with app.app_context():
        created = db.session.scalar(select(Experience).where(Experience.title == "Alongamento em fibra"))
        assert created.status == ExperienceStatus.DRAFT
        assert created.regular_price == Decimal("180.00")
        assert created.price == Decimal("160.00")
        assert db.session.scalar(select(func.count(ExperienceSlot.id))) == before["slots"]
        assert db.session.scalar(select(func.count(Booking.id))) == before["bookings"]
        assert db.session.scalar(select(func.count(WorkPost.id))) == before["posts"]

    # O rascunho novo é o primeiro da lista e não fica reservável.
    html = _page(client, "/pro/servicos")
    assert "Alongamento em fibra" in html
    assert "Publicar serviço" in html


def test_server_error_keeps_typed_values_and_marks_the_price_step(app, client):
    ids = _setup(app)
    _login(client, ids["user"])
    response = client.post("/pro/servicos/novo", data={
        "title": "Preço trocado",
        "category": "unhas",
        "short_description": "Resumo mantido.",
        "regular_price": "50.00",
        "price": "80.00",
        "duration_minutes": "60",
        "establishment_id": "0",
    })
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'value="Preço trocado"' in html
    assert 'value="Resumo mantido."' in html
    assert "O preço IDDUN não pode ser maior que o preço regular." in html
    price_step = html[html.index('id="etapa-preco"'):html.index('id="etapa-local"')]
    assert 'aria-invalid="true"' in price_step
    assert 'aria-describedby="price-help price-errors"' in price_step
    with app.app_context():
        assert db.session.scalar(select(Experience).where(Experience.title == "Preço trocado")) is None


def test_edit_wizard_keeps_status_and_returns_to_the_selected_service(app, client):
    ids = _setup(app)
    _login(client, ids["user"])
    html = _page(client, f"/pro/servicos/{ids['draft']}/editar")
    assert "Salvar alterações" in html
    assert "Revisão" in html

    response = client.post(f"/pro/servicos/{ids['draft']}/editar", data={
        "title": "Spa dos pés completo",
        "category": "unhas",
        "short_description": "Resumo novo.",
        "regular_price": "120.00",
        "price": "100.00",
        "duration_minutes": "60",
        "establishment_id": "0",
    })
    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/pro/servicos?servico={ids['draft']}")
    with app.app_context():
        assert db.session.get(Experience, ids["draft"]).status == ExperienceStatus.DRAFT


# ---------------------------------------------------------------- Catálogo C

def test_catalog_lists_owned_services_and_details_only_the_selected_one(app, client):
    ids = _setup(app)
    _login(client, ids["user"])
    html = _page(client, f"/pro/servicos?servico={ids['published']}")

    assert "Esmaltação em gel" in html and "Spa dos pés" in html
    assert "Serviço de outra pessoa" not in html
    index = html[html.index('class="pro-catalog-list"'):html.index('id="servico-selecionado"')]
    assert index.count('aria-current="true"') == 1
    assert f'href="/pro/servicos?servico={ids["published"]}#servico-selecionado" aria-current="true"' in html
    # AC-CAT-02: um só conjunto de formulários de horário, o do selecionado.
    assert html.count("/horarios/lote") == 1
    assert html.count("/horarios/jornada") == 1
    assert f'/pro/servicos/{ids["published"]}/horarios"' in html
    assert f'/pro/servicos/{ids["draft"]}/horarios' not in html
    # Horários reais, com bloquear e liberar conforme o estado.
    assert "Bloquear horário" in html and "Liberar horário" in html
    # Publicado: pausar e visualizar; editar não é oferecido.
    assert "Pausar serviço" in html
    assert "Visualizar e consultar horários" in html
    assert f'/pro/servicos/{ids["published"]}/editar' not in html
    assert "pro-catalog--detail" in html


def test_catalog_draft_panel_offers_edit_and_publish_but_no_slots(app, client):
    ids = _setup(app)
    _login(client, ids["user"])
    html = _page(client, f"/pro/servicos?servico={ids['draft']}")
    detail = html[html.index('id="servico-selecionado"'):]
    assert "Spa dos pés" in detail
    assert f'/pro/servicos/{ids["draft"]}/editar' in detail
    assert "Publicar serviço" in detail
    assert "Pausar serviço" not in detail
    assert "Visualizar e consultar horários" not in detail
    assert "/horarios" not in detail
    assert "não está disponível para reservas públicas enquanto estiver rascunho" in detail


def test_catalog_without_selection_picks_the_newest_and_stays_on_the_list_on_phones(app, client):
    ids = _setup(app)
    _login(client, ids["user"])
    html = _page(client, "/pro/servicos")
    # O mais recente (rascunho) fica selecionado nas telas amplas...
    detail = html[html.index('id="servico-selecionado"'):]
    assert "Spa dos pés" in detail
    # ...e no celular a lista vem primeiro (sem a classe de detalhe).
    assert "pro-catalog--detail" not in html


def test_catalog_never_selects_someone_elses_service(app, client):
    ids = _setup(app)
    _login(client, ids["user"])
    for value in (ids["foreign"], 999999, "abc"):
        html = _page(client, f"/pro/servicos?servico={value}")
        assert "Serviço de outra pessoa" not in html
        assert f"/pro/servicos/{ids['foreign']}/" not in html
        assert "pro-catalog--detail" not in html


def test_slot_dialog_opens_from_the_server_only_for_published_services(app, client):
    ids = _setup(app)
    _login(client, ids["user"])
    html = _page(client, f"/pro/servicos?servico={ids['published']}&abrir=lote")
    assert re.search(r'id="slot-dialog-lote"[^>]*data-dialog open', html)
    assert not re.search(r'id="slot-dialog-horario"[^>]*data-dialog open', html)
    assert html.count('name="csrf_token"') >= 7

    html = _page(client, f"/pro/servicos?servico={ids['draft']}&abrir=lote")
    assert 'id="slot-dialog-lote"' not in html

    html = _page(client, f"/pro/servicos?servico={ids['published']}&abrir=qualquer")
    assert not re.search(r'data-dialog open', html)


def test_slot_actions_return_to_the_same_selected_service(app, client, monkeypatch):
    ids = _setup(app)
    _login(client, ids["user"])
    monkeypatch.setattr("app.routes.platform.create_availability", lambda **kwargs: None)
    response = client.post(
        f"/pro/servicos/{ids['published']}/horarios",
        data={"slot_date": "2027-03-10", "slot_time": "10:00"},
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/pro/servicos?servico={ids['published']}")


def test_other_professional_cannot_act_on_the_selected_service(app, client):
    ids = _setup(app)
    _login(client, ids["other_user"])
    for action in ("publicar", "pausar"):
        assert client.post(f"/pro/servicos/{ids['published']}/{action}").status_code == 404
    with app.app_context():
        assert db.session.get(Experience, ids["published"]).status == ExperienceStatus.PUBLISHED
