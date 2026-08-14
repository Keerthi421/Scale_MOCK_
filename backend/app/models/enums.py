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
