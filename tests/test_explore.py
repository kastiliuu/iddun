"""PR 5a do programa IDDUN 2.0 — Explorar (D-SOC-18, 19; DEC-ID-179–187).

- Busca e descoberta só mostram posts de autores públicos, como o feed.
- A API ganha tipo, paginação, contagens, preço, horário e ordenação.
- /explorar tem abas com contagens reais, filtros no endereço e estado sem
  resultados honesto.
"""

import re
from datetime import timedelta
from decimal import Decimal

from app.extensions import db
from app.models.booking import ExperienceSlot, SlotStatus
from app.models.establishment import Establishment
from app.models.experience import Experience, ExperienceStatus
from app.models.professional import ProfessionalProfile
from app.models.profile import ClientProfile
from app.models.user import User
from app.models.work_post import WorkPost, WorkPostAuthorType, WorkPostStatus
from app.services.time_service import utcnow
from tests.test_api_graph import _catalog

SEARCH = "/api/v1/search"


def _post(app, caption, **author):
    with app.app_context():
        db.session.add(WorkPost(status=WorkPostStatus.PUBLISHED, published_at=utcnow(), caption=caption, **author))
        db.session.commit()


def _service(app, catalog, title, price, *, slot=False, slug=None):
    with app.app_context():
        experience = Experience(
            professional_id=catalog["professional"],
            establishment_id=catalog["establishment"],
            title=title,
            slug=slug or title.lower().replace(" ", "-"),
            category="cabelo",
            short_description="Serviço de teste do Explorar.",
            regular_price=Decimal(price),
            price=Decimal(price),
            duration_minutes=60,
            status=ExperienceStatus.PUBLISHED,
        )
        db.session.add(experience)
        db.session.flush()
        if slot:
            start = utcnow() + timedelta(days=2)
            db.session.add(ExperienceSlot(
                experience_id=experience.id,
                professional_id=catalog["professional"],
                establishment_id=catalog["establishment"],
                starts_at=start,
                ends_at=start + timedelta(hours=1),
                status=SlotStatus.AVAILABLE,
            ))
        db.session.commit()


# ------------------------------------------------- D-SOC-19 (visibilidade)


def test_search_and_discovery_only_show_posts_from_public_authors(app, client):
    catalog = _catalog(app)
    with app.app_context():
        hidden_pro = ProfessionalProfile(display_name="Pro Rascunho Sonda", slug="pro-rascunho-sonda", is_active=False)
        hidden_business = Establishment(name="Studio Inativo Sonda", slug="studio-inativo-sonda", is_active=False)
        user = User(name="Cliente Inativa Sonda", email="inativa-sonda@example.com", role="client")
        user.set_password("senha-forte-123")
        user.is_active_account = False
        client_profile = ClientProfile(user=user)
        db.session.add_all([hidden_pro, hidden_business, user, client_profile])
        db.session.commit()
        ids = (hidden_pro.id, hidden_business.id, client_profile.id)

    _post(app, "Sonda do rascunho", author_type=WorkPostAuthorType.PROFESSIONAL, professional_id=ids[0])
    _post(app, "Sonda do inativo", author_type=WorkPostAuthorType.ESTABLISHMENT, establishment_id=ids[1])
    _post(app, "Sonda da inativa", author_type=WorkPostAuthorType.CLIENT, client_profile_id=ids[2])
    _post(app, "Sonda pública", author_type=WorkPostAuthorType.PROFESSIONAL, professional_id=catalog["professional"])

    posts = client.get(f"{SEARCH}?q=Sonda&type=post").get_json()["sections"]["posts"]
    assert [item["subtitle"] for item in posts] == ["Sonda pública"]

    discovery = str(client.get("/api/v1/discovery").get_json())
    assert "Sonda pública" in discovery
    for hidden in ("Sonda do rascunho", "Sonda do inativo", "Sonda da inativa"):
        assert hidden not in discovery

    page = client.get("/explorar?q=Sonda&tipo=publicacoes").get_data(as_text=True)
    assert "Sonda pública" in page and "Sonda do rascunho" not in page


# ------------------------------------------------------------------- API


def test_search_api_keeps_the_old_contract_and_adds_counts(app, client):
    _catalog(app)
    data = client.get(f"{SEARCH}?q=Graph").get_json()

    assert set(data) >= {"query", "location", "category", "items", "sections", "counts", "page"}
    assert data["page"] is None
    assert data["counts"]["experiences"] == 1
    assert data["counts"]["professionals"] == 1
    assert data["counts"]["establishments"] == 1
    assert data["counts"]["total"] == sum(
        data["counts"][key] for key in ("experiences", "professionals", "establishments", "posts")
    )
    assert data["sections"]["experiences"][0]["nextAvailableLabel"] is None


