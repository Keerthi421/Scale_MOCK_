"""Prompts for system-design review.

Prompts are versioned and live here rather than inline in services, so a change
is reviewable in a diff and every stored evaluation can record which version
produced it. Bump PROMPT_VERSION whenever wording changes in a way that could
move scores.
"""

from __future__ import annotations

from dataclasses import dataclass

PROMPT_VERSION = "design-review/v1"


@dataclass(frozen=True, slots=True)
class DesignSubmission:
    problem_title: str
    problem_statement: str
    functional_requirements: list[str]
    non_functional_requirements: list[str]
    # Flattened canvas: "Load Balancer -> Application Server" style edges plus
    # node labels, so the model sees topology rather than raw React Flow JSON.
    components: list[str]
    connections: list[str]
    candidate_notes: str | None = None


SYSTEM_PROMPT = """\
You are a staff-level engineer reviewing a system design an interview candidate \
produced. You have run design reviews for large-scale distributed systems and you \
grade the way a real interviewer does: on reasoning, not vocabulary.

How to judge:

Reward designs that meet the stated requirements at the stated scale. A simple \
design that satisfies the requirements is better than an elaborate one that adds \
components it does not need. Do not reward name-dropping technologies; a candidate \
who writes "Kafka" without saying what it decouples has not earned points for it.

Weigh problems by consequence. A missing replica in the primary datastore is a \
critical issue. An unspecified cache eviction policy is minor. Order issues by \
severity and be honest when a design is genuinely weak — an inflated score teaches \
the candidate nothing.

Ground every claim in what the design actually contains. If the candidate never \
estimated storage, say the estimate is absent rather than inventing one on their \
behalf. If a component's purpose is ambiguous, treat the ambiguity itself as the \
finding.

For each dimension, score against what this specific problem demands. A URL \
shortener that ignores strong consistency is fine; a payment ledger that does is \
not. Do not apply a generic checklist uniformly across problems.

Write for the candidate. Explanations should teach the underlying principle, and \
each recommendation should be concrete enough to act on."""


def build_review_prompt(submission: DesignSubmission) -> str:
    functional = "\n".join(f"- {r}" for r in submission.functional_requirements) or "- (none given)"
    non_functional = (
        "\n".join(f"- {r}" for r in submission.non_functional_requirements) or "- (none given)"
    )
    components = "\n".join(f"- {c}" for c in submission.components) or "- (no components placed)"
    connections = "\n".join(f"- {c}" for c in submission.connections) or "- (no connections drawn)"
    notes = submission.candidate_notes or "(the candidate left no written notes)"

    return f"""\
# Problem: {submission.problem_title}

{submission.problem_statement}

## Functional requirements
{functional}

## Non-functional requirements
{non_functional}

## The candidate's architecture

Components placed on the canvas:
{components}

Connections drawn between them:
{connections}

## The candidate's notes
{notes}

---

Review this design and return your assessment in the required JSON format. \
An empty or near-empty canvas should score low and say plainly what is missing — \
do not review a design that was never drawn as though it exists."""
