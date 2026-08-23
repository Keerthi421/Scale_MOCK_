"use client";

import { useState } from "react";
import { ChevronDown, Clock, Lock } from "lucide-react";
import type { ProblemDetail } from "@/lib/types";

function Section({
  title,
  defaultOpen = true,
  children,
}: {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section className="border-b border-[var(--color-border)]">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between px-4 py-2.5 text-left"
      >
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-faint)]">
          {title}
        </h3>
        <ChevronDown
          size={14}
          className={`text-[var(--color-text-faint)] transition-transform ${open ? "" : "-rotate-90"}`}
        />
      </button>
      {open ? <div className="px-4 pb-4">{children}</div> : null}
    </section>
  );
}

const DIFFICULTY_STYLE: Record<string, string> = {
  easy: "text-[var(--color-success)] border-[var(--color-success)]",
  medium: "text-[var(--color-warning)] border-[var(--color-warning)]",
  hard: "text-[var(--color-danger)] border-[var(--color-danger)]",
};

export function RequirementsPanel({ problem }: { problem: ProblemDetail }) {
  return (
    <aside className="flex h-full w-[340px] shrink-0 flex-col overflow-y-auto border-r border-[var(--color-border)] bg-[var(--color-surface)]">
      <header className="border-b border-[var(--color-border)] px-4 py-3">
        <div className="mb-1.5 flex items-center gap-2">
          <span
            className={`rounded border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${DIFFICULTY_STYLE[problem.difficulty]}`}
          >
            {problem.difficulty}
          </span>
          <span className="flex items-center gap-1 text-[11px] text-[var(--color-text-faint)]">
            <Clock size={11} />
            {problem.estimated_minutes} min
          </span>
        </div>
        <h1 className="text-base font-semibold leading-tight text-[var(--color-text)]">
          {problem.title}
        </h1>
        <div className="mt-2 flex flex-wrap gap-1">
          {problem.companies.map((c) => (
            <span
              key={c}
              className="rounded bg-[var(--color-surface-raised)] px-1.5 py-0.5 text-[10px] text-[var(--color-text-muted)]"
            >
              {c}
            </span>
          ))}
        </div>
      </header>

      <Section title="Problem">
        <div className="space-y-2 text-[13px] leading-relaxed text-[var(--color-text-muted)]">
          {problem.description_md.split("\n\n").map((p, i) => (
            <p key={i}>{p}</p>
          ))}
        </div>
      </Section>

      <Section title="Functional Requirements">
        <ul className="space-y-1.5">
          {problem.functional_requirements.map((r, i) => (
            <li key={i} className="flex gap-2 text-[13px] leading-snug text-[var(--color-text-muted)]">
              <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-[var(--color-success)]" />
              {r}
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Non-Functional Requirements">
        <ul className="space-y-1.5">
          {problem.non_functional_requirements.map((r, i) => (
            <li key={i} className="flex gap-2 text-[13px] leading-snug text-[var(--color-text-muted)]">
              <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-[var(--color-info)]" />
              {r}
            </li>
          ))}
        </ul>
      </Section>

      {problem.capacity_estimation?.length ? (
        <Section title="Capacity Estimation" defaultOpen={false}>
          <div className="space-y-3">
            {problem.capacity_estimation.map((row, i) => (
              <div key={i} className="rounded border border-[var(--color-border)] p-2.5">
                <div className="text-[12px] font-medium text-[var(--color-text)]">
                  {row.metric}
                </div>
                <div className="mt-1 text-[11px] text-[var(--color-text-faint)]">
                  {row.assumption}
                </div>
                {/* The arithmetic is shown, not just the answer — reproducing
                    the working is what the interview actually asks for. */}
                <code className="mt-1.5 block font-mono text-[11px] leading-relaxed text-[var(--color-text-muted)]">
                  {row.working}
                </code>
                <div className="mt-1 text-[12px] font-medium text-[var(--color-accent)]">
                  {row.result}
                </div>
              </div>
            ))}
          </div>
        </Section>
      ) : null}

      {problem.is_locked ? (
        <div className="m-4 rounded border border-[var(--color-border-strong)] bg-[var(--color-surface-raised)] p-3">
          <div className="mb-1 flex items-center gap-1.5 text-[12px] font-medium text-[var(--color-text)]">
            <Lock size={12} />
            Worked solution is Premium
          </div>
          <p className="text-[11px] leading-relaxed text-[var(--color-text-muted)]">
            The problem and requirements stay open so you can attempt it. The
            reference architecture, data model, and trade-off analysis unlock
            with Premium.
          </p>
        </div>
      ) : null}
    </aside>
  );
}
