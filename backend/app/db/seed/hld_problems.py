"""HLD problem catalog.

All content here is originally authored. The *topics* are the canonical
interview set (public knowledge — every platform and textbook covers the same
scenarios); the statements, requirements, capacity math, and guidance are
written for this product and are not copied from any third-party platform.

Capacity numbers are deliberately shown as worked arithmetic rather than
results, because the arithmetic is the part a candidate is actually asked to
reproduce in an interview.
"""

from __future__ import annotations

from typing import Any

from app.models.enums import Difficulty, NodeKind

# Each entry becomes one `problems` row plus one `hld_problem_details` row.
# `sheet_tier` is the smallest sheet that includes the problem: a 25-tier
# problem also appears in the 75 and 150 sheets.
HLD_PROBLEMS: list[dict[str, Any]] = [
    {
        "slug": "design-a-url-shortener",
        "title": "Design a URL Shortener",
        "difficulty": Difficulty.EASY,
        "order_index": 1,
        "sheet_tier": 25,
        "is_free_preview": True,
        "estimated_minutes": 35,
        "tags": ["hashing", "key-value", "caching", "read-heavy"],
        "companies": ["Amazon", "Google", "Microsoft"],
        "summary": "Map long URLs to short codes and redirect at scale.",
        "description_md": (
            "Design a service that turns a long URL into a short code and redirects "
            "visitors who follow it.\n\n"
            "The interesting part is not generating the code — it is that reads "
            "outnumber writes by roughly two orders of magnitude, redirects must be "
            "fast enough to feel instant, and a code, once issued, can never be "
            "reused for a different URL."
        ),
        "functional_requirements": [
            "Given a long URL, return a short code.",
            "Given a short code, redirect to the original URL.",
            "Optionally accept a user-supplied custom alias.",
            "Optionally accept an expiry time, after which the code stops resolving.",
        ],
        "non_functional_requirements": [
            "Redirect p99 latency under 100ms.",
            "Read:write ratio around 100:1.",
            "Codes must be unique and never recycled.",
            "Availability matters more than strong consistency on reads.",
        ],
        "capacity_estimation": [
            {
                "metric": "Write QPS",
                "assumption": "100M new links per month",
                "working": "100e6 / (30 x 86400) = ~39 writes/sec average; assume 3x peak",
                "result": "~40 writes/sec average, ~120/sec peak",
            },
            {
                "metric": "Read QPS",
                "assumption": "100:1 read:write ratio",
                "working": "40 x 100 = 4,000 reads/sec average, ~12,000/sec peak",
                "result": "~4K reads/sec average",
            },
            {
                "metric": "Storage (5 years)",
                "assumption": "~500 bytes per record (URL, code, owner, timestamps)",
                "working": "100e6 x 12 x 5 = 6e9 records; 6e9 x 500B = ~3TB",
                "result": "~3TB, before replication",
            },
            {
                "metric": "Cache working set",
                "assumption": "Classic 80/20 — 20% of links serve 80% of reads",
                "working": "Daily reads ~345M; 20% of distinct daily links x 500B",
                "result": "Tens of GB — comfortably cacheable in memory",
            },
        ],
        "expected_components": [
            NodeKind.CLIENT, NodeKind.LOAD_BALANCER, NodeKind.APP_SERVER,
            NodeKind.CACHE, NodeKind.SQL_DATABASE, NodeKind.READ_REPLICA,
        ],
        "api_design_md": (
            "```\n"
            "POST /api/v1/links        { url, custom_alias?, expires_at? } -> { code, short_url }\n"
            "GET  /{code}              -> 302 redirect to the original URL\n"
            "GET  /api/v1/links/{code} -> metadata (owner, clicks, created_at)\n"
            "DELETE /api/v1/links/{code}\n"
            "```\n\n"
            "Use 302 rather than 301. A 301 is cached by the browser indefinitely, "
            "which means you stop seeing the traffic — and analytics is usually the "
            "reason this service exists."
        ),
        "data_model_md": (
            "A single table is enough:\n\n"
            "```\n"
            "links(code PK, long_url, user_id, created_at, expires_at, click_count)\n"
            "```\n\n"
            "Every read is a primary-key lookup on `code`, so this stays fast even at "
            "billions of rows. Do not put `click_count` in the hot path — incrementing "
            "a row on every redirect turns a read-only path into a write. Emit a click "
            "event to a queue and aggregate it asynchronously instead."
        ),
        "architecture_md": (
            "Client -> Load Balancer -> Application Servers, with Redis in front of the "
            "database.\n\n"
            "**Generating the code.** Three approaches, in increasing order of how well "
            "they interview:\n\n"
            "1. *Hash the URL* (MD5/SHA, base62-encode a prefix). Simple, but collisions "
            "need handling and the same URL always maps to the same code — which breaks "
            "per-user analytics.\n"
            "2. *Random code with a uniqueness check.* Clean, but the check is a database "
            "round trip on every write, and it degrades as the keyspace fills.\n"
            "3. *Pre-generated key range per server.* A coordination service hands each "
            "app server a block of unused counter values, which it base62-encodes locally. "
            "No collisions, no per-write coordination. The cost is a small number of keys "
            "lost whenever a server dies mid-block, which is fine — the keyspace is huge.\n\n"
            "Base62 over 7 characters gives 62^7 = ~3.5 trillion codes, comfortably more "
            "than the ~6 billion this design needs over five years."
        ),
        "scaling_md": (
            "Reads are the whole problem, so cache aggressively: Redis read-through, with "
            "the TTL set from the link's own expiry. A cache hit should never touch the "
            "database.\n\n"
            "For the database, primary-key lookups shard cleanly on `code`. Add read "
            "replicas before sharding — replication lag is acceptable here because a link "
            "that resolves a few hundred milliseconds after creation is not a correctness "
            "problem.\n\n"
            "Expiry is best handled lazily: check `expires_at` on read and treat an expired "
            "row as a 404, then reclaim rows with a background job. A job that deletes "
            "exactly at expiry time creates a thundering herd against the database for no "
            "user-visible benefit."
        ),
        "tradeoffs_md": (
            "**Custom aliases break the key-range scheme.** They have to go through a "
            "uniqueness check, so they are a genuinely different write path. Say so rather "
            "than pretending one mechanism covers both.\n\n"
            "**Analytics is where this design usually falls down.** Counting clicks "
            "synchronously converts a cache-served read into a database write and destroys "
            "the read-heavy properties you just built for. Fire an event; aggregate later.\n\n"
            "**Eventual consistency is the right call here.** A user who creates a link and "
            "hits it immediately might see a miss for a moment. Weigh that against the cost "
            "of strong consistency on a 4,000 QPS read path."
        ),
    },
    {
        "slug": "design-a-rate-limiter",
        "title": "Design a Distributed Rate Limiter",
        "difficulty": Difficulty.MEDIUM,
        "order_index": 2,
        "sheet_tier": 25,
        "is_free_preview": True,
        "estimated_minutes": 40,
        "tags": ["algorithms", "redis", "concurrency", "distributed-state"],
        "companies": ["Stripe", "Cloudflare", "Amazon"],
        "summary": "Cap per-client request rates across a fleet of servers.",
        "description_md": (
            "Design a rate limiter that caps how many requests a client may make in a "
            "given window, enforced consistently across many application servers.\n\n"
            "The hard part is that the counter is shared state on the hot path of every "
            "request. It has to be correct enough to actually limit abuse, and cheap "
            "enough that it does not become the bottleneck it was meant to prevent."
        ),
        "functional_requirements": [
            "Limit requests per client identifier (API key, user, or IP).",
            "Support different limits per endpoint and per plan tier.",
            "Return 429 with a Retry-After header when a caller is over the limit.",
            "Expose remaining quota to clients via response headers.",
        ],
        "non_functional_requirements": [
            "Adds under 5ms to request latency.",
            "Enforced consistently across all application servers.",
            "Must fail open — a limiter outage cannot take down the API.",
            "Memory proportional to active clients, not total clients.",
        ],
        "capacity_estimation": [
            {
                "metric": "Limiter QPS",
                "assumption": "Every API request checks the limit; 50K API QPS",
                "working": "50,000 checks/sec, each 1-2 Redis operations",
                "result": "~50-100K Redis ops/sec — one cluster handles this",
            },
            {
                "metric": "Memory",
                "assumption": "1M active clients, sliding-window log, ~100 entries each",
                "working": "1e6 x 100 x ~16B per entry = ~1.6GB",
                "result": "~2GB — the reason counters beat logs at scale",
            },
        ],
        "expected_components": [
            NodeKind.CLIENT, NodeKind.API_GATEWAY, NodeKind.RATE_LIMITER,
            NodeKind.CACHE, NodeKind.APP_SERVER, NodeKind.MONITORING,
        ],
        "api_design_md": (
            "The limiter is middleware, not a public API. What matters is what it puts on "
            "the response:\n\n"
            "```\n"
            "X-RateLimit-Limit: 1000\n"
            "X-RateLimit-Remaining: 847\n"
            "X-RateLimit-Reset: 1735689600\n"
            "Retry-After: 42          (on 429 only)\n"
            "```\n\n"
            "Returning these is not decoration — without them a well-behaved client cannot "
            "back off correctly and will hammer you until it gets banned."
        ),
        "data_model_md": (
            "State lives in Redis, keyed by client and window:\n\n"
            "```\n"
            "ratelimit:{client_id}:{endpoint}  -> counter or sorted set\n"
            "```\n\n"
            "Set a TTL slightly longer than the window so keys for inactive clients expire "
            "on their own. That is what keeps memory proportional to *active* clients."
        ),
        "architecture_md": (
            "Enforce at the API gateway, before requests reach application servers — a "
            "request you reject should cost as little as possible.\n\n"
            "**Choosing the algorithm** is the core of this question:\n\n"
            "- *Fixed window counter.* One counter per window. Trivially cheap, but allows "
            "2x the limit across a boundary: 100 requests at 0:59 and 100 more at 1:01 is "
            "200 in two seconds.\n"
            "- *Sliding window log.* A sorted set of timestamps; drop old entries on read. "
            "Exact, but memory grows with the limit — expensive at high limits.\n"
            "- *Sliding window counter.* Weights the previous window's count by how far into "
            "the current window you are. Approximate, but bounded memory and no boundary "
            "burst. This is usually the right default.\n"
            "- *Token bucket.* Tokens refill at a fixed rate; each request spends one. "
            "Allows deliberate bursts, which is the correct behavior for most APIs.\n\n"
            "Whichever you choose, the check must be atomic. A read-then-write from many "
            "servers races, and under exactly the concurrent load the limiter exists to "
            "control. Use a Lua script or `INCR` with an expiry set in the same round trip."
        ),
        "scaling_md": (
            "One Redis instance handles a surprising amount of this. When it stops being "
            "enough, shard by client id — every key for a client lives on one shard, so "
            "there is no cross-shard coordination.\n\n"
            "To cut latency further, keep a per-server local counter as a first pass and "
            "only consult Redis near the limit. This trades a little accuracy for a large "
            "drop in network round trips.\n\n"
            "**Fail open.** If Redis is unreachable, allow the request and alert. A limiter "
            "that fails closed converts a cache outage into a total API outage — you have "
            "turned a mitigation into a single point of failure."
        ),
        "tradeoffs_md": (
            "**Accuracy versus cost.** Exact limiting needs per-request shared state. "
            "Approximate limiting is dramatically cheaper and almost always sufficient — "
            "the goal is preventing abuse, not billing-grade precision.\n\n"
            "**Distributed versus local.** Local counters are fast but let a client with N "
            "connections get N times the limit. Say which you chose and why.\n\n"
            "**What to key on.** IP is easy but punishes users behind shared NAT and is "
            "trivially evaded. API keys are correct but only exist for authenticated "
            "traffic — you need a fallback for the login endpoint itself, which is exactly "
            "where abuse concentrates."
        ),
    },
    {
        "slug": "design-a-news-feed",
        "title": "Design a News Feed",
        "difficulty": Difficulty.HARD,
        "order_index": 3,
        "sheet_tier": 25,
        "is_free_preview": False,
        "estimated_minutes": 50,
        "tags": ["fanout", "caching", "ranking", "write-heavy"],
        "companies": ["Meta", "Twitter", "LinkedIn"],
        "summary": "Build and serve a personalized timeline at social-network scale.",
        "description_md": (
            "Design the feed for a social network: users follow other users, and each user "
            "sees a personalized timeline of recent posts from the people they follow.\n\n"
            "This problem is really one question — when do you do the work? Assembling the "
            "feed at read time is simple but slow. Assembling it at write time is fast to "
            "read but explodes for users with millions of followers."
        ),
        "functional_requirements": [
            "Users can post; posts appear in followers' feeds.",
            "Users can follow and unfollow other users.",
            "Feed is ordered (chronological or ranked) and paginates.",
            "Feed reflects new posts within seconds.",
        ],
        "non_functional_requirements": [
            "Feed load p99 under 200ms.",
            "Read-heavy: users read far more than they post.",
            "Follower counts are highly skewed — most users have few, some have millions.",
            "Eventual consistency is acceptable; a post may take seconds to appear.",
        ],
        "capacity_estimation": [
            {
                "metric": "Post write QPS",
                "assumption": "300M DAU, 20% post once per day",
                "working": "60e6 / 86400 = ~700 posts/sec average, ~2,100 peak",
                "result": "~700 writes/sec",
            },
            {
                "metric": "Fanout writes",
                "assumption": "Average 200 followers per poster",
                "working": "700 x 200 = 140,000 feed-entry writes/sec",
                "result": "~140K/sec — the number that motivates the hybrid design",
            },
            {
                "metric": "Feed read QPS",
                "assumption": "300M DAU x 10 feed loads/day",
                "working": "3e9 / 86400 = ~35,000 reads/sec average",
                "result": "~35K reads/sec",
            },
            {
                "metric": "Feed cache",
                "assumption": "Cache 200 post ids per active user, 8 bytes each",
                "working": "300e6 x 200 x 8B = ~480GB",
                "result": "~500GB across a Redis cluster",
            },
        ],
        "expected_components": [
            NodeKind.CLIENT, NodeKind.LOAD_BALANCER, NodeKind.API_GATEWAY,
            NodeKind.APP_SERVER, NodeKind.MESSAGE_QUEUE, NodeKind.WORKER,
            NodeKind.CACHE, NodeKind.NOSQL_DATABASE, NodeKind.OBJECT_STORAGE,
        ],
        "api_design_md": (
            "```\n"
            "POST /api/v1/posts          { text, media_ids? } -> { post_id }\n"
            "GET  /api/v1/feed?cursor=   -> { posts[], next_cursor }\n"
            "POST /api/v1/follow/{user}\n"
            "```\n\n"
            "Paginate by cursor, not offset. `OFFSET 10000` makes the database scan and "
            "discard 10,000 rows, and on a feed that is constantly gaining new entries at "
            "the top, offsets also shift under the reader and duplicate posts across pages."
        ),
        "data_model_md": (
            "```\n"
            "posts(post_id PK, author_id, text, media_urls, created_at)\n"
            "follows(follower_id, followee_id, created_at)   -- indexed both directions\n"
            "feed(user_id, post_id, score, created_at)       -- the materialized timeline\n"
            "```\n\n"
            "Store post *ids* in the feed, not post bodies. Otherwise editing or deleting "
            "one post means rewriting it in millions of feed rows — and you will miss some."
        ),
        "architecture_md": (
            "**Fanout-on-write (push).** When a user posts, a worker writes the post id into "
            "each follower's feed list. Reads are then a single cache lookup. Excellent for "
            "the common case; catastrophic for a celebrity — one post by a user with 50M "
            "followers is 50M writes.\n\n"
            "**Fanout-on-read (pull).** Build the feed at request time by querying recent "
            "posts from everyone the user follows. No write amplification, but reads become "
            "a scatter-gather across hundreds of authors — far too slow at 35K QPS.\n\n"
            "**The hybrid is the answer, and knowing *why* is the point.** Push for ordinary "
            "users; for accounts above a follower threshold, skip fanout and merge their "
            "recent posts in at read time. Each user's feed read then becomes: fetch the "
            "precomputed list, fetch recent posts from the handful of celebrities they "
            "follow, merge, return. You pay a small read cost to avoid an unbounded write "
            "cost, and the threshold is a tunable rather than a hardcoded rule."
        ),
        "scaling_md": (
            "Fanout goes through a queue, never inline with the post request. The user's "
            "post should be durable and acknowledged in milliseconds; propagation is "
            "background work.\n\n"
            "Cap stored feeds — a few hundred entries per user is plenty, since almost "
            "nobody scrolls further. Fall back to a query for the rare deep scroll.\n\n"
            "Fan out only to *active* users. Writing feed entries for accounts that have not "
            "logged in for a year is pure waste; rebuild their feed on next login instead."
        ),
        "tradeoffs_md": (
            "**Chronological versus ranked.** Ranking improves engagement but means the feed "
            "cannot simply be a sorted list — you need a scoring pipeline and features, and "
            "the score changes after write. That is a substantially bigger system.\n\n"
            "**Deletes and edits are the hidden cost of push.** Storing ids instead of bodies "
            "is what makes them tractable; mention it, because interviewers look for it.\n\n"
            "**The celebrity threshold is a real tuning problem.** Too low and you lose the "
            "benefit of precomputation; too high and a few accounts can saturate the fanout "
            "workers. It should be adjustable at runtime, not a constant in the code."
        ),
    },
    {
        "slug": "design-a-chat-application",
        "title": "Design a Chat Application",
        "difficulty": Difficulty.HARD,
        "order_index": 4,
        "sheet_tier": 25,
        "is_free_preview": False,
        "estimated_minutes": 50,
        "tags": ["websockets", "realtime", "ordering", "presence"],
        "companies": ["Meta", "Slack", "Discord"],
        "summary": "Real-time messaging with delivery guarantees and presence.",
        "description_md": (
            "Design a messaging service supporting one-to-one and group chat, with "
            "delivery receipts, presence, and message history.\n\n"
            "The distinctive constraint is that connections are long-lived and stateful. "
            "That breaks the usual assumption that any server can handle any request, and "
            "it makes routing a message to a recipient a genuine design problem."
        ),
        "functional_requirements": [
            "Send and receive messages in one-to-one and group conversations.",
            "Deliver in real time to online recipients; queue for offline ones.",
            "Show sent, delivered, and read receipts.",
            "Persist and paginate conversation history.",
        ],
        "non_functional_requirements": [
            "Message delivery under 500ms for online users.",
            "Messages must not be lost, and must not be shown out of order.",
            "Support tens of millions of concurrent connections.",
            "Exactly-once display, even if delivery is retried.",
        ],
        "capacity_estimation": [
            {
                "metric": "Concurrent connections",
                "assumption": "50M DAU, 20% connected at peak",
                "working": "10M concurrent WebSockets; ~50K per server",
                "result": "~200 connection servers",
            },
            {
                "metric": "Message QPS",
                "assumption": "50M users x 40 messages/day",
                "working": "2e9 / 86400 = ~23,000 messages/sec, ~70K peak",
                "result": "~23K writes/sec",
            },
            {
                "metric": "Storage per year",
                "assumption": "~300 bytes per message including metadata",
                "working": "2e9 x 365 x 300B = ~220TB/year",
                "result": "~220TB/year — tiering old messages matters",
            },
        ],
        "expected_components": [
            NodeKind.CLIENT, NodeKind.LOAD_BALANCER, NodeKind.APP_SERVER,
            NodeKind.PUB_SUB, NodeKind.CACHE, NodeKind.NOSQL_DATABASE,
            NodeKind.MESSAGE_QUEUE, NodeKind.OBJECT_STORAGE,
        ],
        "api_design_md": (
            "History is REST; the live path is a WebSocket:\n\n"
            "```\n"
            "GET /api/v1/conversations/{id}/messages?before=  -> page of history\n"
            "WS  /ws   { type: 'send', conversation_id, client_msg_id, text }\n"
            "          { type: 'ack',  client_msg_id, server_msg_id, seq }\n"
            "          { type: 'message', ... }   (server push)\n"
            "```\n\n"
            "The `client_msg_id` is what makes retries safe. A client that resends after a "
            "timeout must not create a duplicate message, and the server dedupes on that id."
        ),
        "data_model_md": (
            "```\n"
            "messages(conversation_id PARTITION KEY, seq CLUSTERING KEY,\n"
            "         sender_id, body, created_at, client_msg_id)\n"
            "conversation_members(conversation_id, user_id, last_read_seq)\n"
            "```\n\n"
            "Partitioning by conversation and clustering by a per-conversation sequence "
            "number gives you the two things this system needs: history reads are a single "
            "partition scan, and ordering is well-defined without relying on clocks.\n\n"
            "Read state is one integer per member — `last_read_seq`. Storing a per-message "
            "read flag would multiply your write volume by the group size for no benefit."
        ),
        "architecture_md": (
            "Clients hold WebSockets to connection servers behind an L4 load balancer. A "
            "session registry (Redis) maps `user_id -> connection_server`, so any server "
            "can find where a recipient is connected.\n\n"
            "Sending a message: the connection server persists it, assigns the next `seq` "
            "for that conversation, acknowledges the sender, then looks up each recipient "
            "and forwards. Recipients on other servers are reached via pub/sub rather than "
            "direct server-to-server calls — that keeps servers from needing a full mesh.\n\n"
            "**Ordering.** Do not order by wall-clock timestamp; clocks disagree across "
            "servers and two messages can land in the same millisecond. A per-conversation "
            "sequence number, assigned server-side, gives a total order within the only "
            "scope where order actually matters.\n\n"
            "**Offline delivery.** If the registry shows no connection, persist and let the "
            "recipient pull on reconnect. The client sends its last seen `seq`, and the "
            "server returns everything after it — the same mechanism also repairs any "
            "message dropped by a flaky connection."
        ),
        "scaling_md": (
            "Connection servers are the constrained resource: each holds tens of thousands "
            "of open sockets, so memory and file descriptors bound the fleet, not CPU.\n\n"
            "Shard messages by conversation. Conversations are independent, so this scales "
            "cleanly and keeps every history read on one shard.\n\n"
            "Tier storage by age. Recent messages belong in a hot store; a year-old "
            "conversation can live in cheaper storage with a slower read path, because "
            "almost nobody scrolls back that far.\n\n"
            "Group messages need a fanout limit. A 10,000-member group turns one send into "
            "10,000 deliveries — that path belongs on a queue, not inline."
        ),
        "tradeoffs_md": (
            "**WebSocket versus long polling.** WebSockets are the right answer but they "
            "make servers stateful, which complicates deploys — you cannot drain a server "
            "without dropping connections, so you need reconnect-with-resume on the client "
            "regardless.\n\n"
            "**Read receipts are more expensive than they look.** In a large group they are "
            "a write per member per message. A last-read pointer per member is the standard "
            "compromise, at the cost of not knowing precisely who read what.\n\n"
            "**End-to-end encryption changes the design.** Server-side search and "
            "server-generated previews stop being possible, and multi-device key management "
            "becomes a significant subsystem. Flag it as a scope question rather than "
            "silently assuming it away."
        ),
    },
    {
        "slug": "design-a-video-streaming-platform",
        "title": "Design a Video Streaming Platform",
        "difficulty": Difficulty.HARD,
        "order_index": 5,
        "sheet_tier": 25,
        "is_free_preview": False,
        "estimated_minutes": 55,
        "tags": ["cdn", "transcoding", "object-storage", "bandwidth"],
        "companies": ["Netflix", "YouTube", "Amazon"],
        "summary": "Upload, transcode, and stream video to a global audience.",
        "description_md": (
            "Design a platform where users upload videos and others watch them, worldwide, "
            "without buffering.\n\n"
            "Unlike most systems in this set, the bottleneck here is bandwidth and storage "
            "rather than QPS. The design questions are about moving very large objects "
            "close to viewers and doing expensive CPU work off the request path."
        ),
        "functional_requirements": [
            "Upload a video and make it available for playback.",
            "Stream at a resolution appropriate to the viewer's bandwidth.",
            "Search videos by title and metadata.",
            "Record view counts and playback position.",
        ],
        "non_functional_requirements": [
            "Playback starts within 2 seconds.",
            "Minimal rebuffering across varied network conditions.",
            "Durable storage — an uploaded video must never be lost.",
            "Upload availability may be lower than playback availability.",
        ],
        "capacity_estimation": [
            {
                "metric": "Upload volume",
                "assumption": "500 hours uploaded per minute, ~1GB per hour raw",
                "working": "500GB/min = ~8.3GB/sec ingest",
                "result": "~720TB/day of raw uploads",
            },
            {
                "metric": "Storage with transcoding",
                "assumption": "5 renditions, ~1.5x the original in total",
                "working": "720TB x 1.5 x 365 = ~394PB/year",
                "result": "Hundreds of petabytes per year",
            },
            {
                "metric": "Peak egress",
                "assumption": "10M concurrent viewers at 3 Mbps average",
                "working": "10e6 x 3 Mbps = 30 Tbps",
                "result": "~30 Tbps — only a CDN makes this affordable",
            },
        ],
        "expected_components": [
            NodeKind.CLIENT, NodeKind.CDN, NodeKind.LOAD_BALANCER,
            NodeKind.APP_SERVER, NodeKind.OBJECT_STORAGE, NodeKind.MESSAGE_QUEUE,
            NodeKind.WORKER, NodeKind.SEARCH_INDEX, NodeKind.NOSQL_DATABASE,
        ],
        "api_design_md": (
            "```\n"
            "POST /api/v1/videos              -> { video_id, upload_url }\n"
            "PUT  {upload_url}                -> direct upload to object storage\n"
            "GET  /api/v1/videos/{id}         -> metadata + manifest URL\n"
            "GET  /manifest/{id}.m3u8         -> adaptive bitrate manifest\n"
            "```\n\n"
            "Upload goes straight from the client to object storage via a presigned URL. "
            "Proxying multi-gigabyte files through your application servers wastes bandwidth "
            "and ties up a worker for the entire transfer."
        ),
        "data_model_md": (
            "```\n"
            "videos(video_id PK, uploader_id, title, description, status, duration, created_at)\n"
            "renditions(video_id, resolution, bitrate, storage_key, segment_count)\n"
            "view_events(video_id, user_id, position, watched_at)   -- append-only\n"
            "```\n\n"
            "`status` drives the upload lifecycle: uploaded, transcoding, ready, failed. "
            "The client polls or subscribes to it, because a video is not watchable the "
            "moment the bytes land."
        ),
        "architecture_md": (
            "Two decoupled pipelines.\n\n"
            "**Ingest.** Client uploads directly to object storage; completion enqueues a "
            "transcoding job. Workers split the video into segments, encode each into "
            "multiple resolutions, and write an HLS or DASH manifest. Segment-level "
            "parallelism is what makes transcoding a long video tractable — the segments "
            "are independent, so the work fans out across many workers.\n\n"
            "**Playback.** The client fetches the manifest, then pulls segments from the "
            "CDN. Adaptive bitrate is a client-side decision: it measures throughput and "
            "picks the next segment's rendition accordingly, which is why a viewer on a "
            "degrading connection sees quality drop instead of a stall.\n\n"
            "Origin servers should serve almost no video. If your CDN hit rate is not very "
            "high, the economics of this system do not work."
        ),
        "scaling_md": (
            "Transcoding is embarrassingly parallel and bursty — the right shape for a "
            "queue plus an autoscaling worker pool, and a strong case for spot instances "
            "given that a lost job is simply retried.\n\n"
            "Prioritize the queue. A 30-second clip should not wait behind a feature film; "
            "separate queues by expected duration so short uploads stay fast.\n\n"
            "Popularity is extremely skewed. Pre-push anticipated hits to edge caches, and "
            "let the long tail be pulled on demand and evicted normally.\n\n"
            "Move cold content to cheaper storage tiers. Most videos are watched heavily "
            "for days and then almost never again."
        ),
        "tradeoffs_md": (
            "**Transcode everything up front, or on demand?** Up front costs storage for "
            "renditions nobody watches; on demand adds latency to the first view. A common "
            "compromise is eager transcoding of common resolutions and lazy generation of "
            "the rest.\n\n"
            "**View counts cannot be exact at this volume.** Counting every play "
            "synchronously is a write per view. Aggregate from an event stream and accept "
            "that the number is a few minutes stale.\n\n"
            "**CDN cost is the dominant line item.** Multi-CDN improves resilience and "
            "negotiating position but adds real operational complexity — worth raising as "
            "a business-aware tradeoff rather than a purely technical one."
        ),
    },
    {
        "slug": "design-a-notification-system",
        "title": "Design a Notification System",
        "difficulty": Difficulty.MEDIUM,
        "order_index": 6,
        "sheet_tier": 25,
        "is_free_preview": False,
        "estimated_minutes": 40,
        "tags": ["queues", "fanout", "third-party-apis", "idempotency"],
        "companies": ["Uber", "Airbnb", "Amazon"],
        "summary": "Deliver push, email, and SMS reliably across providers.",
        "description_md": (
            "Design a service other teams call to notify users across push, email, and SMS.\n\n"
            "Most of the difficulty is that delivery depends on third parties you do not "
            "control and cannot retry blindly — a retried payment alert that sends twice is "
            "a real user-facing problem."
        ),
        "functional_requirements": [
            "Send notifications over push, email, and SMS.",
            "Respect per-user channel preferences and quiet hours.",
            "Support templated content with per-user variables.",
            "Track delivery status and expose it to calling services.",
        ],
        "non_functional_requirements": [
            "At-least-once delivery with de-duplication at the edge.",
            "A failing provider must not block other channels.",
            "Handle bursts far above steady-state volume.",
            "Never send to a user who opted out.",
        ],
        "capacity_estimation": [
            {
                "metric": "Send volume",
                "assumption": "10M notifications/day, 5x burst on campaigns",
                "working": "10e6 / 86400 = ~116/sec steady, ~600/sec burst",
                "result": "Low steady QPS, high burst — queue-shaped",
            },
            {
                "metric": "Retry amplification",
                "assumption": "2% failure rate, up to 3 retries",
                "working": "10e6 x 0.02 x 3 = 600K extra sends/day",
                "result": "~6% overhead — budget for it",
            },
        ],
        "expected_components": [
            NodeKind.API_GATEWAY, NodeKind.APP_SERVER, NodeKind.MESSAGE_QUEUE,
            NodeKind.WORKER, NodeKind.CACHE, NodeKind.SQL_DATABASE, NodeKind.MONITORING,
        ],
        "api_design_md": (
            "```\n"
            "POST /api/v1/notifications\n"
            "  { user_id, template_id, variables, channels[], idempotency_key }\n"
            "  -> { notification_id, status: 'queued' }\n"
            "GET /api/v1/notifications/{id}  -> per-channel delivery status\n"
            "```\n\n"
            "`idempotency_key` is required, not optional. Calling services retry on timeout, "
            "and without a key you cannot tell a retry from a second genuine request."
        ),
        "data_model_md": (
            "```\n"
            "notifications(id PK, user_id, template_id, payload, idempotency_key UNIQUE,\n"
            "              created_at)\n"
            "deliveries(id PK, notification_id, channel, provider, status, attempts,\n"
            "           last_error, updated_at)\n"
            "preferences(user_id, channel, enabled, quiet_hours_start, quiet_hours_end)\n"
            "```\n\n"
            "One notification, many deliveries — one per channel. They succeed and fail "
            "independently, so they need independent status."
        ),
        "architecture_md": (
            "The API validates, de-duplicates on the idempotency key, persists, and enqueues. "
            "It does not call providers — a synchronous provider call would make your API's "
            "latency and availability a function of theirs.\n\n"
            "Use a queue per channel. Push, email, and SMS have completely different "
            "throughput and failure characteristics, and a backed-up SMS provider should "
            "not delay push notifications.\n\n"
            "Workers check preferences and quiet hours, render the template, call the "
            "provider, and record the outcome. Provider webhooks update delivery status "
            "asynchronously — the provider accepting a message is not the same as the user "
            "receiving it.\n\n"
            "Wrap each provider in a circuit breaker. When one starts failing, stop calling "
            "it, fail fast, and either fall back to a secondary provider or park the work "
            "until it recovers."
        ),
        "scaling_md": (
            "Bursts are the normal case here — a campaign is 100x steady state. The queue "
            "absorbs it and workers autoscale on queue depth.\n\n"
            "Respect provider rate limits per provider, not globally, or one noisy tenant "
            "gets everyone throttled.\n\n"
            "Give every queue a dead-letter queue. Notifications that exhaust retries must "
            "land somewhere a human can inspect, rather than vanishing.\n\n"
            "Cache preferences aggressively — they are read on every send and change rarely."
        ),
        "tradeoffs_md": (
            "**At-least-once versus at-most-once.** At-least-once plus idempotency is almost "
            "always right, but the de-duplication window is a real decision: too short and "
            "a delayed retry duplicates, too long and a legitimate repeat gets swallowed.\n\n"
            "**Priority matters.** A password reset and a marketing blast should not share a "
            "queue. Separate them, or the campaign delays the thing the user is waiting on.\n\n"
            "**Quiet hours need a timezone, and users travel.** Deciding whether to use the "
            "profile timezone or the last known location is a genuine product question worth "
            "surfacing rather than assuming."
        ),
    },
]
