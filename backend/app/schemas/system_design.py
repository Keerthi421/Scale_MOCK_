"""Request/response models for the system-design area."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import Difficulty, NodeKind

# Bounds on a saved canvas. Generous for real designs, tight enough that a
# malicious client cannot store megabytes of JSONB per autosave.
MAX_NODES = 120
MAX_EDGES = 300


class CanvasNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64)
    kind: NodeKind
    label: str = Field(min_length=1, max_length=80)
    x: float
    y: float
    notes: str | None = Field(default=None, max_length=500)


class CanvasEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64)
    source: str = Field(min_length=1, max_length=64)
    target: str = Field(min_length=1, max_length=64)
    label: str | None = Field(default=None, max_length=80)


class CanvasPayload(BaseModel):
    """A full canvas snapshot. Validated as a graph, not just a pair of lists."""

    model_config = ConfigDict(extra="forbid")

    nodes: list[CanvasNode] = Field(max_length=MAX_NODES)
    edges: list[CanvasEdge] = Field(max_length=MAX_EDGES)
    candidate_notes_md: str | None = Field(default=None, max_length=20_000)

    @field_validator("nodes")
    @classmethod
    def _unique_node_ids(cls, v: list[CanvasNode]) -> list[CanvasNode]:
        ids = [n.id for n in v]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate node ids")
        return v

    @model_validator(mode="after")
    def _edges_reference_real_nodes(self) -> CanvasPayload:
        """Reject dangling edges.

        A saved edge pointing at a deleted node renders as a line into empty
        space and, worse, reaches the reviewer as a connection that does not
        exist — so it must be caught on write, not on read.
        """
        node_ids = {n.id for n in self.nodes}
        for edge in self.edges:
            if edge.source not in node_ids:
                raise ValueError(f"edge {edge.id} has unknown source {edge.source}")
            if edge.target not in node_ids:
                raise ValueError(f"edge {edge.id} has unknown target {edge.target}")
            if edge.source == edge.target:
                raise ValueError(f"edge {edge.id} connects a node to itself")
        return self


class WorkspaceSaveRequest(CanvasPayload):
    # The version the client last read. Omit only on first save.
    expected_version: int | None = Field(default=None, ge=1)


class WorkspaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    problem_id: uuid.UUID
    title: str
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    candidate_notes_md: str | None
    version: int
    share_slug: str | None
    updated_at: datetime


class ComponentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kind: NodeKind
    label: str
    category: str
    description: str
    icon: str


class HldProblemSummary(BaseModel):
    """Row in the sheet list. Deliberately omits the study guide — the list
    endpoint must not ship 150 long-form guides to render a table."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    title: str
    summary: str
    difficulty: Difficulty
    tags: list[str]
    companies: list[str]
    estimated_minutes: int
    sheet_tier: int
    is_premium: bool
    # Resolved per-user; false for anonymous callers.
    is_solved: bool = False
    is_locked: bool = False


class CapacityRow(BaseModel):
    metric: str
    assumption: str
    working: str
    result: str


class HldProblemDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    title: str
    difficulty: Difficulty
    description_md: str
    functional_requirements: list[str]
    non_functional_requirements: list[str]
    estimated_minutes: int
    tags: list[str]
    companies: list[str]

    # Gated fields. Omitted entirely (not blanked) for users without access, so
    # the payload never carries content the caller is not entitled to.
    study_guide_md: str | None = None
    capacity_estimation: list[CapacityRow] | None = None
    api_design_md: str | None = None
    data_model_md: str | None = None
    architecture_md: str | None = None
    scaling_md: str | None = None
    tradeoffs_md: str | None = None

    is_locked: bool = False


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Reviewing a specific version keeps the stored score tied to the canvas
    # that produced it, even if the user keeps editing while the review runs.
    workspace_version: int | None = Field(default=None, ge=1)


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    workspace_version: int
    overall_score: float
    payload: dict[str, Any]
    model_id: str
    prompt_version: str
    created_at: datetime
