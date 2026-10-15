from app.extensions import db
from app.services.time_service import utcnow


class NoShowDispute(db.Model):
    __tablename__ = "booking_no_show_disputes"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=False, index=True)
    client_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    reviewer_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    justification = db.Column(db.Text, nullable=False)
    evidence_reference = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(24), nullable=False, default="pending", index=True)
    resolution_note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    booking = db.relationship("Booking", backref=db.backref("no_show_disputes", order_by="NoShowDispute.created_at.desc()"))

    __table_args__ = (
        db.CheckConstraint("status IN ('pending', 'accepted', 'rejected')", name="ck_no_show_dispute_status"),
        db.Index("uq_pending_no_show_dispute", "booking_id", unique=True,
                 postgresql_where=db.text("status = 'pending'"),
                 sqlite_where=db.text("status = 'pending'")),
    )
