"""QA-003: visual catalog contract without changing service operations."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "app/templates/platform/professional-services.html"
EDITOR = ROOT / "app/templates/platform/professional-service-form.html"
CSS = ROOT / "app/static/css/pro-service-catalog.css"
MOBILE_LIST = ROOT / "mobile/src/app/manage-services.tsx"
MOBILE_EDITOR = ROOT / "mobile/src/app/create-service.tsx"


def test_catalog_preserves_all_mutating_actions_and_csrf():
    content = CATALOG.read_text(encoding="utf-8")
    assert 'data-iddun-surface="light"' in content
    assert "pro-catalog-service" in content
    for endpoint in (
        "professional.create_service_slot",
        "professional.create_service_slots_from_schedule",
        "professional.create_service_slots_batch",
        "professional.block_service_slot",
        "professional.reopen_service_slot",
        "professional.publish_service",
        "professional.pause_service",
    ):
        assert endpoint in content
    assert content.count('name="csrf_token"') >= 7


def test_service_editor_preserves_fields_errors_and_submit():
    content = EDITOR.read_text(encoding="utf-8")
    assert 'data-iddun-surface="light"' in content
    assert "pro-service-form-section" in content
    assert "form.hidden_tag()" in content
    assert "field_errors(field)" in content
    for key in (
        "form.image_file", "form.title", "form.category",
        "form.establishment_id", "form.short_description",
        "form.description", "form.regular_price", "form.price",
        "form.duration_minutes",
    ):
        assert key in content


def test_scoped_styles_use_tokens_and_have_mobile_rules():
    content = CSS.read_text(encoding="utf-8")
    assert ".pro-catalog-service" in content
    assert ".pro-service-form-section" in content
    assert "@media (max-width: 640px)" in content
    assert "prefers-reduced-motion" in content
    assert "var(--ds-" in content
    import re
    assert not re.search(r"#[0-9a-fA-F]{3,8}\\b", content)


def test_expo_catalog_and_editor_still_call_real_service_api():
    listing = MOBILE_LIST.read_text(encoding="utf-8")
    editor = MOBILE_EDITOR.read_text(encoding="utf-8")
    assert "getManagedServices()" in listing
    assert "changeProfessionalServiceStatus(" in listing
    assert "router.push(\"/create-service\")" in listing
    assert "styles.card" in listing
    assert "createProfessionalServiceDraft(payload)" in editor
    assert "updateProfessionalServiceDraft(serviceId, payload)" in editor
    assert "styles.section" in editor
