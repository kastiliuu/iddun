"""V-05 (BUG-013) — "Esqueci minha senha" abaixo do campo de senha.

Como no app (mobile/src/app/login.tsx): o link vem depois do campo, para
que o Tab vá do e-mail para a senha, e não para o link.
"""


def test_forgot_link_comes_after_password_field(client):
    html = client.get("/login").get_data(as_text=True)

    password = html.index('id="password"')
    link = html.index('class="auth-forgot-link"')
    assert link > password
    assert 'href="/senha/esqueci"' in html[link - 80:link]
    assert "auth-label-row" not in html
