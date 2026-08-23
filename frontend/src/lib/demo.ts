import type { ProblemDetail, ProblemSummary } from "./types";

/**
 * Offline fallback content.
 *
 * The backend is the source of truth, but it needs Postgres. Until the
 * database is provisioned, the canvas would otherwise be unreachable — and a
 * practice tool you cannot open is worse than one with placeholder content.
 * These mirror the first two seeded problems in
 * `backend/app/db/seed/hld_problems.py`; delete this module once the API is
 * reliably up.
 */
export const DEMO_PROBLEMS: ProblemSummary[] = [
  {
    id: "demo-1",
    slug: "design-a-url-shortener",
    title: "Design a URL Shortener",
    summary: "Map long URLs to short codes and redirect at scale.",
    difficulty: "easy",
    tags: ["hashing", "key-value", "caching", "read-heavy"],
    companies: ["Amazon", "Google", "Microsoft"],
    estimated_minutes: 35,
    sheet_tier: 25,
    is_premium: false,
    is_solved: false,
    is_locked: false,
  },
  {
    id: "demo-2",
    slug: "design-a-rate-limiter",
    title: "Design a Distributed Rate Limiter",
    summary: "Cap per-client request rates across a fleet of servers.",
    difficulty: "medium",
    tags: ["algorithms", "redis", "concurrency"],
    companies: ["Stripe", "Cloudflare", "Amazon"],
    estimated_minutes: 40,
    sheet_tier: 25,
    is_premium: false,
    is_solved: false,
    is_locked: false,
  },
  {
    id: "demo-3",
    slug: "design-a-news-feed",
    title: "Design a News Feed",
    summary: "Build and serve a personalized timeline at social-network scale.",
    difficulty: "hard",
    tags: ["fanout", "caching", "ranking"],
    companies: ["Meta", "Twitter", "LinkedIn"],
    estimated_minutes: 50,
    sheet_tier: 25,
    is_premium: true,
    is_solved: false,
    is_locked: true,
  },
];

const DETAILS: Record<string, ProblemDetail> = {
  "design-a-url-shortener": {
    id: "demo-1",
    slug: "design-a-url-shortener",
    title: "Design a URL Shortener",
    difficulty: "easy",
    description_md:
      "Design a service that turns a long URL into a short code and redirects visitors who follow it.\n\nThe interesting part is not generating the code — it is that reads outnumber writes by roughly two orders of magnitude, redirects must be fast enough to feel instant, and a code, once issued, can never be reused for a different URL.",
    functional_requirements: [
      "Given a long URL, return a short code.",
      "Given a short code, redirect to the original URL.",
      "Optionally accept a user-supplied custom alias.",
      "Optionally accept an expiry time, after which the code stops resolving.",
    ],
    non_functional_requirements: [
      "Redirect p99 latency under 100ms.",
      "Read:write ratio around 100:1.",
      "Codes must be unique and never recycled.",
      "Availability matters more than strong consistency on reads.",
    ],
    estimated_minutes: 35,
    tags: ["hashing", "key-value", "caching", "read-heavy"],
    companies: ["Amazon", "Google", "Microsoft"],
    is_locked: false,
    capacity_estimation: [
      {
        metric: "Write QPS",
        assumption: "100M new links per month",
        working: "100e6 / (30 x 86400) = ~39/sec; assume 3x peak",
        result: "~40/sec average, ~120/sec peak",
      },
      {
        metric: "Read QPS",
        assumption: "100:1 read:write ratio",
        working: "40 x 100 = 4,000/sec average",
        result: "~4K reads/sec",
      },
      {
        metric: "Storage (5 years)",
        assumption: "~500 bytes per record",
        working: "100e6 x 12 x 5 = 6e9 records x 500B",
        result: "~3TB before replication",
      },
    ],
  },
  "design-a-rate-limiter": {
    id: "demo-2",
    slug: "design-a-rate-limiter",
    title: "Design a Distributed Rate Limiter",
    difficulty: "medium",
    description_md:
      "Design a rate limiter that caps how many requests a client may make in a given window, enforced consistently across many application servers.\n\nThe hard part is that the counter is shared state on the hot path of every request. It has to be correct enough to actually limit abuse, and cheap enough that it does not become the bottleneck it was meant to prevent.",
    functional_requirements: [
      "Limit requests per client identifier (API key, user, or IP).",
      "Support different limits per endpoint and per plan tier.",
      "Return 429 with a Retry-After header when over the limit.",
      "Expose remaining quota via response headers.",
    ],
    non_functional_requirements: [
      "Adds under 5ms to request latency.",
      "Enforced consistently across all application servers.",
      "Must fail open — a limiter outage cannot take down the API.",
      "Memory proportional to active clients, not total clients.",
    ],
    estimated_minutes: 40,
    tags: ["algorithms", "redis", "concurrency"],
    companies: ["Stripe", "Cloudflare", "Amazon"],
    is_locked: false,
    capacity_estimation: [
      {
        metric: "Limiter QPS",
        assumption: "Every API request checks the limit; 50K API QPS",
        working: "50,000 checks/sec x 1-2 Redis ops",
        result: "~50-100K Redis ops/sec",
      },
      {
        metric: "Memory",
        assumption: "1M active clients, sliding log, ~100 entries each",
        working: "1e6 x 100 x ~16B",
        result: "~2GB",
      },
    ],
  },
};

export function demoDetail(slug: string): ProblemDetail | null {
  return DETAILS[slug] ?? null;
}
