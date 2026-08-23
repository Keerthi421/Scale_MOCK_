"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CheckCircle2, Clock, Lock, Search } from "lucide-react";
import { api } from "@/lib/api";
import { DEMO_PROBLEMS } from "@/lib/demo";
import type { ProblemSummary } from "@/lib/types";

const TIERS = [25, 75, 150] as const;

const DIFFICULTY_STYLE: Record<string, string> = {
  easy: "text-[var(--color-success)]",
  medium: "text-[var(--color-warning)]",
  hard: "text-[var(--color-danger)]",
};

export default function ProblemSheetPage() {
  const [problems, setProblems] = useState<ProblemSummary[]>([]);
  const [tier, setTier] = useState<number>(25);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    api
      .listProblems({ sheet_tier: tier, search: query || undefined })
      .then((page) => {
        if (cancelled) return;
        setProblems(page.items);
        setOffline(false);
      })
      .catch(() => {
        if (cancelled) return;
        setProblems(DEMO_PROBLEMS);
        setOffline(true);
      })
      .finally(() => !cancelled && setLoading(false));

    return () => {
      cancelled = true;
    };
  }, [tier, query]);

  const solved = problems.filter((p) => p.is_solved).length;

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-4xl px-6 py-10">
        <header className="mb-8">
          <div className="mb-1 font-mono text-[11px] text-[var(--color-text-faint)]">
            ⌁ InterviewForge
          </div>
          <h1 className="text-2xl font-semibold text-[var(--color-text)]">
            System Design Sheet
          </h1>
          <p className="mt-1.5 max-w-xl text-sm leading-relaxed text-[var(--color-text-muted)]">
            Work through each problem on the architecture canvas, then get an AI
            review of what you drew. Progress is saved to your account, not your
            browser.
          </p>
        </header>

        <div className="mb-5 flex flex-wrap items-center gap-3">
          <div className="flex rounded border border-[var(--color-border)] p-0.5">
            {TIERS.map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setTier(t)}
                className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
                  tier === t
                    ? "bg-[var(--color-accent)] text-[#1a1005]"
                    : "text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
                }`}
              >
                {t}
              </button>
            ))}
          </div>

          <div className="relative flex-1 sm:max-w-xs">
            <Search
              size={14}
              className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--color-text-faint)]"
            />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search problems…"
              className="w-full rounded border border-[var(--color-border)] bg-[var(--color-surface)] py-1.5 pl-8 pr-2.5 text-sm outline-none placeholder:text-[var(--color-text-faint)] focus:border-[var(--color-accent)]"
            />
          </div>

          <div className="ml-auto font-mono text-xs text-[var(--color-text-faint)]">
            {solved} / {problems.length} solved
          </div>
        </div>

        {offline ? (
          <div className="mb-5 rounded border border-[var(--color-warning)] bg-[var(--color-surface)] px-3 py-2 text-[12px] text-[var(--color-warning)]">
            API unreachable — showing bundled sample problems. Start the backend
            to load the full sheet and save your work.
          </div>
        ) : null}

        {loading ? (
          <div className="space-y-2">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="h-[68px] animate-pulse rounded border border-[var(--color-border)] bg-[var(--color-surface)]"
              />
            ))}
          </div>
        ) : problems.length === 0 ? (
          <p className="py-16 text-center text-sm text-[var(--color-text-faint)]">
            No problems match your filters.
          </p>
        ) : (
          <ul className="space-y-2">
            {problems.map((problem, index) => (
              <li key={problem.id}>
                <Link
                  href={`/system-design/${problem.slug}`}
                  className="group flex items-center gap-4 rounded border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 transition-colors hover:border-[var(--color-border-strong)] hover:bg-[var(--color-surface-raised)]"
                >
                  <span className="w-6 shrink-0 font-mono text-xs text-[var(--color-text-faint)]">
                    {String(index + 1).padStart(2, "0")}
                  </span>

                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <h2 className="truncate text-[14px] font-medium text-[var(--color-text)]">
                        {problem.title}
                      </h2>
                      {problem.is_solved ? (
                        <CheckCircle2 size={13} className="shrink-0 text-[var(--color-success)]" />
                      ) : null}
                      {problem.is_locked ? (
                        <Lock size={12} className="shrink-0 text-[var(--color-text-faint)]" />
                      ) : null}
                    </div>
                    <p className="mt-0.5 truncate text-[12.5px] text-[var(--color-text-muted)]">
                      {problem.summary}
                    </p>
                  </div>

                  <div className="hidden shrink-0 items-center gap-3 sm:flex">
                    <span className="flex items-center gap-1 text-[11px] text-[var(--color-text-faint)]">
                      <Clock size={11} />
                      {problem.estimated_minutes}m
                    </span>
                    <span
                      className={`w-14 text-right text-[11px] font-medium capitalize ${DIFFICULTY_STYLE[problem.difficulty]}`}
                    >
                      {problem.difficulty}
                    </span>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
