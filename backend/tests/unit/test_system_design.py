"""Canvas validation, edge rendering, and seed-content integrity."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.db.seed.components import COMPONENTS
from app.db.seed.hld_problems import HLD_PROBLEMS
from app.models.enums import NodeKind
from app.schemas.system_design import MAX_EDGES, MAX_NODES, CanvasPayload
from app.services.system_design_service import SHEET_TIERS, SystemDesignService


def _node(node_id: str, kind: NodeKind = NodeKind.APP_SERVER) -> dict[str, object]:
    return {"id": node_id, "kind": kind, "label": node_id.title(), "x": 0.0, "y": 0.0}


def _edge(edge_id: str, source: str, target: str) -> dict[str, object]:
    return {"id": edge_id, "source": source, "target": target}


# --- Canvas graph validation ------------------------------------------------


def test_valid_canvas_is_accepted() -> None:
    payload = CanvasPayload(
        nodes=[_node("client", NodeKind.CLIENT), _node("api")],
        edges=[_edge("e1", "client", "api")],
    )
    assert len(payload.nodes) == 2


def test_edge_to_missing_node_is_rejected() -> None:
    """A dangling edge renders as a line into empty space and reaches the
    reviewer as a connection that does not exist."""
    with pytest.raises(ValidationError, match="unknown target"):
        CanvasPayload(
            nodes=[_node("client", NodeKind.CLIENT)],
            edges=[_edge("e1", "client", "deleted-node")],
        )


def test_edge_from_missing_node_is_rejected() -> None:
    with pytest.raises(ValidationError, match="unknown source"):
        CanvasPayload(nodes=[_node("api")], edges=[_edge("e1", "ghost", "api")])


def test_self_loop_is_rejected() -> None:
    with pytest.raises(ValidationError, match="connects a node to itself"):
        CanvasPayload(nodes=[_node("api")], edges=[_edge("e1", "api", "api")])


def test_duplicate_node_ids_are_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicate node ids"):
        CanvasPayload(nodes=[_node("api"), _node("api")], edges=[])


def test_empty_canvas_is_valid() -> None:
    """A blank canvas must save — users open a workspace before drawing."""
    payload = CanvasPayload(nodes=[], edges=[])
    assert payload.nodes == []


def test_node_cap_is_enforced() -> None:
    with pytest.raises(ValidationError):
        CanvasPayload(nodes=[_node(f"n{i}") for i in range(MAX_NODES + 1)], edges=[])


def test_edge_cap_is_enforced() -> None:
    nodes = [_node("a"), _node("b")]
    with pytest.raises(ValidationError):
        CanvasPayload(
            nodes=nodes,
            edges=[_edge(f"e{i}", "a", "b") for i in range(MAX_EDGES + 1)],
        )


# --- Edge rendering for the reviewer ---------------------------------------


def test_edges_are_described_with_labels_not_ids() -> None:
    """The model must see 'API Gateway -> Cache'; 'n3 -> n7' is meaningless."""

    class _FakeWorkspace:
        nodes = [
            {"id": "n1", "label": "API Gateway"},
            {"id": "n2", "label": "Cache"},
        ]
        edges = [{"id": "e1", "source": "n1", "target": "n2", "label": "read-through"}]

    described = SystemDesignService._describe_edges(_FakeWorkspace)  # type: ignore[arg-type]
    assert described == ["API Gateway -> Cache [read-through]"]


def test_edge_description_survives_a_missing_label() -> None:
    class _FakeWorkspace:
        nodes = [{"id": "n1", "label": "Client"}]
        edges = [{"id": "e1", "source": "n1", "target": "n9"}]

    described = SystemDesignService._describe_edges(_FakeWorkspace)  # type: ignore[arg-type]
    assert described == ["Client -> n9"]


# --- Seed content integrity -------------------------------------------------


def test_problem_slugs_are_unique() -> None:
    slugs = [p["slug"] for p in HLD_PROBLEMS]
    assert len(slugs) == len(set(slugs))


def test_problem_order_indexes_are_unique() -> None:
    """Ordering drives the sheet; duplicates make list order non-deterministic."""
    orders = [p["order_index"] for p in HLD_PROBLEMS]
    assert len(orders) == len(set(orders))


def test_sheet_tiers_are_valid() -> None:
    for problem in HLD_PROBLEMS:
        assert problem["sheet_tier"] in SHEET_TIERS, problem["slug"]


def test_expected_components_are_real_palette_entries() -> None:
    """A problem expecting a component the palette lacks means a candidate is
    graded against something they could not place."""
    palette = {kind for kind, *_ in COMPONENTS}
    for problem in HLD_PROBLEMS:
        for component in problem["expected_components"]:
            assert component in palette, f"{problem['slug']} expects unplaceable {component}"


def test_capacity_rows_are_complete() -> None:
    required = {"metric", "assumption", "working", "result"}
    for problem in HLD_PROBLEMS:
        for row in problem["capacity_estimation"]:
            assert required <= row.keys(), f"{problem['slug']} capacity row missing keys"


def test_every_problem_has_requirements() -> None:
    for problem in HLD_PROBLEMS:
        assert problem["functional_requirements"], problem["slug"]
        assert problem["non_functional_requirements"], problem["slug"]


def test_free_preview_problems_exist() -> None:
    """Free tier needs a real entry point, or the sheet is a wall of locks."""
    assert any(p["is_free_preview"] for p in HLD_PROBLEMS)


def test_palette_kinds_are_unique_and_cover_the_enum() -> None:
    kinds = [kind for kind, *_ in COMPONENTS]
    assert len(kinds) == len(set(kinds))
    # Every NodeKind must be placeable, or a saved canvas could hold a kind the
    # palette cannot render.
    assert set(kinds) == set(NodeKind)
