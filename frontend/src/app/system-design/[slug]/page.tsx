"use client";

import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, WifiOff } from "lucide-react";
import { DesignCanvas } from "@/components/canvas/DesignCanvas";
import { RequirementsPanel } from "@/components/canvas/RequirementsPanel";
import { ReviewPanel } from "@/components/canvas/ReviewPanel";
import { ApiRequestError, api } from "@/lib/api";
import { demoDetail } from "@/lib/demo";
import { FALLBACK_PALETTE } from "@/lib/palette";
import type {
  DesignReviewPayload,
  PaletteComponent,
  ProblemDetail,
  SerializedEdge,
  SerializedNode,
  Workspace,
} from "@/lib/types";

export default function PracticePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = use(params);

  const [problem, setProblem] = useState<ProblemDetail | null>(null);
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [components, setComponents] = useState<PaletteComponent[]>(FALLBACK_PALETTE);
  const [review, setReview] = useState<DesignReviewPayload | null>(null);

  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(false);
  const [saving, setSaving] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      // The palette degrades independently: if only this call fails we still
      // have the bundled fallback, so the canvas stays usable.
      try {
        const palette = await api.listComponents();
        if (!cancelled && palette.length) setComponents(palette);
      } catch {
        /* fallback already in state */
      }

      try {
        const detail = await api.getProblem(slug);
        if (cancelled) return;
        setProblem(detail);

        // Opening a workspace requires auth. Without a session the canvas is
        // still usable as a scratchpad — it just cannot persist.
        try {
          const ws = await api.openWorkspace(slug);
          if (!cancelled) setWorkspace(ws);
        } catch {
          /* unauthenticated — scratchpad mode */
        }
      } catch {
        if (cancelled) return;
        const fallback = demoDetail(slug);
        setProblem(fallback);
        setOffline(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [slug]);

  // Guard against losing work on accidental navigation.
  useEffect(() => {
    if (!dirty) return;
    function warn(e: BeforeUnloadEvent) {
      e.preventDefault();
    }
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  const flash = useCallback((message: string) => {
    setToast(message);
    setTimeout(() => setToast(null), 4000);
  }, []);

  const handleSave = useCallback(
    async (nodes: SerializedNode[], edges: SerializedEdge[]) => {
      if (!workspace) {
        flash("Sign in to save this design. Your canvas is not persisted yet.");
        return;
      }
      setSaving(true);
      try {
        const updated = await api.saveWorkspace(workspace.id, {
          nodes,
          edges,
          candidate_notes_md: workspace.candidate_notes_md,
          expected_version: workspace.version,
        });
        setWorkspace(updated);
        flash("Saved.");
      } catch (error) {
        if (error instanceof ApiRequestError && error.isConflict) {
          flash("This design changed in another tab. Reload before saving again.");
        } else {
          flash(error instanceof Error ? error.message : "Save failed.");
        }
      } finally {
        setSaving(false);
      }
    },
    [workspace, flash],
  );

  const handleReview = useCallback(async () => {
    if (!workspace) {
      flash("Sign in to run an AI review.");
      return;
    }
    setReviewing(true);
    try {
      const result = await api.reviewWorkspace(workspace.id);
      setReview(result.payload);
    } catch (error) {
      if (error instanceof ApiRequestError && error.isPremiumRequired) {
        flash("AI design review is a Premium feature.");
      } else {
        flash(error instanceof Error ? error.message : "Review failed.");
      }
    } finally {
      setReviewing(false);
    }
  }, [workspace, flash]);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-[var(--color-text-faint)]">
        Loading…
      </div>
    );
  }

  if (!problem) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3">
        <p className="text-sm text-[var(--color-text-muted)]">
          Problem “{slug}” not found.
        </p>
        <Link href="/system-design" className="text-sm text-[var(--color-accent)] hover:underline">
          Back to problems
        </Link>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <nav className="flex shrink-0 items-center gap-3 border-b border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2">
        <Link
          href="/system-design"
          className="flex items-center gap-1.5 text-[13px] text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
        >
          <ArrowLeft size={14} />
          Problems
        </Link>
        <span className="font-mono text-[11px] text-[var(--color-text-faint)]">
          ⌁ InterviewForge
        </span>
        <div className="flex-1" />
        {offline ? (
          <span
            className="flex items-center gap-1.5 rounded border border-[var(--color-warning)] px-2 py-0.5 text-[11px] text-[var(--color-warning)]"
            title="The API is unreachable, so this problem is loaded from bundled content and nothing will persist."
          >
            <WifiOff size={11} />
            Offline — not saving
          </span>
        ) : null}
        {dirty && !offline ? (
          <span className="text-[11px] text-[var(--color-text-faint)]">
            Unsaved changes
          </span>
        ) : null}
      </nav>

      <div className="flex min-h-0 flex-1">
        <RequirementsPanel problem={problem} />

        <div className="min-w-0 flex-1">
          <DesignCanvas
            initialNodes={(workspace?.nodes as SerializedNode[]) ?? []}
            initialEdges={(workspace?.edges as SerializedEdge[]) ?? []}
            components={components}
            onSave={handleSave}
            onReview={handleReview}
            saving={saving}
            reviewing={reviewing}
            onDirtyChange={setDirty}
          />
        </div>

        {review ? <ReviewPanel review={review} onClose={() => setReview(null)} /> : null}
      </div>

      {toast ? (
        <div
          role="status"
          className="fixed bottom-4 left-1/2 -translate-x-1/2 rounded border border-[var(--color-border-strong)] bg-[var(--color-surface-raised)] px-3.5 py-2 text-[13px] text-[var(--color-text)] shadow-xl"
        >
          {toast}
        </div>
      ) : null}
    </div>
  );
}
