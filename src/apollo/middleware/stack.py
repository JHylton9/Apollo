"""The middleware stacks, defined in one place so their order is explicit and tested."""

from __future__ import annotations

from apollo.middleware.errors import build_tool_error_middleware
from apollo.middleware.hitl import build_hitl_middleware
from apollo.middleware.pii import build_pii_middleware
from apollo.middleware.resilience import (
    build_model_retry_middleware,
    build_tool_retry_middleware,
)


def coordinator_middleware(retry_delay: float = 1.0) -> list:
    return [
        *build_pii_middleware(),
        build_model_retry_middleware(retry_delay),
        build_hitl_middleware(),
        build_tool_error_middleware(),
        build_tool_retry_middleware(retry_delay / 2),
    ]


def specialist_middleware(retry_delay: float = 1.0) -> list:
    # Specialists only read data, so they need no HITL gate.
    return [
        *build_pii_middleware(),
        build_model_retry_middleware(retry_delay),
        build_tool_error_middleware(),
        build_tool_retry_middleware(retry_delay / 2),
    ]
