from sqlalchemy import select

from app.extensions import db
from app.models.booking import BookingStatus
from app.models.reputation import Review, ReviewTarget


class ReviewError(ValueError):
    pass


def _validate_rating(value):
    try:
        rating = int(value)
    except (TypeError, ValueError) as exc:
        raise ReviewError("Escolha uma nota de 1 a 5 estrelas.") from exc
    if rating < 1 or rating > 5:
        raise ReviewError("Escolha uma nota de 1 a 5 estrelas.")
    return rating


def _as_bool(value):
    if isinstance(value, bool):
        return value
    if value in {"yes", "sim", "1", 1, True}:
        return True
    if value in {"no", "nao", "não", "0", 0, False}:
        return False
    raise ReviewError("Informe se você recomenda esta experiência.")


def get_review(booking_id, target_type):
    return db.session.scalar(
        select(Review).where(
            Review.booking_id == booking_id,
            Review.target_type == target_type,
        )
    )


def can_review_booking(booking, client_profile):
    return (
        booking is not None
        and client_profile is not None
        and booking.client_id == client_profile.id
        and booking.status == BookingStatus.COMPLETED
    )


def save_review(
    *,
    booking,
    client_profile,
    target_type,
    rating,
    recommended,
    comment=None,
):
    if not can_review_booking(
        booking,
        client_profile,
    ):
        raise ReviewError(
            (
                "A avaliação só fica disponível "
                "depois que o atendimento é concluído."
            )
        )

    if target_type not in ReviewTarget.CHOICES:
        raise ReviewError(
            "Destino de avaliação inválido."
        )

    professional = None
    establishment = None

    if target_type == ReviewTarget.PROFESSIONAL:
        professional = booking.professional
    else:
        establishment = booking.establishment

        if establishment is None:
            raise ReviewError(
                (
                    "Esta reserva não possui um "
                    "estabelecimento para avaliar."
                )
            )

    review = get_review(
        booking.id,
        target_type,
    )

    if review is None:
        review = Review(
            booking=booking,
            client=client_profile,
            target_type=target_type,
            professional=professional,
            establishment=establishment,
        )
        db.session.add(review)
    else:
        review.professional = professional
        review.establishment = establishment

    review.rating = _validate_rating(
        rating
    )
    review.recommended = _as_bool(
        recommended
    )
    review.comment = (
        (comment or "").strip()
        or None
    )

    db.session.flush()

    return review


def save_booking_reviews(
    *,
    booking,
    client_profile,
    professional_rating,
    professional_recommended,
    professional_comment=None,
    establishment_rating=None,
    establishment_recommended=None,
    establishment_comment=None,
):
    save_review(
        booking=booking,
        client_profile=client_profile,
        target_type=ReviewTarget.PROFESSIONAL,
        rating=professional_rating,
        recommended=professional_recommended,
        comment=professional_comment,
    )

    has_establishment_review = (
        booking.establishment is not None
        and establishment_rating not in (None, "")
        and establishment_recommended not in (None, "")
    )

    if has_establishment_review:
        save_review(
            booking=booking,
            client_profile=client_profile,
            target_type=ReviewTarget.ESTABLISHMENT,
            rating=establishment_rating,
            recommended=establishment_recommended,
            comment=establishment_comment,
        )

    db.session.commit()


def reputation_summary(reviews):
    visible = [review for review in (reviews or []) if review.is_visible]
    if not visible:
        return {
            "count": 0,
            "average": None,
            "average_label": "Novo",
            "recommended_count": 0,
            "recommendation_percent": None,
            "recommendation_label": "Sem avaliações ainda",
        }

    average = sum(review.rating for review in visible) / len(visible)
    recommended_count = sum(1 for review in visible if review.recommended)
    recommendation_percent = round((recommended_count / len(visible)) * 100)
    return {
        "count": len(visible),
        "average": average,
        "average_label": f"{average:.1f}".replace(".", ","),
        "recommended_count": recommended_count,
        "recommendation_percent": recommendation_percent,
        "recommendation_label": f"{recommendation_percent}% recomendam",
    }
