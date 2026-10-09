"""Hardening regression coverage for the IDDUN Pro V1 shell."""

from app.extensions import db
from app.models.professional import ProfessionalProfile
from app.models.user import User, UserRole


PRO_ROUTES = (
    "/pro/painel",
    "/pro/clientes",
    "/pro/insights",
    "/pro/jornada",
)


def _professional(app):
    with app.app_context():
        user = User(
            name="Pro Hardening",
            email="pro-hardening@example.com",
            role=UserRole.PROFESSIONAL,
        )
        user.set_password("senha-forte-123")

        profile = ProfessionalProfile(
            user=user,
            display_name="Pro Hardening",
            slug="pro-hardening",
            primary_specialty="Nail Designer",
            bio=(
                "Perfil profissional válido para validar "
                "o shell final do IDDUN Pro."
            ),
            city="Curitiba",
            state="PR",
            timezone="America/Sao_Paulo",
            onboarding_completed=True,
            is_active=True,
        )

        db.session.add_all(
            [user, profile]
        )
        db.session.commit()

        return user.id


def _login(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


def _mobile_nav(html):
    start = html.index(
        '<nav class="pro-mobile-nav"'
    )
    end = html.index(
        "</nav>",
        start,
    )
    return html[
        start:end
    ]


def test_all_pro_v1_routes_require_authentication(client):
    for route in PRO_ROUTES:
        response = client.get(
            route,
            follow_redirects=False,
        )

        assert response.status_code == 302


def test_pro_v1_routes_share_accessible_five_item_mobile_navigation(
    app,
    client,
):
    user_id = _professional(app)
    _login(client, user_id)

    for route in PRO_ROUTES:
        response = client.get(route)

        assert response.status_code == 200

        html = response.get_data(
            as_text=True
        )
        nav = _mobile_nav(html)

        assert (
            'aria-label="Navegação principal '
            'do IDDUN Pro"'
            in nav
        )
        assert nav.count("<a") == 5
        assert (
            'aria-current="page"'
            in nav
        )

        assert ">Hoje</span>" in nav
        assert ">Agenda</span>" in nav
        assert ">Clientes</span>" in nav
        assert ">Insights</span>" in nav
        assert ">Jornada</span>" in nav


def test_pro_v1_shell_has_skip_navigation_and_main_focus_target(
    app,
    client,
):
    user_id = _professional(app)
    _login(client, user_id)

    html = client.get(
        "/pro/painel"
    ).get_data(as_text=True)

    assert (
        'class="skip-link" '
        'href="#main-content"'
        in html
    )
    assert (
        'id="main-content" '
        'tabindex="-1"'
        in html
    )


def test_each_pro_v1_screen_marks_current_mobile_destination(
    app,
    client,
):
    user_id = _professional(app)
    _login(client, user_id)

    expected = {
        "/pro/painel":
            "professional.dashboard",
        "/pro/clientes":
            "professional.clients",
        "/pro/insights":
            "professional.insights",
        "/pro/jornada":
            "professional.schedule",
    }

    for route in expected:
        html = client.get(
            route
        ).get_data(as_text=True)
        nav = _mobile_nav(html)

        active_anchor = nav.split(
            'aria-current="page"',
            1,
        )[0].rsplit(
            "<a",
            1,
        )[-1]

        assert (
            'class="is-active"'
            in active_anchor
        )
