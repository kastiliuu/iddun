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
