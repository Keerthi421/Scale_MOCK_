"use client";

import { useMemo, useState } from "react";
import { CATEGORY_LABELS, CATEGORY_COLOR } from "@/lib/palette";
import type { PaletteComponent } from "@/lib/types";

interface Props {
  components: PaletteComponent[];
  onAdd: (component: PaletteComponent) => void;
}

/**
 * The component palette.
 *
 * Supports both drag-to-place and click-to-add. Click matters: drag-and-drop
 * is awkward on trackpads and unusable on touch, and a candidate should never
 * lose interview time fighting the tool.
 */
export function Palette({ components, onAdd }: Props) {
  const [query, setQuery] = useState("");

  const grouped = useMemo(() => {
    const q = query.trim().toLowerCase();
    const matched = q
      ? components.filter(
          (c) =>
            c.label.toLowerCase().includes(q) ||
            c.kind.includes(q) ||
            c.description.toLowerCase().includes(q),
        )
      : components;

    return matched.reduce<Record<string, PaletteComponent[]>>((acc, c) => {
      (acc[c.category] ??= []).push(c);
      return acc;
    }, {});
  }, [components, query]);

  const categories = Object.keys(grouped);

  return (
    <aside className="flex h-full w-60 shrink-0 flex-col border-r border-[var(--color-border)] bg-[var(--color-surface)]">
      <div className="border-b border-[var(--color-border)] p-3">
        <h2 className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-faint)]">
          Components
        </h2>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search…"
          className="w-full rounded border border-[var(--color-border)] bg-[var(--color-bg)] px-2.5 py-1.5 text-sm text-[var(--color-text)] outline-none placeholder:text-[var(--color-text-faint)] focus:border-[var(--color-accent)]"
        />
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {categories.length === 0 ? (
          <p className="px-1 py-6 text-center text-xs text-[var(--color-text-faint)]">
            No components match “{query}”.
          </p>
        ) : (
          categories.map((category) => (
            <section key={category} className="mb-3">
              <div className="mb-1 flex items-center gap-1.5 px-1">
                <span
                  className="h-1.5 w-1.5 rounded-full"
                  style={{ background: CATEGORY_COLOR[category] }}
                />
                <h3 className="text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-faint)]">
                  {CATEGORY_LABELS[category] ?? category}
                </h3>
              </div>

              {grouped[category]!.map((component) => (
                <button
                  key={component.kind}
                  type="button"
                  draggable
                  onDragStart={(e) => {
                    e.dataTransfer.setData(
                      "application/interviewforge-node",
                      JSON.stringify(component),
                    );
                    e.dataTransfer.effectAllowed = "move";
                  }}
                  onClick={() => onAdd(component)}
                  title={component.description}
                  className="group mb-0.5 flex w-full cursor-grab items-center gap-2 rounded px-2 py-1.5 text-left transition-colors hover:bg-[var(--color-surface-hover)] active:cursor-grabbing"
                >
                  <span
                    className="h-4 w-0.5 shrink-0 rounded-full opacity-60 transition-opacity group-hover:opacity-100"
                    style={{ background: CATEGORY_COLOR[category] }}
                  />
                  <span className="truncate text-[13px] text-[var(--color-text-muted)] group-hover:text-[var(--color-text)]">
                    {component.label}
                  </span>
                </button>
              ))}
            </section>
          ))
        )}
      </div>

      <p className="border-t border-[var(--color-border)] px-3 py-2 text-[10px] leading-relaxed text-[var(--color-text-faint)]">
        Drag onto the canvas, or click to add. Double-click a node to rename.
      </p>
    </aside>
  );
}
