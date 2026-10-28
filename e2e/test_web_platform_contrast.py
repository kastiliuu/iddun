"""PR-3 (BUG-014 / BUG-003) — legibilidade das telas Pro/Business.

Mede o contraste real no navegador (WCAG 2.x), em desktop e celular:
- os títulos e cartões apontados no dossiê atingem AA (4,5:1; 3:1 para
  texto grande);
- nenhuma tela Pro/Business tem texto quase invisível (abaixo de 2:1);
- o link "Voltar" fica numa linha própria, acima do rótulo da página.

Textos auxiliares de 8–11 px abaixo de AA são a PR-3b (registrada no Notion).
"""

import re

import pytest
from playwright.sync_api import Page, expect

from e2e.seed_client import E2E_BUSINESS_SLUG, E2E_EMAIL, E2E_PASSWORD, E2E_PRO_EMAIL

CONTRAST = """
(selector) => {
  const parse = (value) => {
    const match = value && value.match(/rgba?\\(([^)]+)\\)/);
    if (!match) return null;
    const parts = match[1].split(',').map(Number);
    return { r: parts[0], g: parts[1], b: parts[2], a: parts.length > 3 ? parts[3] : 1 };
  };
  const blend = (top, base) => ({
    r: top.r * top.a + base.r * (1 - top.a),
    g: top.g * top.a + base.g * (1 - top.a),
    b: top.b * top.a + base.b * (1 - top.a),
    a: 1,
  });
  const luminance = ({ r, g, b }) => {
    const channel = (c) => {
      c /= 255;
      return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
    };
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
  };
  // Effective background: stacked colours up to the first opaque layer;
  // a gradient counts by its last opaque stop (all gradients here are dark).
  const background = (element) => {
    const layers = [];
    for (let node = element; node; node = node.parentElement) {
      const style = getComputedStyle(node);
      if (/gradient/.test(style.backgroundImage)) {
        const stops = [...style.backgroundImage.matchAll(/rgba?\\([^)]+\\)/g)]
          .map((m) => parse(m[0]))
          .filter((c) => c.a > 0.5);
        if (stops.length) { layers.push(stops[stops.length - 1]); break; }
      }
      const colour = parse(style.backgroundColor);
      if (colour && colour.a > 0) {
        layers.push(colour);
        if (colour.a >= 1) break;
      }
    }
    let base = { r: 255, g: 255, b: 255, a: 1 };
    for (let i = layers.length - 1; i >= 0; i -= 1) base = blend(layers[i], base);
    return base;
  };
  const measure = (element) => {
    const style = getComputedStyle(element);
    const back = background(element);
    const text = parse(style.color);
    const front = blend({ ...text, a: text.a * Number(style.opacity) }, back);
    const [light, dark] = [luminance(front), luminance(back)].sort((a, b) => b - a);
    const size = parseFloat(style.fontSize);
    const bold = Number(style.fontWeight) >= 700;
    return {
      text: element.innerText.trim().slice(0, 40),
      ratio: (light + 0.05) / (dark + 0.05),
      large: size >= 24 || (size >= 18.66 && bold),
      hasImage: element.classList.contains('has-image'),
    };
  };
  const visible = (element) => {
    const rect = element.getBoundingClientRect();
    const style = getComputedStyle(element);
    return rect.width > 0 && style.visibility !== 'hidden' && style.display !== 'none'
      && !element.closest('[hidden], [aria-hidden="true"], .site-header, .mobile-bottom-nav, footer, .media-cropper');
  };
  const ownText = (element) => [...element.childNodes]
    .some((node) => node.nodeType === 3 && node.textContent.trim());
  const pool = selector
    ? [...document.querySelectorAll(selector)]
    : [...document.querySelectorAll('h1,h2,h3,h4,p,span,strong,small,a,label,li,button,em')].filter(ownText);
  return pool.filter(visible).map(measure).filter((item) => !item.hasImage);
}
"""

PAGES = [
    (E2E_EMAIL, "/pro/comecar", [".platform-entry__head h1", ".platform-mode-card__content strong", ".platform-mode-card__content small"]),
    (E2E_EMAIL, "/pro/onboarding", [".platform-onboarding__aside h1"]),
    (E2E_EMAIL, "/business/onboarding", [".platform-onboarding__aside h1"]),
    (E2E_PRO_EMAIL, "/pro/perfil/editar", [".platform-editor__head h1"]),
    (E2E_PRO_EMAIL, f"/business/{E2E_BUSINESS_SLUG}/painel", [".business-catalog__details span", ".business-catalog__value a", ".platform-panel .btn-outline"]),
]

BACK_LINK_PAGES = [
    (E2E_EMAIL, "/business/onboarding"),
    (E2E_PRO_EMAIL, "/pro/perfil/editar"),
]


def _login(page: Page, email: str):
    page.goto("/login")
    page.locator('input[name="email"]').fill(email)
    page.locator('input[name="password"]').fill(E2E_PASSWORD)
    page.locator('button[type="submit"][data-submit]').click()
    expect(page).to_have_url(re.compile(r"/feed(?:\?.*)?$"))


def _reveal(page: Page):
    page.evaluate(
        "() => document.querySelectorAll('[data-reveal],[data-reveal-stagger]')"
        ".forEach((el) => el.classList.add('is-visible'))"
    )
    page.wait_for_timeout(700)


@pytest.mark.parametrize("viewport", [(1440, 900), (390, 844)], ids=["desktop", "mobile"])
@pytest.mark.parametrize("email,path,targets", PAGES, ids=[p[1] for p in PAGES])
def test_platform_texts_meet_contrast(page: Page, viewport, email, path, targets):
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    _login(page, email)
    page.goto(path)
    _reveal(page)

    for selector in targets:
        measured = page.evaluate(CONTRAST, selector)
        assert measured, f"{path}: nada encontrado para {selector}"
        for item in measured:
            needed = 3 if item["large"] else 4.5
            assert item["ratio"] >= needed, f"{path} {selector} {item}"

    invisible = [item for item in page.evaluate(CONTRAST, None) if item["ratio"] < 2]
    assert invisible == [], f"{path}: texto quase invisível {invisible[:5]}"


@pytest.mark.parametrize("email,path", BACK_LINK_PAGES, ids=[p[1] for p in BACK_LINK_PAGES])
def test_back_link_sits_on_its_own_line(page: Page, email, path):
    _login(page, email)
    page.goto(path)

    back = page.locator(".platform-back-link").first.bounding_box()
    kicker = page.locator(".platform-back-link + .platform-kicker").first.bounding_box()
    assert back and kicker
    assert kicker["y"] >= back["y"] + back["height"]
