"""Canvas component palette.

Seeded into `component_catalog` so the client palette and the AI reviewer read
the same list. Descriptions are written for the candidate — they say what the
component is *for*, since a palette that only names things teaches nothing.
"""

from __future__ import annotations

from app.models.enums import NodeKind

# (kind, label, category, icon, description)
COMPONENTS: list[tuple[NodeKind, str, str, str, str]] = [
    # --- Entry points ------------------------------------------------------
    (NodeKind.CLIENT, "Client", "entry", "monitor",
     "A generic consumer of your API. Use when the device type does not matter."),
    (NodeKind.WEB_APP, "Web App", "entry", "globe",
     "Browser client. Relevant when you need to reason about CORS, bundle size, or SSR."),
    (NodeKind.MOBILE_APP, "Mobile App", "entry", "smartphone",
     "Mobile client. Matters when you must handle flaky networks, offline writes, or push."),
    (NodeKind.DNS, "DNS", "entry", "route",
     "Resolves your domain to an address. The place to describe geo-routing or failover."),
    (NodeKind.CDN, "CDN", "entry", "cloud",
     "Caches static assets near users. Cuts latency and origin bandwidth for media-heavy reads."),

    # --- Traffic management ------------------------------------------------
    (NodeKind.LOAD_BALANCER, "Load Balancer", "traffic", "git-fork",
     "Spreads traffic across healthy instances. Say which algorithm and how health is checked."),
    (NodeKind.API_GATEWAY, "API Gateway", "traffic", "door-open",
     "Single entry point for auth, routing, and quotas. Watch that it does not become a SPOF."),
    (NodeKind.REVERSE_PROXY, "Reverse Proxy", "traffic", "shuffle",
     "Terminates TLS and forwards requests. Often also does compression and connection reuse."),
    (NodeKind.RATE_LIMITER, "Rate Limiter", "traffic", "gauge",
     "Caps per-client request rate. Specify the algorithm and where counters live."),

    # --- Compute -----------------------------------------------------------
    (NodeKind.APP_SERVER, "Application Server", "compute", "server",
     "Stateless request handler. Keeping it stateless is what makes horizontal scaling work."),
    (NodeKind.MICROSERVICE, "Microservice", "compute", "boxes",
     "A service owning one bounded capability and its data. Justify each split you make."),
    (NodeKind.WORKER, "Worker", "compute", "cpu",
     "Consumes queued jobs off the request path — encoding, email, indexing."),
    (NodeKind.CRON, "Scheduled Job", "compute", "calendar-clock",
     "Runs periodic work such as rollups, cleanup, or report generation."),

    # --- Data --------------------------------------------------------------
    (NodeKind.SQL_DATABASE, "SQL Database", "data", "database",
     "Relational store with transactions and joins. The default until you can name why not."),
    (NodeKind.NOSQL_DATABASE, "NoSQL Database", "data", "database-zap",
     "Wide-column or document store. Choose it for a known access pattern at high write volume."),
    (NodeKind.READ_REPLICA, "Read Replica", "data", "copy",
     "Serves reads and adds redundancy. Say how you handle replication lag."),
    (NodeKind.CACHE, "Cache", "data", "zap",
     "In-memory store for hot data. State the eviction policy and how stale entries are handled."),
    (NodeKind.OBJECT_STORAGE, "Object Storage", "data", "hard-drive",
     "Blob store for images, video, and backups. Cheap, durable, not for low-latency lookups."),
    (NodeKind.SEARCH_INDEX, "Search Index", "data", "search",
     "Inverted index for full-text and faceted search. Kept in sync asynchronously."),
    (NodeKind.DATA_WAREHOUSE, "Data Warehouse", "data", "bar-chart-3",
     "Columnar store for analytics. Keeps heavy reporting queries off production."),

    # --- Asynchronous ------------------------------------------------------
    (NodeKind.MESSAGE_QUEUE, "Message Queue", "async", "list-ordered",
     "Point-to-point work buffer. Absorbs spikes and lets producers outpace consumers."),
    (NodeKind.EVENT_STREAM, "Event Stream", "async", "activity",
     "Durable ordered log with replay. Use when several consumers need the same events."),
    (NodeKind.PUB_SUB, "Pub/Sub", "async", "radio",
     "Fan-out broadcast to many subscribers. Good for notifications and cache invalidation."),

    # --- Cross-cutting -----------------------------------------------------
    (NodeKind.AUTH_SERVICE, "Auth Service", "platform", "shield",
     "Issues and verifies identity tokens. Centralizes session and permission logic."),
    (NodeKind.MONITORING, "Monitoring", "platform", "line-chart",
     "Metrics, dashboards, and alerts. Name the signals you would page on."),
    (NodeKind.LOGGING, "Logging", "platform", "scroll-text",
     "Aggregated structured logs and traces — how you debug a failure after the fact."),
    (NodeKind.CONFIG_SERVICE, "Config / Feature Flags", "platform", "sliders",
     "Runtime configuration and rollout control without a redeploy."),

    (NodeKind.CUSTOM, "Custom Component", "other", "square-dashed",
     "Anything the palette does not cover. Label it clearly so the reviewer can follow."),
]
