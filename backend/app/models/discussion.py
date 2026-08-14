"""Per-problem discussion threads."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.problem import Problem


class DiscussionPost(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "discussion_posts"
    __table_args__ = (Index("ix_discussion_posts_problem_hot", "problem_id", "upvote_count"),)

    problem_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("problems.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Null for a top-level post; set for a reply. One level of nesting only.
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("discussion_posts.id", ondelete="CASCADE"), nullable=True
    )

    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    # Denormalized from DiscussionVote so the thread list needs no aggregate.
    upvote_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reply_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Soft delete: preserves reply threading when a parent is removed.
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Set when a post reveals a full solution, so it can be collapsed by default.
    is_spoiler: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    problem: Mapped[Problem] = relationship(back_populates="discussion_posts")


class DiscussionVote(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "discussion_votes"
    __table_args__ = (UniqueConstraint("post_id", "user_id", name="uq_discussion_votes_post_user"),)

    post_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("discussion_posts.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
