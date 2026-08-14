"""Per-user aggregate progress and per-problem attempt state."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import Difficulty

if TYPE_CHECKING:
    from app.models.user import User


class UserProgress(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Denormalized rollup powering the dashboard in a single row read."""

    __tablename__ = "user_progress"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    problems_solved: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    easy_solved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    medium_solved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hard_solved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    interview_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    average_interview_score: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)

    current_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_active_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    total_submissions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    accepted_submissions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # { "graphs": {"attempted": 12, "solved": 5}, ... } — drives weak-area detection.
    topic_stats: Mapped[dict[str, dict[str, int]]] = mapped_column(
        JSONB, default=dict, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="progress")

    @property
    def accuracy(self) -> float:
        if not self.total_submissions:
            return 0.0
        return round(self.accepted_submissions / self.total_submissions * 100, 1)


class ProblemAttempt(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Per (user, problem) state: solved flag, bookmark, notes."""

    __tablename__ = "problem_attempts"
    __table_args__ = (
        UniqueConstraint("user_id", "problem_id", name="uq_problem_attempts_user_problem"),
        Index("ix_problem_attempts_solved_at", "user_id", "solved_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("problems.id", ondelete="CASCADE"), nullable=False
    )
    difficulty: Mapped[Difficulty] = mapped_column(
        Enum(Difficulty, name="difficulty", native_enum=True, create_type=False), nullable=False
    )

    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_solved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    solved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    is_bookmarked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_language: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_code: Mapped[str | None] = mapped_column(Text, nullable=True)


class ActivityDay(Base, UUIDPrimaryKeyMixin):
    """One row per user per active day. Backs the contribution heatmap."""

    __tablename__ = "activity_days"
    __table_args__ = (UniqueConstraint("user_id", "day", name="uq_activity_days_user_day"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day: Mapped[date] = mapped_column(Date, nullable=False)
    problems_solved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    interviews_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    minutes_active: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
