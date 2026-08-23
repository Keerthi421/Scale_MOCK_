"use client";

import { AlertTriangle, CheckCircle2, Info, X } from "lucide-react";
import type { DesignReviewPayload } from "@/lib/types";

const SEVERITY = {
  critical: { color: "var(--color-danger)", Icon: AlertTriangle, label: "Critical" },
  major: { color: "var(--color-warning)", Icon: AlertTriangle, label: "Major" },
  minor: { color: "var(--color-info)", Icon: Info, label: "Minor" },
} as const;

function scoreColor(score: number): string {
  if (score >= 75) return "var(--color-success)";
  if (score >= 50) return "var(--color-warning)";
  return "var(--color-danger)";
}

export function ReviewPanel({
  review,
  onClose,
}: {
  review: DesignReviewPayload;
  onClose: () => void;
}) {
  return (
    <aside className="flex h-full w-[400px] shrink-0 flex-col overflow-y-auto border-l border-[var(--color-border)] bg-[var(--color-surface)]">
      <header className="sticky top-0 flex items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3">
        <h2 className="text-sm font-semibold text-[var(--color-text)]">Design Review</h2>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close review"
          className="rounded p-1 text-[var(--color-text-faint)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text)]"
        >
          <X size={15} />
        </button>
      </header>

      <div className="border-b border-[var(--color-border)] px-4 py-4">
        <div className="flex items-baseline gap-2">
          <span
            className="text-4xl font-bold tabular-nums"
            style={{ color: scoreColor(review.overall_score) }}
          >
            {Math.round(review.overall_score)}
          </span>
          <span className="text-sm text-[var(--color-text-faint)]">/ 100</span>
        </div>
        <div className="mt-3 space-y-2 text-[13px] leading-relaxed text-[var(--color-text-muted)]">
          {review.summary_md.split("\n\n").map((p, i) => (
            <p key={i}>{p}</p>
          ))}
        </div>
      </div>

      {review.dimension_scores.length ? (
        <section className="border-b border-[var(--color-border)] px-4 py-3">
          <h3 className="mb-2.5 text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-faint)]">
            By Dimension
          </h3>
          <div className="space-y-2.5">
            {review.dimension_scores.map((d) => (
              <div key={d.dimension}>
                <div className="mb-1 flex items-center justify-between">
                  <span className="text-[12px] capitalize text-[var(--color-text-muted)]">
                    {d.dimension.replace(/_/g, " ")}
                  </span>
                  <span
                    className="font-mono text-[11px] tabular-nums"
                    style={{ color: scoreColor(d.score) }}
                  >
                    {Math.round(d.score)}
                  </span>
                </div>
                <div className="h-1 overflow-hidden rounded-full bg-[var(--color-surface-raised)]">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{ width: `${d.score}%`, background: scoreColor(d.score) }}
                  />
                </div>
                <p className="mt-1 text-[11px] leading-snug text-[var(--color-text-faint)]">
                  {d.rationale}
                </p>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {review.issues.length ? (
        <section className="border-b border-[var(--color-border)] px-4 py-3">
          <h3 className="mb-2.5 text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-faint)]">
            Issues ({review.issues.length})
          </h3>
          <div className="space-y-2.5">
            {review.issues.map((issue, i) => {
              const meta = SEVERITY[issue.severity];
              return (
                <div
                  key={i}
                  className="rounded border-l-2 bg-[var(--color-surface-raised)] p-2.5"
                  style={{ borderLeftColor: meta.color }}
                >
                  <div className="flex items-center gap-1.5">
                    <meta.Icon size={12} style={{ color: meta.color }} />
                    <span
                      className="text-[10px] font-semibold uppercase tracking-wide"
                      style={{ color: meta.color }}
                    >
                      {meta.label}
                    </span>
                    {issue.component ? (
                      <span className="font-mono text-[10px] text-[var(--color-text-faint)]">
                        · {issue.component}
                      </span>
                    ) : null}
                  </div>
                  <div className="mt-1 text-[12.5px] font-medium text-[var(--color-text)]">
                    {issue.title}
                  </div>
                  <p className="mt-1 text-[11.5px] leading-snug text-[var(--color-text-muted)]">
                    {issue.explanation}
                  </p>
                  <p className="mt-1.5 border-t border-[var(--color-border)] pt-1.5 text-[11.5px] leading-snug text-[var(--color-accent)]">
                    {issue.recommendation}
                  </p>
                </div>
              );
            })}
          </div>
        </section>
      ) : null}

      {review.missing_components.length || review.bottlenecks.length ? (
        <section className="border-b border-[var(--color-border)] px-4 py-3">
          {review.missing_components.length ? (
            <>
              <h3 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-faint)]">
                Missing
              </h3>
              <ul className="mb-3 space-y-1">
                {review.missing_components.map((c, i) => (
                  <li key={i} className="text-[12px] text-[var(--color-text-muted)]">
                    · {c}
                  </li>
                ))}
              </ul>
            </>
          ) : null}
          {review.bottlenecks.length ? (
            <>
              <h3 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-faint)]">
                Bottlenecks
              </h3>
              <ul className="space-y-1">
                {review.bottlenecks.map((b, i) => (
                  <li key={i} className="text-[12px] text-[var(--color-text-muted)]">
                    · {b}
                  </li>
                ))}
              </ul>
            </>
          ) : null}
        </section>
      ) : null}

      {review.strengths.length ? (
        <section className="border-b border-[var(--color-border)] px-4 py-3">
          <h3 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-faint)]">
            Strengths
          </h3>
          <ul className="space-y-1">
            {review.strengths.map((s, i) => (
              <li
                key={i}
                className="flex gap-1.5 text-[12px] leading-snug text-[var(--color-text-muted)]"
              >
                <CheckCircle2
                  size={12}
                  className="mt-0.5 shrink-0 text-[var(--color-success)]"
                />
                {s}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {review.next_steps.length ? (
        <section className="px-4 py-3">
          <h3 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-faint)]">
            Next Steps
          </h3>
          <ol className="space-y-1.5">
            {review.next_steps.map((step, i) => (
              <li key={i} className="flex gap-2 text-[12px] leading-snug text-[var(--color-text-muted)]">
                <span className="font-mono text-[var(--color-accent)]">{i + 1}.</span>
                {step}
              </li>
            ))}
          </ol>
        </section>
      ) : null}
    </aside>
  );
}
