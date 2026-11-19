"""Tool error recovery: turn expected tool failures into feedback the model can act on."""

from __future__ import annotations

from typing import Any

from langchain.agents.middleware import ToolErrorMiddleware
from langchain_core.messages import ToolMessage

# Every message this middleware produces starts with this, which tells its errors apart
# from other error ToolMessages (for example a HITL rejection is also status="error").
ERROR_PREFIX = "Tool error in"


def tool_error_feedback(error: Exception, request) -> str | None:
    """Return model-readable feedback for expected errors; None lets the error propagate."""
    name = request.tool_call["name"]
    if isinstance(error, ValueError):
        # Our tools raise ValueError for invalid input, with a message written for the model.
        return (
            f"{ERROR_PREFIX} `{name}` (invalid input): {error} "
            "Correct the input and try again if you can; otherwise tell the user plainly "
            "that this request could not be completed and why."
        )
    if isinstance(error, FileNotFoundError):
        # Missing ingested data: name the problem without exposing file system paths.
        return (
            f"{ERROR_PREFIX} `{name}`: the required JCF data has not been ingested on this "
            "system. Tell the user the information is temporarily unavailable."
        )
    return None


def build_tool_error_middleware() -> ToolErrorMiddleware:
    return ToolErrorMiddleware(tool_error_feedback)


def is_handled_tool_error(message: Any) -> bool:
    """True if `message` is feedback produced by this module's ToolErrorMiddleware."""
    return (
        isinstance(message, ToolMessage)
        and message.status == "error"
        and str(message.content).startswith(ERROR_PREFIX)
    )
