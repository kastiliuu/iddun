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
        "DataTransfer",
        "canvas.toBlob",
        "data-crop-zoom",
        "pointerId",
        "pinchState",
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
        ".media-cropper__viewport--avatar",
        ".media-cropper__viewport--cover",
        ".media-cropper__zoom",
        "accent-color: var(--color-plum)",
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
        "data-crop-zoom",
        'data-crop-kind="{{ kind }}"',
        'data-crop-aspect="{{ crop_aspect }}"',
        "media-cropper__viewport--{{ kind }}",
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

def test_professional_edit_shows_validation_summary():
    template = _read("app/templates/platform/professional-edit.html")
    assert "{% if form.errors %}" in template
    assert 'role="alert"' in template
    assert "Não foi possível salvar o perfil" in template
    assert "form.errors.items()" in template


def test_mobile_transport_diagnostics_do_not_log_credentials_or_file_uri():
    client = _read("mobile/src/api/client.ts")
    assert '"[IDDUN API] Transport failure"' in client
    diagnostic = client.split('"[IDDUN API] Transport failure"', 1)[1].split("});", 1)[0]
    assert "isMultipart: isFormData" in diagnostic
    assert "errorMessage:" in diagnostic
    assert "Authorization" not in diagnostic
    assert "token" not in diagnostic
    assert "body" not in diagnostic
    assert "uri" not in diagnostic


def test_mobile_media_upload_uses_real_blob_for_expo_fetch():
    media = _read("mobile/src/api/media.ts")
    assert "await fileResponse.blob()" in media
    assert 'form.append("file", blob, image.name)' in media
    assert "as unknown as Blob" not in media
    assert "await imageFormData(image" in media
    for endpoint in ("avatar", "cover", "portfolio"):
        assert f'/api/v1/media/professional/{endpoint}' in media


def test_mobile_post_upload_reuses_real_blob_multipart_builder():
    feed = _read("mobile/src/api/feed.ts")
    media = _read("mobile/src/api/media.ts")
    assert "export async function imageFormData(" in media
    assert "await imageFormData(payload.image)" in feed
    assert "await imageFormData(image, {focusX, focusY})" in feed
    assert "await postFormData(payload)" in feed
    assert "as unknown as Blob" not in feed
    assert '"/api/v1/posts"' in feed
    assert "/image" in feed


def test_ds06_cropper_generates_real_profile_derivative_before_submit():
    javascript = _read("app/static/js/media-cropper.js")
    template = _read("app/templates/components/media-upload.html")

    for contract in (
        "cropRect",
        "replaceInputWithCrop",
        "drawImage(",
        "new File(",
        "transfer.items.add(file)",
        "input.files = transfer.files",
        "'image/jpeg', 0.9",
        "focusX.value = '50'",
        "focusY.value = '50'",
    ):
        assert contract in javascript

    assert "A área visível é exatamente o que será usado" in template
    assert "gesto de pinça" in template
    assert "type=\"range\"" in template
    assert "min=\"1\"" in template
    assert "max=\"3\"" in template
