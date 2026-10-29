"""Editorial landing preserves real navigation, honest copy and accessible fallbacks."""


def test_editorial_landing_links_to_real_categories_and_signup(client):
    # D-HOME-04 a 07: as seções "Como funciona" e "Para quem é" saíram da
    # Home (aprovado em 29/10/2026); a explicação continua em /como-funciona.
    html = client.get("/").get_data(as_text=True)
    assert 'id="como-funciona"' not in html
    assert 'id="para-quem"' not in html
    assert 'href="/como-funciona"' in html
    assert 'href="/cadastro"' in html
    assert 'href="/login"' in html
    assert 'action="/experiencias"' in html
    assert "/experiencias?categoria=" in html


def test_mobile_navigation_is_progressive_and_motion_is_css_only(client):
    html = client.get("/").get_data(as_text=True)
    assert 'class="landing-mobile-menu"' in html
    assert '<summary aria-label="Abrir navegação">' in html
    assert "landing-motion.js" not in html
    assert "data-landing-orbit" not in html
    assert 'href="#"' not in html


def test_landing_does_not_invent_availability_or_verification(client):
    html = client.get("/").get_data(as_text=True)
    assert "Hoje, " not in html
    assert "Perfil verificado" not in html
    assert "Avaliações verificadas" not in html
    assert "não representa disponibilidade" not in html


def test_landing_nav_order_matches_page_order(client):
    html = client.get("/").get_data(as_text=True)
    nav = html.split('aria-label="Navegação da página inicial"')[1].split("</nav>")[0]
    assert nav.index("#profissionais") < nav.index("#estabelecimentos") < nav.index("#comunidade")
    assert html.index('id="profissionais"') < html.index('id="estabelecimentos"') < html.index('id="comunidade"')


def test_landing_invites_new_profiles_even_without_directory_data(client):
    html = client.get("/").get_data(as_text=True)
    assert "Seu perfil pode estar aqui" in html
    assert "Participe da comunidade" in html
    assert "Cadastrar meu estabelecimento" in html
