"""Base of every Web form: default validation messages in Portuguese.

BUG-017: WTForms answered "This field is required." and other English
defaults because no translation was configured. The catalogue bundled with
WTForms (``wtforms/locale/pt``) is used -- no new dependency -- and a few
messages are rewritten to say what to do, in the same words as the client-side
validation of the onboarding wizards (static/js/platform.js).
"""

from flask_wtf import FlaskForm
from wtforms.i18n import get_translations

_CATALOGUE = get_translations(["pt_BR", "pt"])

_OVERRIDES = {
    "This field is required.": "Preencha este campo.",
    "Invalid email address.": "Informe um e-mail válido.",
    "Field must be at least %(min)d character long.": "Use pelo menos %(min)d caractere.",
    "Field must be at least %(min)d characters long.": "Use pelo menos %(min)d caracteres.",
    "Field cannot be longer than %(max)d character.": "Use no máximo %(max)d caractere.",
    "Field cannot be longer than %(max)d characters.": "Use no máximo %(max)d caracteres.",
    "Field must be between %(min)d and %(max)d characters long.": (
        "Use entre %(min)d e %(max)d caracteres."
    ),
}


class _PortugueseMessages:
    def gettext(self, string):
        return _OVERRIDES.get(string) or _CATALOGUE.gettext(string)

    def ngettext(self, singular, plural, n):
        chosen = singular if n == 1 else plural
        return _OVERRIDES.get(chosen) or _CATALOGUE.ngettext(singular, plural, n)


PORTUGUESE_MESSAGES = _PortugueseMessages()


class IddunForm(FlaskForm):
    class Meta:
        def get_translations(self, form):
            return PORTUGUESE_MESSAGES

        def render_field(self, field, render_kw):
            # V-02a: um campo com erro é anunciado como inválido e aponta
            # para a mensagem do macro field_errors (id "<campo>-errors").
            if field.errors:
                render_kw = dict(render_kw)
                render_kw["aria-invalid"] = "true"
                described = render_kw.get("aria-describedby", "").split()
                error_id = f"{field.id}-errors"
                if error_id not in described:
                    described.append(error_id)
                render_kw["aria-describedby"] = " ".join(described)
            return super().render_field(field, render_kw)
