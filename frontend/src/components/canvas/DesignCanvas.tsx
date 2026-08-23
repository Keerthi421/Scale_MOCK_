"use client";

import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  addEdge,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type Connection,
  type Edge,
  type Node,
  type NodeChange,
  type EdgeChange,
} from "@xyflow/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArchitectureNode } from "./ArchitectureNode";
import { Palette } from "./Palette";
import { CanvasToolbar } from "./CanvasToolbar";
import { FALLBACK_PALETTE, categoryOf } from "@/lib/palette";
import type {
  CanvasNodeData,
  PaletteComponent,
  SerializedEdge,
  SerializedNode,
} from "@/lib/types";

const nodeTypes = { architecture: ArchitectureNode };

/** Layered auto-layout order. Architecture diagrams read left-to-right from
 *  entry points through to storage, so laying out by category is far more
 *  useful here than a generic force-directed graph. */
const LAYER_ORDER = ["entry", "traffic", "compute", "async", "data", "platform", "other"];

const COLUMN_WIDTH = 240;
const ROW_HEIGHT = 110;
const MAX_HISTORY = 50;

interface Snapshot {
  nodes: Node[];
  edges: Edge[];
}

interface Props {
  initialNodes: SerializedNode[];
  initialEdges: SerializedEdge[];
  components?: PaletteComponent[];
  onSave?: (nodes: SerializedNode[], edges: SerializedEdge[]) => Promise<void> | void;
  onReview?: () => void;
  saving?: boolean;
  reviewing?: boolean;
  dirty?: boolean;
  onDirtyChange?: (dirty: boolean) => void;
}

function toFlowNode(n: SerializedNode): Node {
  return {
    id: n.id,
    type: "architecture",
    position: { x: n.x, y: n.y },
    data: { kind: n.kind, label: n.label, notes: n.notes ?? null } satisfies CanvasNodeData,
  };
}

function toFlowEdge(e: SerializedEdge): Edge {
  return {
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.label ?? undefined,
    animated: false,
  };
}

