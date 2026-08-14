"""AI mock interview sessions, transcripts, and evaluations."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import Difficulty, InterviewStatus, MessageRole, ProblemCategory

if TYPE_CHECKING:
    from app.models.user import User


class MockInterview(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "mock_interviews"
    __table_args__ = (Index("ix_mock_interviews_user_recent", "user_id", "created_at"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    problem_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("problems.id", ondelete="SET NULL"), nullable=True
    )

    category: Mapped[ProblemCategory] = mapped_column(
        Enum(ProblemCategory, name="problem_category", native_enum=True, create_type=False),
        nullable=False,
    )
    difficulty: Mapped[Difficulty] = mapped_column(
        Enum(Difficulty, name="difficulty", native_enum=True, create_type=False), nullable=False
    )
    status: Mapped[InterviewStatus] = mapped_column(
        Enum(InterviewStatus, name="interview_status", native_enum=True),
        default=InterviewStatus.IN_PROGRESS,
        nullable=False,
        index=True,
    )

    # Interview configuration, captured at start so replays are reproducible.
    company_style: Mapped[str | None] = mapped_column(String(64), nullable=True)
    planned_duration_minutes: Mapped[int] = mapped_column(Integer, default=45, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Pinned for score comparability across model and prompt changes.
    model_id: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(32), nullable=False)
    rubric_version: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Candidate's final code/design artifact, if the interview involved one.
    final_artifact: Mapped[str | None] = mapped_column(Text, nullable=True)

    total_input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user: Mapped[User] = relationship(back_populates="interviews")
    messages: Mapped[list[InterviewMessage]] = relationship(
        back_populates="interview",
        cascade="all, delete-orphan",
        order_by="InterviewMessage.sequence",
    )
    evaluation: Mapped[InterviewEvaluation | None] = relationship(
        back_populates="interview", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def duration_seconds(self) -> int | None:
        if self.ended_at is None:
            return None
        return int((self.ended_at - self.started_at).total_seconds())


class InterviewMessage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One turn of the transcript.

    `sequence` is assigned by the service, not derived from timestamps, so
    ordering survives clock skew and concurrent streaming writes.
    """

    __tablename__ = "interview_messages"
    __table_args__ = (
        UniqueConstraint("interview_id", "sequence", name="uq_interview_messages_seq"),
    )

    interview_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("mock_interviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, name="message_role", native_enum=True), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Interviewer-only private reasoning (which rubric point this probes,
    # whether a hint was spent). Never serialized to the candidate.
    interviewer_state: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    interview: Mapped[MockInterview] = relationship(back_populates="messages")


class InterviewEvaluation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Structured post-interview report."""

    __tablename__ = "interview_evaluations"

    interview_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("mock_interviews.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    overall_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    # { "communication": 72.0, "approach": 81.0, "tradeoffs": 55.0, ... }
    dimension_scores: Mapped[dict[str, float]] = mapped_column(JSONB, nullable=False)

    strengths: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, nullable=False)
    weaknesses: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, nullable=False)
    recommendations: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, nullable=False)
    summary_md: Mapped[str] = mapped_column(Text, nullable=False)

    # Per-question breakdown and score-over-time series for the report charts.
    question_breakdown: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, nullable=False
    )
    recommended_problem_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(PgUUID(as_uuid=True)), default=list, nullable=False
    )

    interview: Mapped[MockInterview] = relationship(back_populates="evaluation")
