from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class ProfessionalWorkingHour(db.Model):
    __tablename__ = "professional_working_hours"

    id = db.Column(db.Integer, primary_key=True)
    professional_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "professional_profiles.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    weekday = db.Column(
        db.SmallInteger,
        nullable=False,
        index=True,
    )
    start_time = db.Column(
        db.Time,
        nullable=False,
    )
    end_time = db.Column(
        db.Time,
        nullable=False,
    )
    break_start_time = db.Column(
        db.Time,
        nullable=True,
    )
    break_end_time = db.Column(
        db.Time,
        nullable=True,
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    professional = db.relationship(
        "ProfessionalProfile",
        back_populates="working_hours",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "professional_id",
            "weekday",
            name=(
                "uq_professional_working_hours_"
                "professional_weekday"
            ),
        ),
        db.CheckConstraint(
            "weekday >= 0 AND weekday <= 6",
            name=(
                "ck_professional_working_hours_"
                "weekday"
            ),
        ),
        db.CheckConstraint(
            "start_time < end_time",
            name=(
                "ck_professional_working_hours_"
                "range"
            ),
        ),
    )


WEEKDAY_LABELS = {
    0: "Segunda-feira",
    1: "Terça-feira",
    2: "Quarta-feira",
    3: "Quinta-feira",
    4: "Sexta-feira",
    5: "Sábado",
    6: "Domingo",
}
