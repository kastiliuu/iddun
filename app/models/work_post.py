from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class WorkPostAuthorType:
    CLIENT = "client"
    PROFESSIONAL = "professional"
    ESTABLISHMENT = "establishment"

    VALUES = (
        CLIENT,
        PROFESSIONAL,
        ESTABLISHMENT,
    )


class WorkPostStatus:
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    # Ocultado pela equipe de moderação (DEC-ID-231, 276).
    HIDDEN = "hidden"
    # Removido pela autora; a linha fica para o histórico (D-SOC-09).
    REMOVED = "removed"

    VALUES = (
        DRAFT,
        PUBLISHED,
        ARCHIVED,
        HIDDEN,
        REMOVED,
    )


# Carrossel da V0 (D-SOC-02).
MAX_POST_IMAGES = 10


AUTHOR_SHAPE_SQL = (
    "("
    "author_type = 'client' "
    "AND client_profile_id IS NOT NULL "
    "AND professional_id IS NULL "
    "AND establishment_id IS NULL"
    ") OR ("
    "author_type = 'professional' "
    "AND professional_id IS NOT NULL "
    "AND establishment_id IS NULL "
    "AND client_profile_id IS NULL"
    ") OR ("
    "author_type = 'establishment' "
    "AND establishment_id IS NOT NULL "
    "AND professional_id IS NULL "
    "AND client_profile_id IS NULL"
    ")"
)

STATUS_SQL = (
    "status IN "
    "('draft', 'published', 'archived', 'hidden', 'removed')"
)


class WorkPost(db.Model):
    __tablename__ = "work_posts"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )
    author_type = db.Column(
        db.String(32),
        nullable=False,
        index=True,
    )
    professional_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "professional_profiles.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )
    establishment_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "establishments.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )
    # Autora Cliente (DEC-ID-224).
    client_profile_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "client_profiles.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )
    # Conta que criou o post; nula nos posts anteriores à PR 3.
    created_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )
    experience_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "experiences.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )
    caption = db.Column(
        db.String(1200),
        nullable=True,
    )
    # Primeira imagem do carrossel, mantida para clientes antigos; nula em
    # publicação só de texto (DEC-ID-225).
    image_url = db.Column(
        db.String(500),
        nullable=True,
    )
    image_focus_x = db.Column(
        db.SmallInteger,
        nullable=False,
        default=50,
    )
    image_focus_y = db.Column(
        db.SmallInteger,
        nullable=False,
        default=50,
    )
    status = db.Column(
        db.String(24),
        nullable=False,
        default=WorkPostStatus.PUBLISHED,
        index=True,
    )
    published_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
        default=utcnow,
        index=True,
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
    removed_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
    )

    client_profile = db.relationship(
        "ClientProfile",
    )
    created_by = db.relationship(
        "User",
        foreign_keys=[created_by_user_id],
    )
    media = db.relationship(
        "WorkPostMedia",
        back_populates="post",
        cascade="all, delete-orphan",
        order_by="WorkPostMedia.position",
    )
    professional = db.relationship(
        "ProfessionalProfile",
        back_populates="work_posts",
    )
    establishment = db.relationship(
        "Establishment",
        back_populates="work_posts",
    )
    experience = db.relationship(
        "Experience",
        back_populates="work_posts",
    )

    __table_args__ = (
        db.CheckConstraint(
            (
                AUTHOR_SHAPE_SQL
            ),
            name="ck_work_post_author_shape",
        ),
        db.CheckConstraint(
            (
                "image_focus_x BETWEEN 0 AND 100 "
                "AND image_focus_y BETWEEN 0 AND 100"
            ),
            name="ck_work_post_focus_range",
        ),
        db.CheckConstraint(
            STATUS_SQL,
            name="ck_work_post_status",
        ),
    )


