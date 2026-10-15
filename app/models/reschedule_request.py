from app.extensions import db
from app.services.time_service import utcnow


class RescheduleRequest(db.Model):
    __tablename__ = "booking_reschedule_requests"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=False, index=True)
    requested_slot_id = db.Column(db.Integer, db.ForeignKey("experience_slots.id", ondelete="RESTRICT"), nullable=False)
    original_slot_id = db.Column(db.Integer, db.ForeignKey("experience_slots.id", ondelete="RESTRICT"), nullable=False)
    requested_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    resolved_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = db.Column(db.String(24), nullable=False, default="pending", index=True)
    reason = db.Column(db.String(255), nullable=True)
    resolution_reason = db.Column(db.String(255), nullable=True)
    requested_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)

    booking = db.relationship("Booking", backref=db.backref("reschedule_requests", order_by="RescheduleRequest.requested_at.desc()"))
    requested_slot = db.relationship("ExperienceSlot", foreign_keys=[requested_slot_id])
    original_slot = db.relationship("ExperienceSlot", foreign_keys=[original_slot_id])

    __table_args__ = (
        db.CheckConstraint("status IN ('pending', 'withdrawn', 'executed', 'rejected')", name="ck_reschedule_request_status"),
        db.Index("uq_pending_reschedule_per_booking", "booking_id", unique=True,
                 postgresql_where=db.text("status = 'pending'"),
                 sqlite_where=db.text("status = 'pending'")),
    )
