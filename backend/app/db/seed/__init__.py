"""Seed data loader.

Run with:  python -m app.db.seed

Idempotent by design — every row is matched on a natural key and updated in
place, so re-running after adding content is safe and is the normal way to
publish new problems.
"""

from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.seed.components import COMPONENTS
from app.db.seed.hld_problems import HLD_PROBLEMS
from app.db.session import SessionLocal
from app.models.enums import ProblemCategory
from app.models.problem import Problem
from app.models.system_design import ComponentCatalogEntry, HldProblemDetail


async def seed_components(db: AsyncSession) -> tuple[int, int]:
    created = updated = 0
    for order, (kind, label, category, icon, description) in enumerate(COMPONENTS):
        entry = await db.scalar(
            select(ComponentCatalogEntry).where(ComponentCatalogEntry.kind == kind)
        )
        if entry is None:
            db.add(
                ComponentCatalogEntry(
                    kind=kind,
                    label=label,
                    category=category,
                    icon=icon,
                    description=description,
                    order_index=order,
                )
            )
            created += 1
        else:
            entry.label = label
            entry.category = category
            entry.icon = icon
            entry.description = description
            entry.order_index = order
            updated += 1
    return created, updated


def _build_guide(spec: dict[str, Any]) -> str:
    """Assemble the long-form guide from its sections.

    Stored pre-rendered on `problems.study_guide_md` so the problem page needs
    one read rather than stitching sections together on every request.
    """
    sections = [
        ("Architecture", spec.get("architecture_md")),
        ("API design", spec.get("api_design_md")),
        ("Data model", spec.get("data_model_md")),
        ("Scaling", spec.get("scaling_md")),
        ("Tradeoffs", spec.get("tradeoffs_md")),
    ]
    return "\n\n".join(f"## {title}\n\n{body}" for title, body in sections if body)


async def seed_hld_problems(db: AsyncSession) -> tuple[int, int]:
    created = updated = 0
    for spec in HLD_PROBLEMS:
        problem = await db.scalar(select(Problem).where(Problem.slug == spec["slug"]))

        if problem is None:
            problem = Problem(slug=spec["slug"], category=ProblemCategory.HLD)
            db.add(problem)
            created += 1
        else:
            updated += 1

        problem.title = spec["title"]
        problem.difficulty = spec["difficulty"]
        problem.summary = spec["summary"]
        problem.description_md = spec["description_md"]
        problem.study_guide_md = _build_guide(spec)
        problem.tags = spec["tags"]
        problem.companies = spec["companies"]
        problem.order_index = spec["order_index"]
        problem.is_published = True
        # Free-preview problems are the funnel; everything else is gated.
        problem.is_premium = not spec["is_free_preview"]

        await db.flush()

        detail = await db.scalar(
            select(HldProblemDetail).where(HldProblemDetail.problem_id == problem.id)
        )
        if detail is None:
            detail = HldProblemDetail(problem_id=problem.id)
            db.add(detail)

        detail.functional_requirements = spec["functional_requirements"]
        detail.non_functional_requirements = spec["non_functional_requirements"]
        detail.capacity_estimation = spec["capacity_estimation"]
        detail.api_design_md = spec.get("api_design_md")
        detail.data_model_md = spec.get("data_model_md")
        detail.architecture_md = spec.get("architecture_md")
        detail.scaling_md = spec.get("scaling_md")
        detail.tradeoffs_md = spec.get("tradeoffs_md")
        detail.expected_components = [c.value for c in spec["expected_components"]]
        detail.sheet_tier = spec["sheet_tier"]
        detail.estimated_minutes = spec["estimated_minutes"]
        detail.is_free_preview = spec["is_free_preview"]

    return created, updated


async def run() -> None:
    async with SessionLocal() as db:
        c_created, c_updated = await seed_components(db)
        p_created, p_updated = await seed_hld_problems(db)
        await db.commit()

    print(f"components: {c_created} created, {c_updated} updated")
    print(f"hld problems: {p_created} created, {p_updated} updated")


if __name__ == "__main__":
    asyncio.run(run())