class WorkPostMedia(db.Model):
    """Imagens ordenadas de uma publicação (carrossel até 10)."""

    __tablename__ = "work_post_media"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(
        db.Integer,
        db.ForeignKey("work_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position = db.Column(db.SmallInteger, nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    focus_x = db.Column(db.SmallInteger, nullable=False, default=50)
    focus_y = db.Column(db.SmallInteger, nullable=False, default=50)
    alt_text = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    post = db.relationship("WorkPost", back_populates="media")

    __table_args__ = (
        db.UniqueConstraint("post_id", "position", name="uq_work_post_media_position"),
        db.CheckConstraint("position BETWEEN 0 AND 9", name="ck_work_post_media_position"),
        db.CheckConstraint(
            "focus_x BETWEEN 0 AND 100 AND focus_y BETWEEN 0 AND 100",
            name="ck_work_post_media_focus",
        ),
    )


class WorkPostLike(db.Model):
    """Curtida: uma por pessoa e publicação, garantida pelo banco."""

    __tablename__ = "work_post_likes"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(
        db.Integer,
        db.ForeignKey("work_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        db.UniqueConstraint("post_id", "user_id", name="uq_work_post_like_user"),
    )


class CommentStatus:
    VISIBLE = "visible"
    HIDDEN_BY_AUTHOR = "hidden_by_author"
    REMOVED_BY_MODERATION = "removed_by_moderation"
    DELETED = "deleted"

    VALUES = (VISIBLE, HIDDEN_BY_AUTHOR, REMOVED_BY_MODERATION, DELETED)


class WorkPostComment(db.Model):
    """Comentário com resposta em um nível (D-SOC-02)."""

    __tablename__ = "work_post_comments"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(
        db.Integer,
        db.ForeignKey("work_posts.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id = db.Column(
        db.Integer,
        db.ForeignKey("work_post_comments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    body = db.Column(db.String(1000), nullable=False)
    status = db.Column(db.String(32), nullable=False, default=CommentStatus.VISIBLE)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    post = db.relationship("WorkPost")
    user = db.relationship("User")
    parent = db.relationship("WorkPostComment", remote_side=[id])

    __table_args__ = (
        db.Index("ix_work_post_comments_post_created", "post_id", "created_at"),
        db.CheckConstraint(
            "status IN ('visible', 'hidden_by_author', 'removed_by_moderation', 'deleted')",
            name="ck_work_post_comment_status",
        ),
    )


class ReportCategory:
    """D-SOC-10."""

    SPAM = "spam"
    SEXUAL = "sexual"
    VIOLENCE = "violence"
    HARASSMENT = "harassment"
    MISINFORMATION = "misinformation"
    IMAGE_RIGHTS = "image_rights"
    OTHER = "other"

    LABELS = {
        SPAM: "Spam ou golpe",
        SEXUAL: "Conteúdo sexual",
        VIOLENCE: "Violência ou ódio",
        HARASSMENT: "Assédio ou bullying",
        MISINFORMATION: "Informação falsa",
        IMAGE_RIGHTS: "Uso indevido de imagem ou direito autoral",
        OTHER: "Outro motivo",
    }
    VALUES = tuple(LABELS)


class ReportStatus:
    OPEN = "open"
    ACTIONED = "actioned"
    DISMISSED = "dismissed"

    VALUES = (OPEN, ACTIONED, DISMISSED)


class ReportTarget:
    POST = "post"
    COMMENT = "comment"

    VALUES = (POST, COMMENT)


class ContentReport(db.Model):
    """
    Denúncia (DEC-ID-231, 272, 275). O protocolo é só interno; o denunciante
    não recebe confirmação nem histórico. Denúncia não apaga nada.
    """

    __tablename__ = "content_reports"

    id = db.Column(db.Integer, primary_key=True)
    protocol = db.Column(db.String(36), nullable=False)
    reporter_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_type = db.Column(db.String(16), nullable=False)
    post_id = db.Column(
        db.Integer,
        db.ForeignKey("work_posts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    comment_id = db.Column(
        db.Integer,
        db.ForeignKey("work_post_comments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_excerpt = db.Column(db.String(500), nullable=True)
    category = db.Column(db.String(32), nullable=False)
    description = db.Column(db.String(1000), nullable=True)
    status = db.Column(db.String(16), nullable=False, default=ReportStatus.OPEN, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    decided_at = db.Column(db.DateTime(timezone=True), nullable=True)
    decided_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    decision_note = db.Column(db.String(500), nullable=True)

    post = db.relationship("WorkPost")
    comment = db.relationship("WorkPostComment")

    __table_args__ = (
        db.UniqueConstraint("protocol", name="uq_content_reports_protocol"),
        db.CheckConstraint("target_type IN ('post', 'comment')", name="ck_content_report_target"),
        db.CheckConstraint(
            "category IN ('spam', 'sexual', 'violence', 'harassment', "
            "'misinformation', 'image_rights', 'other')",
            name="ck_content_report_category",
        ),
        db.CheckConstraint(
            "status IN ('open', 'actioned', 'dismissed')",
            name="ck_content_report_status",
        ),
    )


class ModerationActionType:
    HIDE = "hide"
    RESTORE = "restore"
    REMOVE_COMMENT = "remove_comment"
    DISMISS = "dismiss"

    VALUES = (HIDE, RESTORE, REMOVE_COMMENT, DISMISS)


class ModerationAction(db.Model):
    """Histórico das decisões da equipe da plataforma (DEC-ID-231, 276)."""

    __tablename__ = "moderation_actions"

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(
        db.Integer,
        db.ForeignKey("content_reports.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_type = db.Column(db.String(16), nullable=False)
    post_id = db.Column(
        db.Integer,
        db.ForeignKey("work_posts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    comment_id = db.Column(
        db.Integer,
        db.ForeignKey("work_post_comments.id", ondelete="SET NULL"),
        nullable=True,
    )
    action = db.Column(db.String(24), nullable=False)
    moderator_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    note = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    moderator = db.relationship("User", foreign_keys=[moderator_user_id])

    __table_args__ = (
        db.CheckConstraint("target_type IN ('post', 'comment')", name="ck_moderation_action_target"),
        db.CheckConstraint(
            "action IN ('hide', 'restore', 'remove_comment', 'dismiss')",
            name="ck_moderation_action_type",
        ),
    )
