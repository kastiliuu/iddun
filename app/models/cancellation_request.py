from app.extensions import db
from app.services.time_service import utcnow


class CancellationRequest(db.Model):
    __tablename__ = "booking_cancellation_requests"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=False, index=True)
    client_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    reason = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    requested_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    resolved_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolution_reason = db.Column(db.String(255), nullable=True)
    booking = db.relationship("Booking", backref=db.backref("cancellation_requests", order_by="CancellationRequest.requested_at.desc()"))

    __table_args__ = (
        db.CheckConstraint("status IN ('pending', 'withdrawn', 'executed')", name="ck_cancellation_request_status"),
        db.Index("ix_booking_cancellation_request_status", "booking_id", "status"),
        db.Index("uq_booking_pending_cancellation", "booking_id", unique=True,
                 postgresql_where=db.text("status = 'pending'"),
                 sqlite_where=db.text("status = 'pending'")),
    )
