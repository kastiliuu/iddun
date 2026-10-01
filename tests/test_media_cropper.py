from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_shared_cropper_assets_expose_accessible_drag_contract():
    javascript = _read("app/static/js/media-cropper.js")
    stylesheet = _read("app/static/css/media-cropper.css")

    for contract in (
        "[data-media-cropper]",
        "[data-crop-stage]",
        "pointerdown",
        "pointermove",
        "pointerup",
        "pointercancel",
        "keydown",
        "ArrowLeft",
        "event.shiftKey",
        "aria-valuetext",
        "URL.revokeObjectURL",
    ):
        assert contract in javascript

    for contract in (
        ".media-cropper__stage",
        "touch-action: none",
        ".media-cropper__stage:focus-visible",
        ".media-cropper__reset:focus-visible",
        ".media-cropper--dark",
        "@media (max-width: 760px)",
        "prefers-reduced-motion: reduce",
    ):
        assert contract in stylesheet


def test_platform_profile_templates_load_shared_cropper_once():
    template_paths = (
        "app/templates/platform/professional-onboarding.html",
        "app/templates/platform/professional-edit.html",
        "app/templates/platform/business-onboarding.html",
        "app/templates/platform/business-edit.html",
    )

    for template_path in template_paths:
        template = _read(template_path)

        assert (
            "{% from 'components/media-upload.html' import "
            "media_upload, multi_upload %}"
        ) in template
        assert template.count("css/media-cropper.css") == 1
        assert template.count("js/media-cropper.js") == 1
        assert "media_upload(" in template


def test_platform_media_upload_macro_wires_focus_and_accessibility():
    template = _read("app/templates/components/media-upload.html")

    for contract in (
        "data-media-control",
        "data-media-cropper",
        'data-crop-input-id="{{ field.id }}"',
        'data-focus-x-id="{{ focus_x.id }}"',
        'data-focus-y-id="{{ focus_y.id }}"',
        "data-crop-stage",
        'tabindex="0"',
        'aria-label="Ajustar enquadramento de {{ field.label.text }}"',
        "data-crop-reset",
        "data-crop-output",
        'aria-live="polite"',
        'draggable="false"',
    ):
        assert contract in template


def test_admin_uses_shared_cropper_instead_of_a_parallel_editor():
    layout = _read("app/templates/admin/layout.html")
    macros = _read("app/templates/admin/_form_macros.html")

    assert layout.count("css/media-cropper.css") == 1
    assert layout.count("js/media-cropper.js") == 1

    for contract in (
        "media-cropper--dark",
        "data-media-cropper",
        'data-crop-input-id="{{ field.id }}"',
        'data-focus-x-id="{{ focus_x_field.id }}"',
        'data-focus-y-id="{{ focus_y_field.id }}"',
        "data-crop-stage",
        'tabindex="0"',
        "data-crop-reset",
        "data-crop-output",
    ):
        assert contract in macros


def test_legacy_cropper_implementations_do_not_return():
    checks = {
        "app/static/js/platform.js": ("data-focus-range",),
        "app/static/css/platform.css": ("platform-focus-control",),
        "app/static/js/admin.js": ("data-crop-editor", "admin-crop"),
        "app/static/css/admin.css": (".admin-crop-",),
        "app/templates/admin/_form_macros.html": ("data-crop-editor",),
    }

    for relative_path, forbidden_contracts in checks.items():
        source = _read(relative_path)

        for forbidden_contract in forbidden_contracts:
            assert forbidden_contract not in source