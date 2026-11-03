"""CSRF para APIs JSON quando a sessão vem do cookie da Web (AUD-04, D-SOC-01).

As rotas das APIs ficam fora da proteção padrão porque o app usa Bearer e
não tem cookie. Algumas, porém, também aceitam a sessão da Web. Nesse caso
a mutação exige o mesmo token CSRF dos formulários (cabeçalho X-CSRFToken);
com Bearer nada muda.
"""

from flask import current_app, request
from flask_login import current_user

from app.extensions import csrf


def protect_cookie_mutation():
    """before_request dos blueprints que aceitam sessão por cookie."""
    if not current_app.config.get("WTF_CSRF_ENABLED", True):
        return None
    if request.method not in current_app.config.get(
        "WTF_CSRF_METHODS", ("POST", "PUT", "PATCH", "DELETE")
    ):
        return None
    if request.headers.get("Authorization") is not None:
        return None
    if not current_user.is_authenticated:
        return None
    csrf.protect()
    return None
