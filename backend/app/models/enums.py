"""Shared enumerations.

These are persisted as native Postgres enums. Adding a value requires a
migration — that friction is deliberate, because these drive authorization and
scoring logic.
"""

from enum import StrEnum


class SubscriptionTier(StrEnum):
    FREE = "free"
    PREMIUM = "premium"
    PRO = "pro"


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    TRIALING = "trialing"


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"


class ProblemCategory(StrEnum):
    DSA = "dsa"
    HLD = "hld"
    LLD = "lld"
    FRONTEND = "frontend"


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Language(StrEnum):
    PYTHON = "python"
    JAVA = "java"
    CPP = "cpp"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"


class InterviewStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    EVALUATING = "evaluating"
    FAILED = "failed"


class MessageRole(StrEnum):
    INTERVIEWER = "interviewer"
    CANDIDATE = "candidate"
    SYSTEM = "system"


class NodeKind(StrEnum):
    """Component types available on the architecture canvas.

    The reviewer prompt and the client palette both derive from this, so a
    component the user can place is always one the reviewer understands.
    """

    # Entry points
    CLIENT = "client"
    MOBILE_APP = "mobile_app"
    WEB_APP = "web_app"
    DNS = "dns"
    CDN = "cdn"

    # Traffic management
    LOAD_BALANCER = "load_balancer"
    API_GATEWAY = "api_gateway"
    REVERSE_PROXY = "reverse_proxy"
    RATE_LIMITER = "rate_limiter"

    # Compute
    APP_SERVER = "app_server"
    MICROSERVICE = "microservice"
    WORKER = "worker"
    CRON = "cron"

    # Data
    SQL_DATABASE = "sql_database"
    NOSQL_DATABASE = "nosql_database"
    READ_REPLICA = "read_replica"
    CACHE = "cache"
    OBJECT_STORAGE = "object_storage"
    SEARCH_INDEX = "search_index"
    DATA_WAREHOUSE = "data_warehouse"

    # Asynchronous
    MESSAGE_QUEUE = "message_queue"
    EVENT_STREAM = "event_stream"
    PUB_SUB = "pub_sub"

    # Cross-cutting
    MONITORING = "monitoring"
    LOGGING = "logging"
    AUTH_SERVICE = "auth_service"
    CONFIG_SERVICE = "config_service"

    # Escape hatch so a candidate is never blocked by a missing palette entry.
    CUSTOM = "custom"


class SubmissionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    ACCEPTED = "accepted"
    WRONG_ANSWER = "wrong_answer"
    TIME_LIMIT_EXCEEDED = "time_limit_exceeded"
    MEMORY_LIMIT_EXCEEDED = "memory_limit_exceeded"
    RUNTIME_ERROR = "runtime_error"
    COMPILE_ERROR = "compile_error"
    INTERNAL_ERROR = "internal_error"
