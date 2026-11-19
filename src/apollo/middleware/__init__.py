"""Middleware: PII redaction, HITL gate, tool error recovery (retries and limits next)."""

from apollo.middleware.errors import build_tool_error_middleware
from apollo.middleware.hitl import build_hitl_middleware
from apollo.middleware.pii import build_pii_middleware, redact_text
from apollo.middleware.stack import coordinator_middleware, specialist_middleware

__all__ = [
    "build_hitl_middleware",
    "build_pii_middleware",
    "build_tool_error_middleware",
    "coordinator_middleware",
    "redact_text",
    "specialist_middleware",
]
