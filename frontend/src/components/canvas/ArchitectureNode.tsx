"use client";

import { Handle, Position, type NodeProps, useReactFlow } from "@xyflow/react";
import { useEffect, useRef, useState } from "react";
import { colorOf } from "@/lib/palette";
import type { CanvasNodeData } from "@/lib/types";

/**
 * One component on the architecture canvas.
 *
 * Handles are on all four sides so a candidate can route a connection the way
 * the diagram reads best, rather than fighting a fixed left-to-right flow.
 */
export function ArchitectureNode({ id, data, selected }: NodeProps) {
  const nodeData = data as unknown as CanvasNodeData;
  const { setNodes } = useReactFlow();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(nodeData.label);
  const inputRef = useRef<HTMLInputElement>(null);

  const accent = colorOf(nodeData.kind);

  useEffect(() => {
    if (editing) inputRef.current?.select();
  }, [editing]);

  function commit() {
    const label = draft.trim() || nodeData.label;
    setNodes((nodes) =>
      nodes.map((n) => (n.id === id ? { ...n, data: { ...n.data, label } } : n)),
    );
    setDraft(label);
    setEditing(false);
  }

  return (
    <div
      className="min-w-[168px] rounded-md border bg-[var(--color-surface-raised)] shadow-lg transition-shadow"
      style={{
        borderColor: selected ? accent : "var(--color-border-strong)",
        boxShadow: selected ? `0 0 0 1px ${accent}, 0 4px 16px rgba(0,0,0,.4)` : undefined,
      }}
      onDoubleClick={(e) => {
        e.stopPropagation();
        setEditing(true);
      }}
    >
      {/* Every side both accepts and originates connections. */}
      {(["Top", "Right", "Bottom", "Left"] as const).map((side) => (
        <div key={side}>
          <Handle
            type="target"
            position={Position[side]}
            id={`${side.toLowerCase()}-t`}
          />
          <Handle
            type="source"
            position={Position[side]}
            id={`${side.toLowerCase()}-s`}
          />
        </div>
      ))}

      <div className="h-1 rounded-t-md" style={{ background: accent }} />

      <div className="px-3 py-2.5">
        {editing ? (
          <input
            ref={inputRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={commit}
            onKeyDown={(e) => {
              if (e.key === "Enter") commit();
              if (e.key === "Escape") {
                setDraft(nodeData.label);
                setEditing(false);
              }
              e.stopPropagation();
            }}
            className="w-full bg-transparent text-sm font-medium text-[var(--color-text)] outline-none"
            maxLength={80}
          />
        ) : (
          <div className="text-sm font-medium leading-tight text-[var(--color-text)]">
            {nodeData.label}
          </div>
        )}

        <div className="mt-0.5 font-mono text-[10px] uppercase tracking-wide text-[var(--color-text-faint)]">
          {nodeData.kind.replace(/_/g, " ")}
        </div>

        {nodeData.notes ? (
          <div className="mt-1.5 border-t border-[var(--color-border)] pt-1.5 text-[11px] leading-snug text-[var(--color-text-muted)]">
            {nodeData.notes}
          </div>
        ) : null}
      </div>
    </div>
  );
}
