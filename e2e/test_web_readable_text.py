"""V-04 (PR-3b) — texto legível nas telas Pro, Business e nos diretórios.

Mede no Chromium, em desktop e celular:
- nenhum texto abaixo de 12 px (--ds-type-caption, FE-DEC-013);
- nenhum texto fora de imagem abaixo do AA (4,5:1; 3:1 para texto grande);
- nenhuma rolagem horizontal.
"""

import pytest
from playwright.sync_api import Page

from e2e.seed_client import E2E_BUSINESS_SLUG, E2E_EMAIL, E2E_PRO_EMAIL
from e2e.test_web_platform_contrast import CONTRAST, _login, _reveal

SMALL_TEXT = """
() => [...document.querySelectorAll('h1,h2,h3,h4,p,span,strong,small,a,label,li,button,em,b,dt,dd,time')]
  .filter((el) => [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim()))
  .filter((el) => {
    const rect = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return rect.width > 0 && style.visibility !== 'hidden' && style.display !== 'none'
      && !el.closest('[hidden], [aria-hidden="true"], .site-header, .mobile-bottom-nav, footer, .media-cropper');
  })
  .map((el) => ({ text: el.innerText.trim().slice(0, 30), size: parseFloat(getComputedStyle(el).fontSize) }))
  .filter((item) => item.size < 12)
"""

PAGES = [
    (E2E_PRO_EMAIL, "/pro/painel"),
    (E2E_PRO_EMAIL, "/pro/perfil/editar"),
    (E2E_PRO_EMAIL, f"/business/{E2E_BUSINESS_SLUG}/painel"),
    (E2E_PRO_EMAIL, f"/business/{E2E_BUSINESS_SLUG}/editar"),
    (E2E_EMAIL, "/pro/comecar"),
    (E2E_EMAIL, "/pro/onboarding"),
    (E2E_EMAIL, "/business/onboarding"),
    (None, "/estabelecimentos"),
    (None, "/profissionais"),
]


@pytest.mark.parametrize("viewport", [(1440, 900), (390, 844)], ids=["desktop", "mobile"])
@pytest.mark.parametrize("email,path", PAGES, ids=[p[1] for p in PAGES])
def test_text_is_large_enough_and_readable(page: Page, viewport, email, path):
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    if email:
        _login(page, email)
    page.goto(path)
    _reveal(page)

    small = page.evaluate(SMALL_TEXT)
    assert small == [], f"{path}: {len(small)} textos abaixo de 12 px, ex.: {small[:5]}"

    failing = [
        item for item in page.evaluate(CONTRAST, None)
        if item["ratio"] < (3 if item["large"] else 4.5)
    ]
    assert failing == [], f"{path}: {len(failing)} textos abaixo do AA, ex.: {failing[:5]}"

    overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    assert overflow <= 0, f"{path}: rolagem horizontal de {overflow}px"
