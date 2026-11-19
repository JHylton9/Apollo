"""The middleware stacks, defined in one place so their order is explicit and tested."""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel

from apollo.middleware.errors import build_tool_error_middleware
from apollo.middleware.hitl import build_hitl_middleware
from apollo.middleware.limits import (
    build_model_call_limit,
    build_summarization_middleware,
    build_tool_call_limits,
)
from apollo.middleware.pii import build_pii_middleware
from apollo.middleware.resilience import (
    build_model_retry_middleware,
    build_tool_retry_middleware,
)


def coordinator_middleware(summary_model: BaseChatModel, retry_delay: float = 1.0) -> list:
    return [
        *build_pii_middleware(),
        build_summarization_middleware(summary_model),
        build_model_call_limit(10),
        build_model_retry_middleware(retry_delay),
        build_hitl_middleware(),
        *build_tool_call_limits(12, per_action=3),
        build_tool_error_middleware(),
        build_tool_retry_middleware(retry_delay / 2),
    ]


def specialist_middleware(retry_delay: float = 1.0) -> list:
    # Specialists start fresh for every task, so they never need summarization, and
    # they only read data, so they need no HITL gate or per-action limits.
    return [
        *build_pii_middleware(),
        build_model_call_limit(8),
        build_model_retry_middleware(retry_delay),
        *build_tool_call_limits(10),
        build_tool_error_middleware(),
        build_tool_retry_middleware(retry_delay / 2),
    ]