function InnerCanvas({
  initialNodes,
  initialEdges,
  components = FALLBACK_PALETTE,
  onSave,
  onReview,
  saving = false,
  reviewing = false,
  onDirtyChange,
}: Props) {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes.map(toFlowNode));
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges.map(toFlowEdge));
  const { screenToFlowPosition, fitView } = useReactFlow();
  const wrapper = useRef<HTMLDivElement>(null);

  const past = useRef<Snapshot[]>([]);
  const future = useRef<Snapshot[]>([]);
  const [, forceRender] = useState(0);
  // Suppresses history capture while we are ourselves applying an undo.
  const applyingHistory = useRef(false);

  const nodeIdCounter = useRef(initialNodes.length + 1);

  const commitHistory = useCallback(() => {
    if (applyingHistory.current) return;
    past.current.push({ nodes: structuredClone(nodes), edges: structuredClone(edges) });
    if (past.current.length > MAX_HISTORY) past.current.shift();
    future.current = [];
    onDirtyChange?.(true);
    forceRender((n) => n + 1);
  }, [nodes, edges, onDirtyChange]);

  const undo = useCallback(() => {
    const previous = past.current.pop();
    if (!previous) return;
    future.current.push({ nodes: structuredClone(nodes), edges: structuredClone(edges) });
    applyingHistory.current = true;
    setNodes(previous.nodes);
    setEdges(previous.edges);
    queueMicrotask(() => (applyingHistory.current = false));
    forceRender((n) => n + 1);
  }, [nodes, edges, setNodes, setEdges]);

  const redo = useCallback(() => {
    const next = future.current.pop();
    if (!next) return;
    past.current.push({ nodes: structuredClone(nodes), edges: structuredClone(edges) });
    applyingHistory.current = true;
    setNodes(next.nodes);
    setEdges(next.edges);
    queueMicrotask(() => (applyingHistory.current = false));
    forceRender((n) => n + 1);
  }, [nodes, edges, setNodes, setEdges]);

  const addComponent = useCallback(
    (component: PaletteComponent, position?: { x: number; y: number }) => {
      commitHistory();
      const id = `n${nodeIdCounter.current++}`;
      setNodes((current) => [
        ...current,
        {
          id,
          type: "architecture",
          // Offset each new node slightly so click-to-add does not stack them
          // all on the same pixel.
          position: position ?? {
            x: 220 + (current.length % 4) * 40,
            y: 120 + Math.floor(current.length / 4) * 40,
          },
          data: { kind: component.kind, label: component.label, notes: null },
        },
      ]);
    },
    [commitHistory, setNodes],
  );

  const onConnect = useCallback(
    (connection: Connection) => {
      commitHistory();
      setEdges((current) =>
        addEdge({ ...connection, id: `e${current.length + 1}-${Date.now()}` }, current),
      );
    },
    [commitHistory, setEdges],
  );

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      const raw = event.dataTransfer.getData("application/interviewforge-node");
      if (!raw) return;
      const component = JSON.parse(raw) as PaletteComponent;
      const position = screenToFlowPosition({ x: event.clientX, y: event.clientY });
      addComponent(component, position);
    },
    [addComponent, screenToFlowPosition],
  );

  /** Arrange nodes into columns by architectural layer. */
  const autoLayout = useCallback(() => {
    commitHistory();
    const columns = new Map<string, Node[]>();
    for (const node of nodes) {
      const layer = categoryOf((node.data as unknown as CanvasNodeData).kind);
      (columns.get(layer) ?? columns.set(layer, []).get(layer)!).push(node);
    }
    const ordered = LAYER_ORDER.filter((l) => columns.has(l));
    setNodes(
      nodes.map((node) => {
        const layer = categoryOf((node.data as unknown as CanvasNodeData).kind);
        const column = ordered.indexOf(layer);
        const row = columns.get(layer)!.indexOf(node);
        return { ...node, position: { x: column * COLUMN_WIDTH, y: row * ROW_HEIGHT } };
      }),
    );
    setTimeout(() => fitView({ padding: 0.2, duration: 300 }), 50);
  }, [nodes, commitHistory, setNodes, fitView]);

  const serialize = useCallback((): {
    nodes: SerializedNode[];
    edges: SerializedEdge[];
  } => {
    const nodeIds = new Set(nodes.map((n) => n.id));
    return {
      nodes: nodes.map((n) => {
        const data = n.data as unknown as CanvasNodeData;
        return {
          id: n.id,
          kind: data.kind,
          label: data.label,
          x: Math.round(n.position.x),
          y: Math.round(n.position.y),
          notes: data.notes ?? null,
        };
      }),
      // Drop any edge whose endpoints no longer exist. The backend rejects
      // dangling edges, so filtering here turns a 422 into a silent no-op
      // rather than a failed save the user cannot act on.
      edges: edges
        .filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target))
        .map((e) => ({
          id: e.id,
          source: e.source,
          target: e.target,
          label: typeof e.label === "string" ? e.label : null,
        })),
    };
  }, [nodes, edges]);

  const handleSave = useCallback(async () => {
    if (!onSave) return;
    const { nodes: n, edges: e } = serialize();
    await onSave(n, e);
    onDirtyChange?.(false);
  }, [onSave, serialize, onDirtyChange]);

  const handleExport = useCallback(() => {
    const blob = new Blob([JSON.stringify(serialize(), null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "architecture.json";
    link.click();
    URL.revokeObjectURL(url);
  }, [serialize]);

  // Track structural edits for history. Position drags are noisy — capturing
  // every pixel of movement would make undo useless — so only commit when a
  // drag ends or something is added or removed.
  const handleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      const structural = changes.some(
        (c) => c.type === "remove" || (c.type === "position" && c.dragging === false),
      );
      if (structural) commitHistory();
      onNodesChange(changes);
      if (changes.some((c) => c.type !== "select")) onDirtyChange?.(true);
    },
    [commitHistory, onNodesChange, onDirtyChange],
  );

  const handleEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      if (changes.some((c) => c.type === "remove")) commitHistory();
      onEdgesChange(changes);
      if (changes.some((c) => c.type !== "select")) onDirtyChange?.(true);
    },
    [commitHistory, onEdgesChange, onDirtyChange],
  );

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      const mod = event.metaKey || event.ctrlKey;
      if (!mod) return;
      if (event.key === "z" && !event.shiftKey) {
        event.preventDefault();
        undo();
      } else if ((event.key === "z" && event.shiftKey) || event.key === "y") {
        event.preventDefault();
        redo();
      } else if (event.key === "s") {
        event.preventDefault();
        void handleSave();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [undo, redo, handleSave]);

  const stats = useMemo(
    () => ({ nodes: nodes.length, edges: edges.length }),
    [nodes.length, edges.length],
  );

  return (
    <div className="flex h-full min-h-0 w-full">
      <Palette components={components} onAdd={(c) => addComponent(c)} />

      <div className="flex min-w-0 flex-1 flex-col">
        <CanvasToolbar
          canUndo={past.current.length > 0}
          canRedo={future.current.length > 0}
          onUndo={undo}
          onRedo={redo}
          onAutoLayout={autoLayout}
          onFit={() => fitView({ padding: 0.2, duration: 300 })}
          onSave={handleSave}
          onExport={handleExport}
          onReview={onReview}
          saving={saving}
          reviewing={reviewing}
          stats={stats}
        />

        <div ref={wrapper} className="min-h-0 flex-1">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={handleNodesChange}
            onEdgesChange={handleEdgesChange}
            onConnect={onConnect}
            onDrop={onDrop}
            onDragOver={(e) => {
              e.preventDefault();
              e.dataTransfer.dropEffect = "move";
            }}
            nodeTypes={nodeTypes}
            fitView
            proOptions={{ hideAttribution: false }}
            deleteKeyCode={["Backspace", "Delete"]}
            className="canvas-grid"
          >
            <Background
              variant={BackgroundVariant.Dots}
              gap={24}
              size={1}
              color="var(--color-border)"
            />
            <Controls showInteractive={false} />
            <MiniMap
              pannable
              zoomable
              className="!bg-[var(--color-surface)]"
              maskColor="rgba(13,15,18,.75)"
              nodeColor={(n) =>
                categoryOf((n.data as unknown as CanvasNodeData).kind) === "data"
                  ? "#a371f7"
                  : "#f0883e"
              }
            />
          </ReactFlow>
        </div>
      </div>
    </div>
  );
}

export function DesignCanvas(props: Props) {
  return (
    <ReactFlowProvider>
      <InnerCanvas {...props} />
    </ReactFlowProvider>
  );
}
