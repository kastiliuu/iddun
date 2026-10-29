"""V-05 (BUG-013) — "Esqueci minha senha" no login, como no app.

Abaixo do campo de senha, alinhado à direita, com área de toque de 44 px;
o Tab vai do e-mail para a senha antes de chegar ao link.
"""

import pytest
from playwright.sync_api import Page

ACTIVE = "document.activeElement.id || document.activeElement.textContent.trim()"


@pytest.mark.parametrize("viewport", [(1440, 900), (390, 844)], ids=["desktop", "mobile"])
def test_forgot_link_sits_below_password_in_tab_order(page: Page, viewport):
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    page.goto("/login")

    page.locator("#email").focus()
    order = []
    for _ in range(4):
        page.keyboard.press("Tab")
        order.append(page.evaluate(ACTIVE))
    assert order == ["password", "Mostrar", "Esqueci minha senha", "remember"]

    field = page.locator(".auth-password-shell").bounding_box()
    link = page.locator(".auth-forgot-link").bounding_box()
    assert link["height"] >= 44
    assert link["y"] >= field["y"] + field["height"]
    # Alinhado à direita do campo, como no app.
    assert abs((link["x"] + link["width"]) - (field["x"] + field["width"])) <= 2
