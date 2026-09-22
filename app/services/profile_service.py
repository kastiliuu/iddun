from app.extensions import db
from app.models.profile import ClientProfile
from app.models.user import User


def ensure_client_profile(user: User) -> ClientProfile:
    """Return the user's client profile, creating it when necessary.

    This keeps old users created before ClientProfile existed compatible with the
    new model without requiring a data backfill migration for local development.
    """
    if user.client_profile is not None:
        return user.client_profile

    profile = ClientProfile(user=user)
    db.session.add(profile)
    db.session.commit()
    return profile
