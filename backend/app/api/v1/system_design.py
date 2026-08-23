"""System-design endpoints: problem sheet, canvas workspace, AI review."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel

from app.ai.anthropic_provider import AnthropicProvider
from app.api.deps import (
    CurrentEntitlements,
    CurrentUser,
    DbSession,
    OptionalUser,
    ai_rate_limit,
    current_entitlements,
)
from app.core.entitlements import Entitlements, get_entitlements
from app.models.user import User
from app.schemas.system_design import (
    ComponentOut,
    HldProblemDetailOut,
    HldProblemSummary,
    ReviewOut,
    WorkspaceOut,
    WorkspaceSaveRequest,
)
from app.services.design_review_service import DesignReviewService
from app.services.system_design_service import SHEET_TIERS, SystemDesignService

router = APIRouter(prefix="/system-design", tags=["system-design"])

AIRateLimited = Annotated[None, Depends(ai_rate_limit())]


class ProblemPage(BaseModel):
    items: list[HldProblemSummary]
    total: int
    limit: int
    offset: int


class ShareOut(BaseModel):
    share_slug: str


def _anonymous_entitlements(user: User | None) -> Entitlements:
    """Anonymous callers get free-tier visibility, not an error.

    The sheet is browsable logged-out — that is the top of the funnel — but
    gated content is withheld exactly as it is for a signed-in free user.
    """
    from app.core.entitlements import _FREE

    return get_entitlements(user) if user is not None else _FREE


@router.get("/problems", response_model=ProblemPage)
async def list_problems(
    db: DbSession,
    user: OptionalUser,
    sheet_tier: Annotated[int, Query(description=f"One of {SHEET_TIERS}")] = 150,
    difficulty: str | None = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProblemPage:
    items, total = await SystemDesignService(db).list_problems(
        entitlements=_anonymous_entitlements(user),
        user_id=user.id if user else None,
        sheet_tier=sheet_tier,
        difficulty=difficulty,
        search=search,
        limit=limit,
        offset=offset,
    )
    return ProblemPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/problems/{slug}", response_model=HldProblemDetailOut)
async def get_problem(slug: str, db: DbSession, user: OptionalUser) -> HldProblemDetailOut:
    return await SystemDesignService(db).get_problem(
        slug, entitlements=_anonymous_entitlements(user)
    )


@router.get("/components", response_model=list[ComponentOut])
async def list_components(db: DbSession) -> list[ComponentOut]:
    """The canvas palette. Served from the DB so it cannot drift from the
    component set the reviewer understands."""
    rows = await SystemDesignService(db).list_components()
    return [ComponentOut.model_validate(r) for r in rows]


@router.post(
    "/problems/{slug}/workspace",
    response_model=WorkspaceOut,
    status_code=status.HTTP_200_OK,
)
async def open_workspace(slug: str, db: DbSession, user: CurrentUser) -> WorkspaceOut:
    """Open (or lazily create) this user's canvas for a problem."""
    workspace = await SystemDesignService(db).get_or_create_workspace(
        user_id=user.id, problem_slug=slug
    )
    return WorkspaceOut.model_validate(workspace)


@router.put("/workspaces/{workspace_id}", response_model=WorkspaceOut)
async def save_workspace(
    workspace_id: uuid.UUID,
    payload: WorkspaceSaveRequest,
    db: DbSession,
    user: CurrentUser,
) -> WorkspaceOut:
    workspace = await SystemDesignService(db).save_workspace(
        workspace_id, payload, user_id=user.id
    )
    return WorkspaceOut.model_validate(workspace)


@router.post("/workspaces/{workspace_id}/share", response_model=ShareOut)
async def share_workspace(
    workspace_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    entitlements: CurrentEntitlements,
) -> ShareOut:
    slug = await SystemDesignService(db).create_share_link(
        workspace_id, user_id=user.id, entitlements=entitlements
    )
    return ShareOut(share_slug=slug)


@router.post(
    "/workspaces/{workspace_id}/review",
    response_model=ReviewOut,
    status_code=status.HTTP_201_CREATED,
)
async def review_workspace(
    workspace_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    _: AIRateLimited,
    entitlements: Annotated[Entitlements, Depends(current_entitlements)],
) -> ReviewOut:
    """Run the AI design review. Rate-limited and premium-gated server-side."""
    reviewer = DesignReviewService(AnthropicProvider())
    review = await SystemDesignService(db).review_workspace(
        workspace_id,
        user_id=user.id,
        entitlements=entitlements,
        reviewer=reviewer,
    )
    return ReviewOut.model_validate(review)
