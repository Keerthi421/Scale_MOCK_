"""Problem catalog: statement, study guide, test cases, and free/premium gating."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
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
from app.models.enums import Difficulty, Language, ProblemCategory

if TYPE_CHECKING:
    from app.models.discussion import DiscussionPost


class Problem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "problems"
    __table_args__ = (
        # The problem-list screen filters on category + difficulty and sorts by
        # order_index; this composite covers that access path directly.
        Index("ix_problems_browse", "category", "difficulty", "order_index"),
        Index("ix_problems_tags", "tags", postgresql_using="gin"),
        Index("ix_problems_companies", "companies", postgresql_using="gin"),
    )

    slug: Mapped[str] = mapped_column(String(160), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[ProblemCategory] = mapped_column(
        Enum(ProblemCategory, name="problem_category", native_enum=True), nullable=False
    )
    difficulty: Mapped[Difficulty] = mapped_column(
        Enum(Difficulty, name="difficulty", native_enum=True), nullable=False
    )

    summary: Mapped[str] = mapped_column(Text, nullable=False)
    description_md: Mapped[str] = mapped_column(Text, nullable=False)
    # Long-form study guide (architecture walkthrough, capacity math, UML,
    # complexity analysis). Null until content is authored.
    study_guide_md: Mapped[str | None] = mapped_column(Text, nullable=True)

    tags: Mapped[list[str]] = mapped_column(ARRAY(String(64)), default=list, nullable=False)
    companies: Mapped[list[str]] = mapped_column(ARRAY(String(64)), default=list, nullable=False)

    # Gating lives on the row, resolved server-side. Never sent as a hint the
    # client can override — the API omits gated fields entirely.
    is_premium: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # DSA-specific. Null for HLD/LLD/frontend problems.
    starter_code: Mapped[dict[str, str] | None] = mapped_column(JSONB, nullable=True)
    solution_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    time_limit_ms: Mapped[int] = mapped_column(Integer, default=2000, nullable=False)
    memory_limit_mb: Mapped[int] = mapped_column(Integer, default=256, nullable=False)

    # Denormalized counters maintained by the submission service.
    total_submissions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    accepted_submissions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    test_cases: Mapped[list[TestCase]] = relationship(
        back_populates="problem", cascade="all, delete-orphan", order_by="TestCase.order_index"
    )
    discussion_posts: Mapped[list[DiscussionPost]] = relationship(
        back_populates="problem", cascade="all, delete-orphan"
    )

    @property
    def acceptance_rate(self) -> float:
        if not self.total_submissions:
            return 0.0
        return round(self.accepted_submissions / self.total_submissions * 100, 1)


class TestCase(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "test_cases"
    __table_args__ = (
        UniqueConstraint("problem_id", "order_index", name="uq_test_cases_problem_order"),
    )

    problem_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("problems.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    stdin: Mapped[str] = mapped_column(Text, nullable=False)
    expected_stdout: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Hidden cases are never serialized to the client, only used by the runner.
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    problem: Mapped[Problem] = relationship(back_populates="test_cases")


class ProblemSolutionRef(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Reference implementations per language, used to validate authored tests."""

    __tablename__ = "problem_solution_refs"
    __table_args__ = (
        UniqueConstraint("problem_id", "language", name="uq_solution_ref_problem_language"),
    )

    problem_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("problems.id", ondelete="CASCADE"), nullable=False
    )
    language: Mapped[Language] = mapped_column(
        Enum(Language, name="language", native_enum=True), nullable=False
    )
    code: Mapped[str] = mapped_column(Text, nullable=False)
    time_complexity: Mapped[str | None] = mapped_column(String(64), nullable=True)
    space_complexity: Mapped[str | None] = mapped_column(String(64), nullable=True)


class ProblemRubric(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Scoring rubric the AI interviewer grades against.

    Kept in the database rather than the prompt so rubrics can be tuned per
    problem without a deploy, and so scores stay comparable across model
    versions by pinning the rubric that produced them.
    """

    __tablename__ = "problem_rubrics"

    problem_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("problems.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # [{ "key": "tradeoffs", "label": "...", "weight": 0.2, "criteria": [...] }]
    dimensions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    # Points the interviewer should steer toward if the candidate misses them.
    expected_talking_points: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, nullable=False
    )
    passing_score: Mapped[float] = mapped_column(Float, default=60.0, nullable=False)
