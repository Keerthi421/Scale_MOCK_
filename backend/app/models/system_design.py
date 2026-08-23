"""System-design workspaces: the persisted architecture canvas and its reviews."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import NodeKind

if TYPE_CHECKING:
    from app.models.problem import Problem


class SystemDesignWorkspace(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One user's canvas for one HLD problem.

    Nodes and edges are stored as JSONB rather than child tables. A canvas is
    always read and written whole — there is no query that fetches "one node" —
    so normalizing them would buy nothing and cost a join plus N inserts on
    every autosave.
    """

    __tablename__ = "system_design_workspaces"
    __table_args__ = (
        UniqueConstraint("user_id", "problem_id", name="uq_workspace_user_problem"),
        Index("ix_workspaces_user_recent", "user_id", "updated_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("problems.id", ondelete="CASCADE"), nullable=False
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)

    # [{ "id", "kind", "label", "x", "y", "notes" }]
    nodes: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    # [{ "id", "source", "target", "label" }]
    edges: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)

    candidate_notes_md: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Monotonic counter bumped on every save. The client sends the version it
    # last read; a mismatch means another tab saved in between, so the write is
    # rejected rather than silently clobbering the other tab's canvas.
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Share links are opt-in and unguessable; null means private.
    share_slug: Mapped[str | None] = mapped_column(
        String(32), unique=True, nullable=True, index=True
    )

    problem: Mapped[Problem] = relationship()
    reviews: Mapped[list[SystemDesignReview]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
        order_by="SystemDesignReview.created_at.desc()",
    )


class SystemDesignReview(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A stored AI review of one canvas snapshot.

    Reviews are append-only: each one pins the canvas version, model, and prompt
    version that produced it, so a score stays interpretable after the design or
    the prompt changes.
    """

    __tablename__ = "system_design_reviews"
    __table_args__ = (Index("ix_reviews_workspace_recent", "workspace_id", "created_at"),)

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("system_design_workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    workspace_version: Mapped[int] = mapped_column(Integer, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)

    # The full DesignReview payload, validated against the Pydantic schema
    # before it is written. Stored whole so the report renders without joins.
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    model_id: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(32), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    workspace: Mapped[SystemDesignWorkspace] = relationship(back_populates="reviews")


class HldProblemDetail(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """HLD-specific content for a Problem row.

    Kept out of `problems` because these columns are null for every DSA and
    frontend problem, and the HLD problem page needs all of them at once.
    """

    __tablename__ = "hld_problem_details"

    problem_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("problems.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    functional_requirements: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    non_functional_requirements: Mapped[list[str]] = mapped_column(
        JSONB, default=list, nullable=False
    )

    # [{ "metric", "assumption", "working", "result" }] — the capacity estimate
    # worked through, so the guide can show the arithmetic rather than a number.
    capacity_estimation: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, nullable=False
    )
    api_design_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_model_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    architecture_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    scaling_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    tradeoffs_md: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Node kinds a strong answer is expected to include. Drives the hint system
    # and gives the reviewer a per-problem baseline instead of a generic checklist.
    expected_components: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)

    # Which sheet tiers include this problem: 25, 75, 150.
    sheet_tier: Mapped[int] = mapped_column(Integer, default=150, nullable=False, index=True)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=45, nullable=False)
    is_free_preview: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    last_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ComponentCatalogEntry(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """The canvas palette, in the database rather than hardcoded in the client.

    Adding a component is then a seed change, not a frontend deploy, and the
    reviewer and the palette read the same list — so they cannot drift.
    """

    __tablename__ = "component_catalog"

    kind: Mapped[NodeKind] = mapped_column(
        Enum(NodeKind, name="node_kind", native_enum=True), unique=True, nullable=False
    )
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    # Lucide icon name; the client maps it to a component.
    icon: Mapped[str] = mapped_column(String(48), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
