"use client";

import {
  Download,
  LayoutGrid,
  Maximize2,
  Redo2,
  Save,
  Sparkles,
  Undo2,
} from "lucide-react";

interface Props {
  canUndo: boolean;
  canRedo: boolean;
  onUndo: () => void;
  onRedo: () => void;
  onAutoLayout: () => void;
  onFit: () => void;
  onSave: () => void;
  onExport: () => void;
  onReview?: () => void;
  saving: boolean;
  reviewing: boolean;
  stats: { nodes: number; edges: number };
}

function ToolButton({
  onClick,
  disabled,
  title,
  children,
}: {
  onClick?: () => void;
  disabled?: boolean;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title}
      aria-label={title}
      className="rounded p-1.5 text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text)] disabled:cursor-not-allowed disabled:opacity-35 disabled:hover:bg-transparent disabled:hover:text-[var(--color-text-muted)]"
    >
      {children}
    </button>
  );
}

export function CanvasToolbar({
  canUndo,
  canRedo,
  onUndo,
  onRedo,
  onAutoLayout,
  onFit,
  onSave,
  onExport,
  onReview,
  saving,
  reviewing,
  stats,
}: Props) {
  return (
    <div className="flex shrink-0 items-center gap-1 border-b border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1.5">
      <ToolButton onClick={onUndo} disabled={!canUndo} title="Undo (Ctrl+Z)">
        <Undo2 size={15} />
      </ToolButton>
      <ToolButton onClick={onRedo} disabled={!canRedo} title="Redo (Ctrl+Shift+Z)">
        <Redo2 size={15} />
      </ToolButton>

      <div className="mx-1 h-4 w-px bg-[var(--color-border)]" />

      <ToolButton onClick={onAutoLayout} title="Auto-layout by architectural layer">
        <LayoutGrid size={15} />
      </ToolButton>
      <ToolButton onClick={onFit} title="Fit to view">
        <Maximize2 size={15} />
      </ToolButton>
      <ToolButton onClick={onExport} title="Export as JSON">
        <Download size={15} />
      </ToolButton>

      <div className="ml-2 font-mono text-[11px] text-[var(--color-text-faint)]">
        {stats.nodes} {stats.nodes === 1 ? "node" : "nodes"} · {stats.edges}{" "}
        {stats.edges === 1 ? "edge" : "edges"}
      </div>

      <div className="flex-1" />

      <button
        type="button"
        onClick={onSave}
        disabled={saving}
        className="flex items-center gap-1.5 rounded border border-[var(--color-border-strong)] px-2.5 py-1 text-xs font-medium text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text)] disabled:opacity-50"
      >
        <Save size={13} />
        {saving ? "Saving…" : "Save"}
      </button>

      {onReview ? (
        <button
          type="button"
          onClick={onReview}
          disabled={reviewing || stats.nodes === 0}
          title={
            stats.nodes === 0
              ? "Add components before requesting a review"
              : "Get an AI review of this architecture"
          }
          className="flex items-center gap-1.5 rounded bg-[var(--color-accent)] px-3 py-1 text-xs font-semibold text-[#1a1005] transition-colors hover:bg-[var(--color-accent-hot)] disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Sparkles size={13} />
          {reviewing ? "Reviewing…" : "Review Design"}
        </button>
      ) : null}
    </div>
  );
}
