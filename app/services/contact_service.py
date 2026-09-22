import re
from urllib.parse import quote

from flask_login import current_user

from app.extensions import db
from app.models.reputation import ContactClick


def normalize_whatsapp_number(value):
    digits = re.sub(r"\D", "", value or "")
    if not digits:
        return None
    if len(digits) in {10, 11}:
        digits = f"55{digits}"
    return digits


def whatsapp_url(phone, message):
    number = normalize_whatsapp_number(phone)
    if not number:
        return None
    return f"https://wa.me/{number}?text={quote(message)}"


def professional_whatsapp_url(profile):
    if not profile or not profile.whatsapp_enabled or not profile.phone:
        return None
    return whatsapp_url(
        profile.phone,
        f"Olá! Encontrei seu perfil no IDDUN e gostaria de saber mais sobre seus serviços, {profile.display_name}.",
    )


def establishment_whatsapp_url(establishment):
    if not establishment or not establishment.whatsapp_enabled or not establishment.phone:
        return None
    return whatsapp_url(
        establishment.phone,
        f"Olá! Encontrei {establishment.name} no IDDUN e gostaria de saber mais sobre os serviços.",
    )


def record_contact_click(*, professional=None, establishment=None, channel="whatsapp"):
    user_id = None
    try:
        if current_user.is_authenticated:
            user_id = current_user.id
    except RuntimeError:
        user_id = None

    click = ContactClick(
        user_id=user_id,
        professional=professional,
        establishment=establishment,
        channel=channel,
    )
    db.session.add(click)
    db.session.commit()
    return click
