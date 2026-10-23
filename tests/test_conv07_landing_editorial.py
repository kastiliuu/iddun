"""Editorial landing preserves real navigation, honest copy and accessible fallbacks."""


def test_editorial_landing_links_to_real_categories_and_signup(client):
    html = client.get("/").get_data(as_text=True)
    assert 'id="como-funciona"' in html
    assert 'id="para-quem"' in html
    assert "Descubra trabalhos reais" in html
    assert "Siga e salve quem inspira" in html
    assert "Reserve com horários reais" in html
    assert 'href="/cadastro"' in html
    assert 'href="/login"' in html
    assert 'name="q"' not in html
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
    assert nav.index("#como-funciona") < nav.index("#para-quem") < nav.index("#comunidade")


def test_landing_invites_new_profiles_even_without_directory_data(client):
    html = client.get("/").get_data(as_text=True)
    assert "Seu perfil pode estar aqui" in html
    assert "Participe da comunidade" in html
    assert "Cadastrar meu estabelecimento" in html
