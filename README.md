# Scale_MOCK_ — InterviewForge

An AI-first SDE interview preparation platform: DSA, High-Level Design,
Low-Level Design, machine coding, frontend challenges, online assessments,
CS fundamentals, and voice-driven AI mock interviews in one workspace.

> Status: **Phase 1 in progress.** Backend spine (config, models, auth,
> entitlements) is implemented and verified. Database migrations and the
> frontend are not yet built.

## Stack

**Backend** — FastAPI, Python 3.12, SQLAlchemy 2.0 (async) + asyncpg, Alembic,
PostgreSQL, Redis, ARQ, Anthropic Claude API, Stripe.
**Frontend** (planned) — Next.js 15, TypeScript, Tailwind, shadcn/ui, Monaco,
React Flow, Zustand.

## What works today

- Argon2id password hashing, JWT access tokens, and **rotating refresh tokens
  with replay detection** — presenting a revoked token revokes its whole family.
- **Server-side entitlement resolution** (`app/core/entitlements.py`). Every
  premium check resolves here; the client never decides access, and a lapsed
  subscription degrades to free even if a billing webhook was missed.
- 18-table schema covering users, subscriptions, problems, test cases, rubrics,
  mock interviews, transcripts, evaluations, submissions, progress, activity
  heatmap, and discussions.
- Endpoints: signup, login, refresh, logout, logout-all, me, me/entitlements.
- Sliding-window Redis rate limiting, structured error envelopes, request timing.

## Getting started

Requires Python 3.12+, [uv](https://github.com/astral-sh/uv), and Docker.

```bash
docker compose up -d
```

```bash
cd backend && uv venv && uv pip install -e ".[dev]"
```

Copy `backend/.env.example` to `backend/.env` and set `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Then run the API:

```bash
cd backend && ./.venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

Interactive docs at `http://localhost:8000/docs`.

## Layout

```
backend/app/
  core/          config, security, entitlements, exceptions, redis
  models/        SQLAlchemy models (18 tables)
  schemas/       Pydantic request/response models
  services/      business logic — never in route handlers
  api/v1/        HTTP routes
  ai/            AIProvider abstraction + prompts (Phase 2)
  workers/       ARQ background jobs
```

Business logic lives in `services/`, not in routes or models. Route handlers
validate, delegate, and serialize.

## Content sourcing

Problem statements are originally authored. Where external data is used it must
be appropriately licensed with attribution (e.g. CodeContests, MBPP, HumanEval,
System Design Primer). No content is copied from other interview-prep platforms.
See [FEATURES.md](FEATURES.md).

## License

Not yet licensed. All rights reserved.
