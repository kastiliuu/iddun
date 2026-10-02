"""Privacidade e anonymização irreversível de contas."""

import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import delete, update

from app.extensions import db
from app.models.account_token import AccountToken
from app.models.api_session import ApiSession
from app.models.booking import (
    BookingStatus,
    SlotStatus,
)
from app.models.establishment import (
    EstablishmentAccessRole,
    EstablishmentAccessStatus,
    EstablishmentUserAccess,
)
from app.models.experience import ExperienceStatus
from app.models.reputation import ContactClick
from app.models.user import UserRole
from app.services.media_service import (
    delete_uploaded_files,
)


class AccountDeletionBlocked(
    ValueError
):
    def __init__(
        self,
        establishments,
    ):
        self.establishments = tuple(
            establishments
        )
        super().__init__(
            (
                "Transfira a titularidade dos "
                "estabelecimentos antes de "
                "excluir sua conta."
            )
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AccountDeletionResult:
    removed_media: int
    queued_media: int


def _as_utc(value):
    if value.tzinfo is None:
        return value.replace(
            tzinfo=timezone.utc
        )

    return value.astimezone(
        timezone.utc
    )


def _now(value=None):
    return _as_utc(
        value
        or datetime.now(
            timezone.utc
        )
    )


def account_deletion_blockers(
    user,
):
    return [
        access.establishment.name
        for access in (
            user.establishment_accesses
        )
        if (
            access.status
            == EstablishmentAccessStatus.ACTIVE
            and access.role
            == EstablishmentAccessRole.OWNER
            and access.establishment
            is not None
            and access.establishment.is_active
        )
    ]


def _collect_professional_media(
    professional,
):
    media = [
        professional.avatar_url,
        professional.cover_url,
    ]

    media.extend(
        item.image_url
        for item in (
            professional.portfolio_items
        )
    )

    media.extend(
        item.document_url
        for item in (
            professional.certifications
        )
        if item.document_url
    )

    return [
        item
        for item in media
        if item
    ]


def _anonymize_professional(
    professional,
    *,
    now,
):
    media = (
        _collect_professional_media(
            professional
        )
    )

    for experience in (
        professional.experiences
    ):
        experience.status = (
            ExperienceStatus.ARCHIVED
        )
        experience.is_featured = (
            False
        )

    for slot in (
        professional.slots
    ):
        if (
            _as_utc(
                slot.starts_at
            )
            <= now
        ):
            continue

        if (
            slot.status
            not in {
                SlotStatus.AVAILABLE,
                SlotStatus.HELD,
            }
        ):
            continue

        slot.status = (
            SlotStatus.EXPIRED
        )
        slot.hold_expires_at = (
            None
        )

        for booking in (
            slot.bookings
        ):
            if (
                booking.status
                == BookingStatus.PENDING
            ):
                booking.status = (
                    BookingStatus.CANCELLED
                )
                booking.cancelled_at = (
                    now
                )
                booking.cancellation_reason = (
                    "Conta profissional removida"
                )
                booking.hold_expires_at = (
                    None
                )

    professional.user = None
    professional.display_name = (
        "Profissional removido"
    )
    professional.headline = None
    professional.bio = None
    professional.primary_specialty = (
        None
    )
    professional.specialties_text = (
        None
    )
    professional.phone = None
    professional.whatsapp_enabled = (
        False
    )
    professional.instagram = None
    professional.city = None
    professional.state = None
    professional.avatar_url = None
    professional.cover_url = None
    professional.onboarding_completed = (
        False
    )
    professional.published_at = (
        None
    )
    professional.is_verified = (
        False
    )
    professional.is_active = (
        False
    )
    professional.claimed_at = (
        None
    )

    for item in list(
        professional.portfolio_items
    ):
        db.session.delete(
            item
        )

    for item in list(
        professional.certifications
    ):
        db.session.delete(
            item
        )

    for item in list(
        professional.calendar_connections
    ):
        db.session.delete(
            item
        )

    for item in list(
        professional.memberships
    ):
        db.session.delete(
            item
        )

    return media


def anonymize_account(
    user,
    *,
    now=None,
):
    if user is None:
        raise ValueError(
            "Conta inválida."
        )

    if not user.is_active:
        return AccountDeletionResult(
            removed_media=0,
            queued_media=0,
        )

    blockers = (
        account_deletion_blockers(
            user
        )
    )

    if blockers:
        raise AccountDeletionBlocked(
            blockers
        )

    current_time = _now(
        now
    )
    media_paths = []

    profile = (
        user.client_profile
    )

    if profile is not None:
        if profile.avatar_url:
            media_paths.append(
                profile.avatar_url
            )

        profile.phone = None
        profile.birth_date = None
        profile.city = None
        profile.state = None
        profile.avatar_url = None
        profile.onboarding_completed = (
            False
        )

    professional = (
        user.professional_profile
    )

    if professional is not None:
        media_paths.extend(
            _anonymize_professional(
                professional,
                now=current_time,
            )
        )

    for access in list(
        user.establishment_accesses
    ):
        db.session.delete(
            access
        )

    db.session.execute(
        update(ContactClick)
        .where(
            ContactClick.user_id
            == user.id
        )
        .values(
            user_id=None
        )
    )

    db.session.execute(
        delete(AccountToken).where(
            AccountToken.user_id
            == user.id
        )
    )

    db.session.execute(
        delete(ApiSession).where(
            ApiSession.user_id
            == user.id
        )
    )

    user.name = "Conta removida"
    user.email = (
        "deleted-"
        f"{user.id}-"
        f"{uuid4().hex}"
        "@deleted.iddun.invalid"
    )
    user.set_password(
        secrets.token_urlsafe(
            48
        )
    )
    user.role = UserRole.CLIENT
    user.email_verified_at = (
        None
    )
    user.is_active_account = (
        False
    )
    user.deleted_at = (
        current_time
    )

    db.session.commit()

    removed = (
        delete_uploaded_files(
            media_paths
        )
    )

    return AccountDeletionResult(
        removed_media=len(
            removed
        ),
        queued_media=len(
            media_paths
        ),
    )
