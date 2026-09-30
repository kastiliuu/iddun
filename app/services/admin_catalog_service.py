from sqlalchemy import func, select

from app.extensions import db
from app.models.establishment import Establishment, MembershipStatus, ProfessionalEstablishmentMembership
from app.models.booking import Booking, BookingStatus, ExperienceSlot, SlotStatus
from app.models.experience import Experience, ExperienceStatus
from app.models.professional import ProfessionalProfile


def dashboard_counts():
    return {
        "professionals": db.session.scalar(select(func.count()).select_from(ProfessionalProfile)) or 0,
        "establishments": db.session.scalar(select(func.count()).select_from(Establishment)) or 0,
        "experiences": db.session.scalar(select(func.count()).select_from(Experience)) or 0,
        "published": db.session.scalar(
            select(func.count()).select_from(Experience).where(Experience.status == ExperienceStatus.PUBLISHED)
        ) or 0,
        "available_slots": db.session.scalar(
            select(func.count()).select_from(ExperienceSlot).where(ExperienceSlot.status == SlotStatus.AVAILABLE)
        ) or 0,
        "confirmed_bookings": db.session.scalar(
            select(func.count()).select_from(Booking).where(Booking.status == BookingStatus.CONFIRMED)
        ) or 0,
        "active_memberships": db.session.scalar(
            select(func.count())
            .select_from(ProfessionalEstablishmentMembership)
            .where(ProfessionalEstablishmentMembership.status == MembershipStatus.ACTIVE)
        ) or 0,
    }


def professional_choices():
    professionals = db.session.scalars(
        select(ProfessionalProfile).order_by(ProfessionalProfile.display_name)
    ).all()
    return [
        (item.id, item.display_name if item.is_active else f"{item.display_name} (inativo)")
        for item in professionals
    ]


def establishment_choices(include_empty=False):
    establishments = db.session.scalars(
        select(Establishment).order_by(Establishment.name)
    ).all()
    choices = [
        (item.id, item.name if item.is_active else f"{item.name} (inativo)")
        for item in establishments
    ]
    if include_empty:
        return [(0, "Sem estabelecimento definido")] + choices
    return choices


def validate_experience_publication(professional_id, establishment_id=None):
    """(a) Impede que o admin publique algo que o catálogo público ocultaria."""
    professional = db.session.get(ProfessionalProfile, professional_id)
    if professional is None:
        raise ValueError("Selecione um profissional válido antes de publicar a experiência.")
    if not professional.is_active:
        raise ValueError(
            f"Ative o perfil de {professional.display_name} antes de publicar a experiência."
        )

    if not establishment_id:
        return

    establishment = db.session.get(Establishment, establishment_id)
    if establishment is None:
        raise ValueError("Selecione um estabelecimento válido antes de publicar a experiência.")
    if not establishment.is_active:
        raise ValueError(
            f"Ative o estabelecimento {establishment.name} antes de publicar a experiência."
        )


def publish_experience(experience):
    """(a) Publica somente experiências elegíveis para o catálogo público."""
    validate_experience_publication(
        professional_id=experience.professional_id,
        establishment_id=experience.establishment_id,
    )
    experience.status = ExperienceStatus.PUBLISHED
    db.session.add(experience)
    return experience


def _can_keep_active_membership(membership):
    if membership.id is None:
        return False

    table = ProfessionalEstablishmentMembership.__table__

    # Consulta o registro gravado, antes que alterações feitas no formulário
    # sejam enviadas ao banco pelo autoflush da sessão.
    with db.session.no_autoflush:
        previous = db.session.execute(
            select(
                table.c.status,
                table.c.professional_id,
                table.c.establishment_id,
            ).where(table.c.id == membership.id)
        ).one_or_none()

    return (
        previous is not None
        and previous.status == MembershipStatus.ACTIVE
        and previous.professional_id == membership.professional_id
        and previous.establishment_id == membership.establishment_id
    )


def save_membership(membership):
    if membership.status == MembershipStatus.ACTIVE:
        if not _can_keep_active_membership(membership):
            raise ValueError(
                "O vínculo só pode ser ativado pelo profissional ao aceitar o convite. "
                "Selecione Pendente para enviar o convite."
            )

        duplicate = db.session.scalar(
            select(ProfessionalEstablishmentMembership.id).where(
                ProfessionalEstablishmentMembership.professional_id == membership.professional_id,
                ProfessionalEstablishmentMembership.establishment_id == membership.establishment_id,
                ProfessionalEstablishmentMembership.status == MembershipStatus.ACTIVE,
                ProfessionalEstablishmentMembership.id != (membership.id or 0),
            )
        )
        if duplicate is not None:
            raise ValueError("Já existe um vínculo ativo entre este profissional e este estabelecimento.")

    if membership.is_primary and membership.status == MembershipStatus.ACTIVE:
        others = db.session.scalars(
            select(ProfessionalEstablishmentMembership).where(
                ProfessionalEstablishmentMembership.professional_id == membership.professional_id,
                ProfessionalEstablishmentMembership.id != (membership.id or 0),
                ProfessionalEstablishmentMembership.is_primary.is_(True),
            )
        ).all()
        for item in others:
            item.is_primary = False

    if membership.status != MembershipStatus.ACTIVE:
        membership.is_primary = False

    db.session.add(membership)
    db.session.commit()
    return membership


def experience_choices(published_only=False):
    query = select(Experience).order_by(Experience.title)
    if published_only:
        query = query.where(Experience.status == ExperienceStatus.PUBLISHED)
    items = db.session.scalars(query).all()
    return [
        (item.id, f"{item.title} · {item.professional.display_name}")
        for item in items
    ]
