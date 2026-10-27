"""PR-1 (BUG-016 / BUG-001): image preview and crop under the real CSP.

The policy allows ``blob:`` only in ``img-src``. These journeys prove both
sides in a real browser:
- the preview and crop of a picked JPEG work on Pro and Business screens,
  with no CSP violation;
- a ``blob:`` script is still refused by ``script-src 'self'``;
- an SVG picked by bypassing ``accept`` is never turned into a preview.
"""

import io
import re

import pytest
from PIL import Image
from playwright.sync_api import Page, expect

from e2e.seed_client import E2E_EMAIL, E2E_PASSWORD, E2E_PRO_EMAIL

# Collects every CSP violation the page reports, from the first script on.
CSP_RECORDER = """
window.__cspViolations = [];
document.addEventListener('securitypolicyviolation', (event) => {
  window.__cspViolations.push({
    directive: event.effectiveDirective || event.violatedDirective,
    blocked: event.blockedURI,
  });
});
"""


@pytest.fixture()
def jpeg_file(tmp_path):
    path = tmp_path / "foto-qa.jpg"
    image = Image.new("RGB", (640, 480), (107, 46, 255))
    for x in range(0, 640, 40):
        for y in range(0, 480, 40):
            if (x + y) % 80 == 0:
                image.paste((26, 15, 46), (x, y, x + 40, y + 40))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    path.write_bytes(buffer.getvalue())
    return path


@pytest.fixture()
def svg_file(tmp_path):
    path = tmp_path / "logo.svg"
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8">'
        "<script>window.__svgRan = 1</script><rect width='8' height='8'/></svg>"
    )
    return path


def _login(page: Page, email: str):
    page.add_init_script(CSP_RECORDER)
    page.goto("/login")
    page.locator('input[name="email"]').fill(email)
    page.locator('input[name="password"]').fill(E2E_PASSWORD)
    page.locator('button[type="submit"][data-submit]').click()
    expect(page).to_have_url(re.compile(r"/feed(?:\?.*)?$"))


def _image_violations(page: Page):
    return [
        item
        for item in page.evaluate("window.__cspViolations")
        if item["directive"] == "img-src"
    ]


def _assert_preview_and_crop(page: Page, input_id: str, file_path):
    page.set_input_files(f"#{input_id}", str(file_path))

    cropper = page.locator(
        f'[data-media-cropper][data-crop-input-id="{input_id}"]'
    )
    expect(cropper).to_have_class(re.compile(r"\bis-open\b"))

    image = cropper.locator("[data-crop-image]")
    page.wait_for_function(
        "(img) => img.complete && img.naturalWidth > 0",
        arg=image.element_handle(),
        timeout=10_000,
    )
    assert image.get_attribute("src").startswith("blob:")

    cropper.locator("[data-crop-confirm]").click()
    expect(cropper).not_to_have_class(re.compile(r"\bis-open\b"))

    # The submitted file is the real crop generated in the browser.
    cropped_name = page.eval_on_selector(
        f"#{input_id}", "(input) => input.files[0] && input.files[0].name"
    )
    assert cropped_name and cropped_name.endswith("-crop.jpg")

    preview = page.locator(
        f'[data-media-control]:has(#{input_id}) [data-image-preview]'
    )
    assert "blob:" in preview.evaluate("(el) => el.style.backgroundImage")
    assert _image_violations(page) == []


def test_blob_script_is_still_blocked_but_blob_image_loads(page: Page):
    page.add_init_script(CSP_RECORDER)
    page.goto("/login")

    result = page.evaluate(
        """async () => {
          const script = document.createElement('script');
          script.src = URL.createObjectURL(
            new Blob(['window.__blobScriptRan = true;'], { type: 'text/javascript' })
          );
          const scriptOutcome = new Promise((resolve) => {
            script.onload = () => resolve('loaded');
            script.onerror = () => resolve('blocked');
          });
          document.head.appendChild(script);

          const canvas = document.createElement('canvas');
          canvas.width = 4;
          canvas.height = 4;
          canvas.getContext('2d').fillRect(0, 0, 4, 4);
          const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
          const image = new Image();
          const imageOutcome = new Promise((resolve) => {
            image.onload = () => resolve(image.naturalWidth);
            image.onerror = () => resolve(0);
          });
          image.src = URL.createObjectURL(blob);

          return {
            script: await scriptOutcome,
            ran: window.__blobScriptRan === true,
            imageWidth: await imageOutcome,
          };
        }"""
    )

    assert result == {"script": "blocked", "ran": False, "imageWidth": 4}
    directives = {item["directive"] for item in page.evaluate("window.__cspViolations")}
    assert "script-src-elem" in directives or "script-src" in directives
    assert "img-src" not in directives


def test_pro_profile_edit_preview_and_crop(page: Page, jpeg_file):
    _login(page, E2E_PRO_EMAIL)
    page.goto("/pro/perfil/editar")

    _assert_preview_and_crop(page, "avatar_file", jpeg_file)
    _assert_preview_and_crop(page, "cover_file", jpeg_file)


def test_business_onboarding_preview_and_crop(page: Page, jpeg_file):
    _login(page, E2E_EMAIL)
    page.goto("/business/onboarding")

    _assert_preview_and_crop(page, "logo_file", jpeg_file)
    _assert_preview_and_crop(page, "cover_file", jpeg_file)


def test_svg_is_never_previewed(page: Page, svg_file):
    _login(page, E2E_PRO_EMAIL)
    page.goto("/pro/perfil/editar")

    page.set_input_files("#avatar_file", str(svg_file))
    page.wait_for_timeout(300)

    cropper = page.locator('[data-media-cropper][data-crop-input-id="avatar_file"]')
    expect(cropper).not_to_have_class(re.compile(r"\bis-open\b"))
    src = cropper.locator("[data-crop-image]").get_attribute("src") or ""
    assert not src.startswith("blob:")
    assert page.evaluate("window.__svgRan") is None
