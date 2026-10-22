"""Public landing contracts: real counts, clear entry and legal links."""

from pathlib import Path

HOME = (Path(__file__).resolve().parents[1] / "app/templates/public/home.html").read_text(encoding="utf-8")


def test_landing_exposes_login_and_registration():
    assert "url_for('auth.login')" in HOME
    assert "url_for('auth.register')" in HOME
    assert "Faça parte do IDDUN" in HOME


def test_landing_displays_real_public_community_data():
    assert "home_stats.members" in HOME
    assert "home_stats.professionals" in HOME
    assert "home_stats.establishments" in HOME
    assert "for professional in professionals[:3]" in HOME
    assert "for studio in studios[:3]" in HOME


def test_landing_includes_existing_legal_and_support_destinations():
    assert "url_for('public.privacy_policy')" in HOME
    assert "url_for('public.terms_of_use')" in HOME
    assert "mailto:contato@iddun.com.br" in HOME


def test_landing_has_no_authenticated_bottom_bar():
    assert "{% block mobile_bottom_nav %}{% endblock %}" in HOME