def test_search_api_pages_one_type(app, client):
    catalog = _catalog(app)
    for index in range(4):
        _service(app, catalog, f"Mechas Explorar {index}", "200.00")

    first = client.get(f"{SEARCH}?q=Mechas&type=experience&limit=3").get_json()
    assert len(first["sections"]["experiences"]) == 3
    assert first["sections"]["professionals"] == []  # só a contagem
    assert first["page"] == {"offset": 0, "limit": 3, "total": 4, "nextOffset": 3}

    second = client.get(f"{SEARCH}?q=Mechas&type=experience&limit=3&offset=3").get_json()
    assert len(second["sections"]["experiences"]) == 1
    assert second["page"]["nextOffset"] is None
    titles = {item["title"] for item in first["sections"]["experiences"] + second["sections"]["experiences"]}
    assert len(titles) == 4


def test_search_api_price_availability_and_sort(app, client):
    catalog = _catalog(app)
    _service(app, catalog, "Luzes Baratas", "90.00")
    _service(app, catalog, "Luzes Caras", "400.00", slot=True)

    def titles(params):
        data = client.get(f"{SEARCH}?q=Luzes&type=experience&{params}").get_json()
        return [item["title"] for item in data["sections"]["experiences"]]

    assert titles("priceMax=100") == ["Luzes Baratas"]
    assert titles("priceMin=100") == ["Luzes Caras"]
    assert titles("available=1") == ["Luzes Caras"]
    assert titles("sort=lowest_price") == ["Luzes Baratas", "Luzes Caras"]

    data = client.get(f"{SEARCH}?q=Luzes&type=experience&available=1").get_json()
    assert data["sections"]["experiences"][0]["nextAvailableLabel"]


def test_search_api_rejects_invalid_parameters(app, client):
    for params in ("type=senha", "priceMin=abc", "priceMax=-1", "sort=aleatorio", "offset=-2"):
        response = client.get(f"{SEARCH}?{params}")
        assert response.status_code == 400, params
        assert response.get_json()["error"]["code"] == "invalid_query_parameter"


# ------------------------------------------------------------------- Web


def _tab_counts(html):
    return dict(re.findall(r'>(Todos|Serviços|Profissionais|Estabelecimentos|Publicações) <span class="explore-tabs-nav__count">(\d+)</span>', html))


def test_explore_page_has_tabs_with_real_counts(app, client):
    catalog = _catalog(app)
    _post(app, "Graph em destaque", author_type=WorkPostAuthorType.PROFESSIONAL, professional_id=catalog["professional"])

    html = client.get("/explorar?q=Graph").get_data(as_text=True)
    assert _tab_counts(html) == {
        "Todos": "4", "Serviços": "1", "Profissionais": "1", "Estabelecimentos": "1", "Publicações": "1",
    }
    assert re.search(r'aria-current="page">Todos <span', html)
    assert 'href="/experiencias/corte-beauty-graph"' in html
    assert 'href="/profissionais/marina-graph"' in html
    assert 'href="/estabelecimentos/studio-graph"' in html
    assert re.search(r'href="/publicacoes/\d+"', html)
    # As abas carregam a busca atual.
    assert 'href="/explorar?q=Graph&amp;tipo=servicos"' in html

    tab = client.get("/explorar?q=Graph&tipo=profissionais").get_data(as_text=True)
    assert re.search(r'aria-current="page">Profissionais <span', tab)
    assert "Marina Graph" in tab and "Corte Beauty Graph" not in tab


def test_explore_filters_stay_in_the_address(app, client):
    catalog = _catalog(app)
    _service(app, catalog, "Escova Filtro", "80.00", slot=True)

    html = client.get("/explorar?q=Escova&tipo=servicos&preco_max=100&disponivel=1&ordem=lowest_price").get_data(as_text=True)
    assert "Escova Filtro" in html
    assert 'name="preco_max" type="number" inputmode="decimal" min="0" step="1" value="100"' in html
    assert re.search(r'name="disponivel" value="1"\s+checked', html)
    assert 'href="/explorar?q=Escova&amp;tipo=profissionais&amp;preco_max=100&amp;disponivel=1&amp;ordem=lowest_price"' in html
    assert "Limpar filtros" in html

    other = client.get("/explorar?q=Escova&tipo=profissionais&disponivel=1").get_data(as_text=True)
    assert "valem só para serviços" in other


def test_explore_zero_results_is_honest(app, client):
    _catalog(app)
    html = client.get("/explorar?q=Corte&local=Cidade Inexistente").get_data(as_text=True)
    assert "Nada encontrado com esta busca." in html
    assert 'href="/explorar?q=Corte"' in html  # Limpar filtros mantém a busca
    # Sugere só categorias que têm resultado real para "Corte".
    assert re.search(r'href="/explorar\?q=Corte&amp;categoria=cabelo">Cabelo <span>\d+</span>', html)
    assert "categoria=unhas" not in html


def test_logged_in_header_explore_goes_to_the_unified_page(app, client):
    from tests.test_section_edit import _login, _pro

    user_id, _ = _pro(app, email="explorador@example.com")
    _login(client, user_id)
    html = client.get("/favoritos").get_data(as_text=True)
    assert 'action="/explorar"' in html
    assert re.search(r'href="/explorar"[^>]*>\s*\S*\s*<svg|href="/explorar"', html)
    assert client.get("/explorar").status_code == 200
