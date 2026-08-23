import type { NodeKind, PaletteComponent } from "./types";

/**
 * Local mirror of the backend's `component_catalog` seed.
 *
 * The API is the source of truth — `GET /system-design/components` — but the
 * canvas must stay usable when the backend is unreachable, and a palette that
 * fails to load leaves the user staring at an empty sidebar with no way to
 * draw anything. This is the fallback, not a second source of truth: a
 * mismatch is a seed-drift bug, so keep the two in sync when adding a kind.
 */
export const FALLBACK_PALETTE: PaletteComponent[] = [
  { kind: "client", label: "Client", category: "entry", icon: "monitor", description: "A generic consumer of your API." },
  { kind: "web_app", label: "Web App", category: "entry", icon: "globe", description: "Browser client." },
  { kind: "mobile_app", label: "Mobile App", category: "entry", icon: "smartphone", description: "Mobile client — flaky networks, offline writes, push." },
  { kind: "dns", label: "DNS", category: "entry", icon: "route", description: "Resolves your domain. Geo-routing and failover live here." },
  { kind: "cdn", label: "CDN", category: "entry", icon: "cloud", description: "Caches static assets near users." },

  { kind: "load_balancer", label: "Load Balancer", category: "traffic", icon: "git-fork", description: "Spreads traffic across healthy instances." },
  { kind: "api_gateway", label: "API Gateway", category: "traffic", icon: "door-open", description: "Single entry point for auth, routing, quotas." },
  { kind: "reverse_proxy", label: "Reverse Proxy", category: "traffic", icon: "shuffle", description: "Terminates TLS and forwards requests." },
  { kind: "rate_limiter", label: "Rate Limiter", category: "traffic", icon: "gauge", description: "Caps per-client request rate." },

  { kind: "app_server", label: "Application Server", category: "compute", icon: "server", description: "Stateless request handler." },
  { kind: "microservice", label: "Microservice", category: "compute", icon: "boxes", description: "Owns one bounded capability and its data." },
  { kind: "worker", label: "Worker", category: "compute", icon: "cpu", description: "Consumes queued jobs off the request path." },
  { kind: "cron", label: "Scheduled Job", category: "compute", icon: "calendar-clock", description: "Periodic rollups, cleanup, reports." },

  { kind: "sql_database", label: "SQL Database", category: "data", icon: "database", description: "Relational store with transactions and joins." },
  { kind: "nosql_database", label: "NoSQL Database", category: "data", icon: "database-zap", description: "Wide-column or document store." },
  { kind: "read_replica", label: "Read Replica", category: "data", icon: "copy", description: "Serves reads and adds redundancy." },
  { kind: "cache", label: "Cache", category: "data", icon: "zap", description: "In-memory store for hot data." },
  { kind: "object_storage", label: "Object Storage", category: "data", icon: "hard-drive", description: "Blob store for images, video, backups." },
  { kind: "search_index", label: "Search Index", category: "data", icon: "search", description: "Inverted index for full-text search." },
  { kind: "data_warehouse", label: "Data Warehouse", category: "data", icon: "bar-chart-3", description: "Columnar store for analytics." },

  { kind: "message_queue", label: "Message Queue", category: "async", icon: "list-ordered", description: "Point-to-point work buffer." },
  { kind: "event_stream", label: "Event Stream", category: "async", icon: "activity", description: "Durable ordered log with replay." },
  { kind: "pub_sub", label: "Pub/Sub", category: "async", icon: "radio", description: "Fan-out broadcast to many subscribers." },

  { kind: "auth_service", label: "Auth Service", category: "platform", icon: "shield", description: "Issues and verifies identity tokens." },
  { kind: "monitoring", label: "Monitoring", category: "platform", icon: "line-chart", description: "Metrics, dashboards, alerts." },
  { kind: "logging", label: "Logging", category: "platform", icon: "scroll-text", description: "Aggregated structured logs and traces." },
  { kind: "config_service", label: "Config / Flags", category: "platform", icon: "sliders", description: "Runtime config and rollout control." },

  { kind: "custom", label: "Custom", category: "other", icon: "square-dashed", description: "Anything the palette does not cover." },
];

export const CATEGORY_LABELS: Record<string, string> = {
  entry: "Entry Points",
  traffic: "Traffic",
  compute: "Compute",
  data: "Data",
  async: "Asynchronous",
  platform: "Platform",
  other: "Other",
};

/** Accent colors per category so the canvas is scannable at a glance. */
export const CATEGORY_COLOR: Record<string, string> = {
  entry: "#58a6ff",
  traffic: "#f0883e",
  compute: "#3fb950",
  data: "#a371f7",
  async: "#d29922",
  platform: "#8b949e",
  other: "#6b7280",
};

export function categoryOf(kind: NodeKind): string {
  return FALLBACK_PALETTE.find((c) => c.kind === kind)?.category ?? "other";
}

export function colorOf(kind: NodeKind): string {
  return CATEGORY_COLOR[categoryOf(kind)] ?? CATEGORY_COLOR.other!;
}
