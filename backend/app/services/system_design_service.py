"""System-design business logic: problem sheets, canvas persistence, reviews."""

from __future__ import annotations

import secrets
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.prompts.system_design import DesignSubmission
from app.core.entitlements import Entitlements
from app.core.exceptions import ConflictError, NotFoundError, PremiumRequiredError
from app.models.enums import ProblemCategory
from app.models.problem import Problem
from app.models.progress import ProblemAttempt
from app.models.system_design import (
    ComponentCatalogEntry,
    HldProblemDetail,
    SystemDesignReview,
    SystemDesignWorkspace,
)
from app.schemas.system_design import (
    HldProblemDetailOut,
    HldProblemSummary,
    WorkspaceSaveRequest,
)
from app.services.design_review_service import DesignReviewService

# Valid sheet sizes. A tier is a prefix of the ordered sheet, not a separate
# dataset — problem 12 is problem 12 in all three.
SHEET_TIERS = (25, 75, 150)


class SystemDesignService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # --- Problem sheet ------------------------------------------------------

    async def list_problems(
        self,
        *,
        entitlements: Entitlements,
        user_id: uuid.UUID | None,
        sheet_tier: int = 150,
        difficulty: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[HldProblemSummary], int]:
        if sheet_tier not in SHEET_TIERS:
            sheet_tier = 150

        stmt = (
            select(Problem, HldProblemDetail)
            .join(HldProblemDetail, HldProblemDetail.problem_id == Problem.id)
            .where(
                Problem.category == ProblemCategory.HLD,
                Problem.is_published.is_(True),
                HldProblemDetail.sheet_tier <= sheet_tier,
            )
        )
        if difficulty:
            stmt = stmt.where(Problem.difficulty == difficulty)
        if search:
            stmt = stmt.where(Problem.title.ilike(f"%{search}%"))

        total = await self.db.scalar(
            select(func.count()).select_from(stmt.subquery())
        )

        stmt = stmt.order_by(Problem.order_index).limit(limit).offset(offset)
        rows = (await self.db.execute(stmt)).all()

        solved: set[uuid.UUID] = set()
        if user_id is not None and rows:
            problem_ids = [p.id for p, _ in rows]
            solved_rows = await self.db.scalars(
                select(ProblemAttempt.problem_id).where(
                    ProblemAttempt.user_id == user_id,
                    ProblemAttempt.problem_id.in_(problem_ids),
                    ProblemAttempt.is_solved.is_(True),
                )
            )
            solved = set(solved_rows)

        can_access_all = entitlements.allows("can_access_premium_problems")

        summaries = [
            HldProblemSummary(
                id=problem.id,
                slug=problem.slug,
                title=problem.title,
                summary=problem.summary,
                difficulty=problem.difficulty,
                tags=problem.tags,
                companies=problem.companies,
                estimated_minutes=detail.estimated_minutes,
                sheet_tier=detail.sheet_tier,
                is_premium=problem.is_premium,
                is_solved=problem.id in solved,
                # Locked rows still appear in the list — the user should see
                # what exists — but the detail endpoint withholds the content.
                is_locked=problem.is_premium
                and not can_access_all
                and not detail.is_free_preview,
            )
            for problem, detail in rows
        ]
        return summaries, int(total or 0)

    async def get_problem(
        self, slug: str, *, entitlements: Entitlements
    ) -> HldProblemDetailOut:
        row = (
            await self.db.execute(
                select(Problem, HldProblemDetail)
                .join(HldProblemDetail, HldProblemDetail.problem_id == Problem.id)
                .where(Problem.slug == slug, Problem.is_published.is_(True))
            )
        ).first()

        if row is None:
            raise NotFoundError("Problem not found")

        problem, detail = row
        locked = (
            problem.is_premium
            and not entitlements.allows("can_access_full_study_guides")
            and not detail.is_free_preview
        )

        out = HldProblemDetailOut(
            id=problem.id,
            slug=problem.slug,
            title=problem.title,
            difficulty=problem.difficulty,
            description_md=problem.description_md,
            functional_requirements=detail.functional_requirements,
            non_functional_requirements=detail.non_functional_requirements,
            estimated_minutes=detail.estimated_minutes,
            tags=problem.tags,
            companies=problem.companies,
            is_locked=locked,
        )

        # The statement and requirements are always visible — a user must be
        # able to attempt the problem. Only the worked solution is gated, and
        # gated fields are omitted rather than blanked.
        if not locked:
            out.study_guide_md = problem.study_guide_md
            out.capacity_estimation = detail.capacity_estimation  # type: ignore[assignment]
            out.api_design_md = detail.api_design_md
            out.data_model_md = detail.data_model_md
            out.architecture_md = detail.architecture_md
            out.scaling_md = detail.scaling_md
            out.tradeoffs_md = detail.tradeoffs_md

        return out

    async def list_components(self) -> list[ComponentCatalogEntry]:
        rows = await self.db.scalars(
            select(ComponentCatalogEntry).order_by(
                ComponentCatalogEntry.category, ComponentCatalogEntry.order_index
            )
        )
        return list(rows)

    # --- Workspace ----------------------------------------------------------

    async def get_or_create_workspace(
        self, *, user_id: uuid.UUID, problem_slug: str
    ) -> SystemDesignWorkspace:
        problem = await self.db.scalar(select(Problem).where(Problem.slug == problem_slug))
        if problem is None:
            raise NotFoundError("Problem not found")

        workspace = await self.db.scalar(
            select(SystemDesignWorkspace).where(
                SystemDesignWorkspace.user_id == user_id,
                SystemDesignWorkspace.problem_id == problem.id,
            )
        )
        if workspace is None:
            workspace = SystemDesignWorkspace(
                user_id=user_id,
                problem_id=problem.id,
                title=problem.title,
                nodes=[],
                edges=[],
            )
            self.db.add(workspace)
            await self.db.flush()
        return workspace

    async def save_workspace(
        self, workspace_id: uuid.UUID, payload: WorkspaceSaveRequest, *, user_id: uuid.UUID
    ) -> SystemDesignWorkspace:
        workspace = await self._owned_workspace(workspace_id, user_id)

        # Optimistic concurrency: two browser tabs on the same canvas would
        # otherwise silently overwrite each other on autosave.
        if payload.expected_version is not None and payload.expected_version != workspace.version:
            raise ConflictError(
                "This design was modified in another session",
                details={"expected": payload.expected_version, "current": workspace.version},
            )

        workspace.nodes = [n.model_dump() for n in payload.nodes]
        workspace.edges = [e.model_dump() for e in payload.edges]
        workspace.candidate_notes_md = payload.candidate_notes_md
        workspace.version += 1
        return workspace

    async def create_share_link(
        self, workspace_id: uuid.UUID, *, user_id: uuid.UUID, entitlements: Entitlements
    ) -> str:
        if not entitlements.allows("can_access_premium_problems"):
            raise PremiumRequiredError(
                "Sharing saved designs requires an upgraded plan",
                required_tier="premium",
                feature="can_access_premium_problems",
            )
        workspace = await self._owned_workspace(workspace_id, user_id)
        if workspace.share_slug is None:
            workspace.share_slug = secrets.token_urlsafe(12)
        return workspace.share_slug

    # --- Review -------------------------------------------------------------

    async def review_workspace(
        self,
        workspace_id: uuid.UUID,
        *,
        user_id: uuid.UUID,
        entitlements: Entitlements,
        reviewer: DesignReviewService,
    ) -> SystemDesignReview:
        workspace = await self._owned_workspace(workspace_id, user_id, load_problem=True)

        detail = await self.db.scalar(
            select(HldProblemDetail).where(HldProblemDetail.problem_id == workspace.problem_id)
        )

        submission = DesignSubmission(
            problem_title=workspace.problem.title,
            problem_statement=workspace.problem.description_md,
            functional_requirements=detail.functional_requirements if detail else [],
            non_functional_requirements=detail.non_functional_requirements if detail else [],
            components=[f"{n.get('label')} ({n.get('kind')})" for n in workspace.nodes],
            connections=self._describe_edges(workspace),
            candidate_notes=workspace.candidate_notes_md,
        )

        result = await reviewer.review(
            submission, entitlements=entitlements, user_id=user_id
        )

        review = SystemDesignReview(
            workspace_id=workspace.id,
            user_id=user_id,
            workspace_version=workspace.version,
            overall_score=result.review.overall_score,
            payload=result.review.model_dump(mode="json"),
            model_id=result.model_id,
            prompt_version=result.prompt_version,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )
        self.db.add(review)
        await self.db.flush()
        return review

    @staticmethod
    def _describe_edges(workspace: SystemDesignWorkspace) -> list[str]:
        """Render edges as readable arrows using node labels, not raw ids.

        The model sees "API Gateway -> Redis", which it can reason about;
        "n3 -> n7" would be meaningless to it.
        """
        labels = {n.get("id"): n.get("label") for n in workspace.nodes}
        described: list[str] = []
        for edge in workspace.edges:
            source = labels.get(edge.get("source"), edge.get("source"))
            target = labels.get(edge.get("target"), edge.get("target"))
            arrow = f"{source} -> {target}"
            if edge.get("label"):
                arrow += f" [{edge['label']}]"
            described.append(arrow)
        return described

    async def _owned_workspace(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID, *, load_problem: bool = False
    ) -> SystemDesignWorkspace:
        stmt = select(SystemDesignWorkspace).where(SystemDesignWorkspace.id == workspace_id)
        if load_problem:
            stmt = stmt.options(selectinload(SystemDesignWorkspace.problem))
        workspace = await self.db.scalar(stmt)

        # Same error for missing and not-owned: a 403 would confirm the id exists.
        if workspace is None or workspace.user_id != user_id:
            raise NotFoundError("Workspace not found")
        return workspace
