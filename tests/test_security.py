def test_security_headers_are_present(client):
    response = client.get("/")

    assert (
        response.headers[
            "X-Content-Type-Options"
        ]
        == "nosniff"
    )
    assert (
        response.headers[
            "X-Frame-Options"
        ]
        == "DENY"
    )
    assert (
        response.headers[
            "Referrer-Policy"
        ]
        == "strict-origin-when-cross-origin"
    )
    assert (
        "frame-ancestors 'none'"
        in response.headers[
            "Content-Security-Policy"
        ]
    )


def test_api_login_rate_limit_returns_json(
    app,
    client,
):
    app.config[
        "RATELIMIT_ENABLED"
    ] = True

    payload = {
        "email": "nobody@example.com",
        "password": "senha-invalida",
    }

    responses = [
        client.post(
            "/api/auth/login",
            json=payload,
        )
        for _ in range(11)
    ]

    assert responses[-1].status_code == 429

    body = responses[-1].get_json()

    assert (
        body["error"]["code"]
        == "rate_limit_exceeded"
    )


def test_rate_limit_headers_are_enabled(
    client,
):
    response = client.post(
        "/api/auth/login",
        json={
            "email": "nobody@example.com",
            "password": "senha-invalida",
        },
    )

    assert "X-RateLimit-Limit" in response.headers
    assert (
        "X-RateLimit-Remaining"
        in response.headers
    )



def test_request_id_is_generated(
    client,
):
    response = client.get("/health")

    request_id = response.headers.get(
        "X-Request-ID"
    )

    assert request_id
    assert len(request_id) == 32


def test_safe_request_id_is_preserved(
    client,
):
    response = client.get(
        "/health",
        headers={
            "X-Request-ID": "mobile-request-123",
        },
    )

    assert (
        response.headers["X-Request-ID"]
        == "mobile-request-123"
    )


def test_unsafe_request_id_is_replaced(
    client,
):
    response = client.get(
        "/health",
        headers={
            "X-Request-ID": (
                "bad request id with spaces"
            ),
        },
    )

    assert (
        response.headers["X-Request-ID"]
        != "bad request id with spaces"
    )


# PR-1 (BUG-016): the policy is pinned directive by directive. The only
# change allowed was ``blob:`` in ``img-src`` -- for the browser preview and
# crop of a file the user picked. Nothing else may widen.
EXPECTED_CSP = {
    "default-src": ["'self'"],
    "base-uri": ["'self'"],
    "form-action": ["'self'"],
    "frame-ancestors": ["'none'"],
    "img-src": ["'self'", "data:", "blob:", "https:"],
    "font-src": ["'self'", "data:", "https://fonts.gstatic.com"],
    "style-src": ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
    "script-src": ["'self'"],
    "connect-src": ["'self'"],
}


def _csp_directives(header):
    directives = {}
    for part in header.split(";"):
        tokens = part.split()
        if tokens:
            directives[tokens[0]] = tokens[1:]
    return directives


def test_content_security_policy_is_pinned(client):
    for path in ("/", "/login", "/api/v1/experiences"):
        header = client.get(path).headers["Content-Security-Policy"]
        assert _csp_directives(header) == EXPECTED_CSP, path


def test_blob_is_allowed_only_for_images(client):
    directives = _csp_directives(client.get("/").headers["Content-Security-Policy"])

    for name, sources in directives.items():
        if name == "img-src":
            assert "blob:" in sources
        else:
            assert "blob:" not in sources, name

    # No directive that would let blob:/workers/objects run code is declared,
    # so they all fall back to default-src 'self'.
    for name in ("worker-src", "child-src", "object-src", "frame-src", "media-src"):
        assert name not in directives
    assert "'unsafe-eval'" not in " ".join(sum(directives.values(), []))


def test_scripts_reject_unsafe_inline(client):
    """NV-06: executable inline handlers and source schemes must be prohibited."""
    for path in ("/", "/login", "/api/v1/experiences"):
        policy = _csp_directives(client.get(path).headers["Content-Security-Policy"])
        assert policy["script-src"] == ["'self'"]
        assert all(
            source not in policy["script-src"]
            for source in ("'unsafe-inline'", "'unsafe-eval'", "data:", "blob:")
        )


def test_inline_event_handlers_are_not_in_app_templates():
    """Regression guard: all template event attributes would bypass strict CSP."""
    from pathlib import Path
    import re

    templates = Path(__file__).resolve().parents[1] / "app" / "templates"
    offenders = [
        f"{path.relative_to(templates)}: {match.group(0)}"
        for path in templates.rglob("*.html")
        for match in re.finditer(
            r"\son(?:click|change|submit|input|error|load|keydown|keyup|focus|blur)\s*=",
            path.read_text(encoding="utf-8"),
            flags=re.IGNORECASE,
        )
    ]
    assert offenders == []
