"""Editorial landing preserves real navigation and accessible fallback."""

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


def test_mobile_navigation_and_motion_are_progressive(client):
    html = client.get("/").get_data(as_text=True)
    assert 'class="landing-mobile-menu"' in html
    assert '<summary aria-label="Abrir navegação">' in html
    assert 'data-landing-orbit' in html
    assert "landing-motion.js" in html
    assert "Arte de apresentação" in html
    assert 'href="#"' not in html
