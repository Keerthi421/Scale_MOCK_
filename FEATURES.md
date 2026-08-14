# InterviewForge — Feature Specification

Derived from competitive research (scalemock.com, Aug 2026) plus the reference
screenshot of their HLD interview surface. This documents the **feature set and
product category** to match or beat. No branding, copy, personas, illustrations,
or code are taken from the reference — all content here is to be authored
originally.

Deployment context: **personal use first.** Billing is built but not on the
critical path; the tier gate is real and server-side, and the owner account is
granted PRO directly.

---

## 1. Content library

| Area | Target | Notes |
|---|---|---|
| HLD problems | 150 | Switchable **25 / 75 / 150** sheet tiers |
| LLD problems | 150 | Java, C++, Python workspace |
| DSA problems | 500 target, 50 to start | Company-tagged, editorial + complexity analysis |
| Online Assessments | 125+ | Timed, mixed MCQ + coding |
| Frontend challenges | 100+ | Live-preview machine coding |
| CS fundamentals | 100+ MCQs | OS, DBMS, OOP, Networks |
| Companies | Top 50 | Company-wise DSA + readiness score |

**Sheet tiers** are the organizing idea worth copying structurally: one curated
ordered list, sliceable at 25/75/150, with per-sheet progress. Implemented as
`Problem.order_index` + a sheet-size filter, not three duplicate datasets.

## 2. AI mock interview (flagship)

Three-pane layout, from the reference screenshot:

- **Left — requirements panel.** Problem statement, functional requirements,
  non-functional requirements (availability, scalability, performance).
- **Center — architecture canvas.** Drag-and-drop React Flow. Component palette:
  Client, DNS, CDN, Load Balancer, API Gateway, Nginx, Server, Microservice,
  Custom. Zoom in/out, fit-to-view, lock. Whiteboard/freeform mode.
- **Right — AI interviewer.** Named persona with role + company archetype
  (originally authored, not theirs), avatar, live speaking indicator, streaming
  transcript.

Session chrome: elapsed timer, mic mute, speaker mute, End Session, theme toggle,
optional webcam picture-in-picture.

Interview types: **DSA**, **HLD**, **LLD**.
Config at start: difficulty, company style, duration, topic.

Interviewer behavior contract:
1. Introduce, state rules
2. Ask the question, invite scoping questions
3. Probe reasoning; challenge assumptions
4. Hint only when the candidate is genuinely stuck (hints are budgeted and logged)
5. Steer toward missed rubric points near the end
6. Close and evaluate

Voice pipeline: mic → STT → streaming LLM → TTS. Text-only fallback must always
work; voice is an enhancement, never a hard dependency.

**Improvement over reference:** rubric is DB-backed and versioned
(`problem_rubrics`), and every interview pins `model_id` + `prompt_version` +
`rubric_version` so scores stay comparable across model changes.

## 3. AI evaluation report

Overall score plus weighted dimensions: communication, approach, trade-offs,
edge cases, time management, technical depth. Strengths, weaknesses,
recommendations, full transcript, per-question breakdown, score timeline,
recommended follow-up problems.

## 4. AI design review

Submit an architecture; receive a structured report: architecture score,
scalability, availability, consistency, database choice, caching, queueing,
load balancing, fault tolerance, security, observability, bottlenecks, missing
components, trade-offs, alternative architecture. Structured JSON internally,
rendered as a report.

## 5. Code workspace

Monaco. Python, Java, C++, JavaScript, TypeScript. Run / Submit / Reset,
visible + hidden test cases, console, submission history, runtime + memory,
AI complexity analysis, AI code review, progressive hints (Hint 1 → 2 → 3 →
Solution — never jump straight to the answer).

## 6. Courses

Course → Module → Chapter → Lesson → Quiz. Per-lesson progress %, resume where
you left off, time spent, quiz scores. HLD and LLD tracks.

## 7. Progress and analytics

Dashboard: daily goal, continue-learning, readiness score with per-area
breakdown, AI recommendations from weak areas, target-company selection,
contribution heatmap, recent activity. Analytics: problems solved, accuracy,
average solve time, mock scores, topic performance, company readiness, weekly
activity, course progress, automatic weak-area detection.

## 8. Community

Global leaderboard, per-problem discussion threads with upvotes and spoiler
collapsing, public profiles with stats and achievements.

## 9. Tiers

Reference tiers for comparison: Free gives first 15 HLD, first 15 LLD, 9 OAs,
9 frontend, 1 AI mock per type, partial courses. Premium unlocks the full
library and unlimited mocks.

InterviewForge tiers (see `app/core/entitlements.py` — authoritative):

| | Free | Premium | Pro |
|---|---|---|---|
| Problems | 10 | Unlimited | Unlimited |
| AI mocks | 2/week | Unlimited | Unlimited |
| Full study guides | — | Yes | Yes |
| Advanced analytics | — | Yes | Yes |
| Company guides | — | — | Yes |
| Resume review | — | — | Yes |
| Mentoring | — | — | Yes |

## 10. Where this beats the reference

1. **Cloud-persisted progress.** Their FAQ states progress lives in the browser
   and does not sync across devices. Ours is Postgres-backed and device-agnostic.
2. **Versioned rubrics + pinned model/prompt** per interview, so scores are
   comparable over time rather than drifting silently with model updates.
3. **Server-side entitlement resolution** with independent expiry re-check, so a
   missed billing webhook degrades safely instead of granting free access.
4. **Replay-detecting auth** (rotating refresh-token families) rather than
   long-lived tokens.
