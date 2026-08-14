"""Code submissions and per-test-case results."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import Language, SubmissionStatus

if TYPE_CHECKING:
    from app.models.user import User


class Submission(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "submissions"
    __table_args__ = (
        Index("ix_submissions_user_problem", "user_id", "problem_id", "created_at"),
        Index("ix_submissions_problem_status", "problem_id", "status"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("problems.id", ondelete="CASCADE"), nullable=False
    )

    language: Mapped[Language] = mapped_column(
        Enum(Language, name="language", native_enum=True, create_type=False), nullable=False
    )
    code: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus, name="submission_status", native_enum=True),
        default=SubmissionStatus.PENDING,
        nullable=False,
    )

    # A "run" executes visible cases only; a "submit" executes everything and
    # is what counts toward progress and acceptance rate.
    is_final: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tests_passed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tests_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    runtime_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_kb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Compile/runtime error text, truncated by the service before storage.
    error_output: Mapped[str | None] = mapped_column(Text, nullable=True)

    # AI complexity analysis, populated asynchronously by a worker.
    analyzed_time_complexity: Mapped[str | None] = mapped_column(String(64), nullable=True)
    analyzed_space_complexity: Mapped[str | None] = mapped_column(String(64), nullable=True)
    code_quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    user: Mapped[User] = relationship(back_populates="submissions")
    results: Mapped[list[SubmissionTestResult]] = relationship(
        back_populates="submission", cascade="all, delete-orphan"
    )


class SubmissionTestResult(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "submission_test_results"

    submission_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    test_case_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("test_cases.id", ondelete="SET NULL"), nullable=True
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # Only populated for visible test cases; hidden-case output is withheld so
    # the expected values cannot be reconstructed by probing.
    actual_stdout: Mapped[str | None] = mapped_column(Text, nullable=True)
    runtime_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    submission: Mapped[Submission] = relationship(back_populates="results")
