"""Model package.

Every model must be imported here. Alembic autogenerate and SQLAlchemy's
relationship resolver both walk `Base.metadata`, and a model that is never
imported is invisible to both — which shows up as a mysteriously missing table.
"""

from app.db.base import Base
from app.models.discussion import DiscussionPost, DiscussionVote
from app.models.interview import InterviewEvaluation, InterviewMessage, MockInterview
from app.models.problem import Problem, ProblemRubric, ProblemSolutionRef, TestCase
from app.models.progress import ActivityDay, ProblemAttempt, UserProgress
from app.models.submission import Submission, SubmissionTestResult
from app.models.system_design import (
    ComponentCatalogEntry,
    HldProblemDetail,
    SystemDesignReview,
    SystemDesignWorkspace,
)
from app.models.user import OAuthAccount, RefreshToken, Subscription, User

__all__ = [
    "ActivityDay",
    "Base",
    "ComponentCatalogEntry",
    "DiscussionPost",
    "DiscussionVote",
    "HldProblemDetail",
    "InterviewEvaluation",
    "InterviewMessage",
    "MockInterview",
    "OAuthAccount",
    "Problem",
    "ProblemAttempt",
    "ProblemRubric",
    "ProblemSolutionRef",
    "RefreshToken",
    "Submission",
    "SubmissionTestResult",
    "Subscription",
    "SystemDesignReview",
    "SystemDesignWorkspace",
    "TestCase",
    "User",
    "UserProgress",
]
