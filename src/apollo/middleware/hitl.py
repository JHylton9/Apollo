"""Human-in-the-loop gate for the high-risk action tools."""

from __future__ import annotations

from typing import Any, cast

from langchain.agents.middleware import HumanInTheLoopMiddleware

from apollo.tools import HIGH_RISK_TOOL_NAMES

ALL_DECISIONS = ["approve", "edit", "reject", "respond"]

REVIEW_DESCRIPTIONS = {
    "issue_fine_notice": "Issue an official traffic violation notice",
    "notify_email": "Send an official JCF email",
    "log_sighting_report": "Log a wanted-person sighting report",
}


def build_hitl_middleware() -> HumanInTheLoopMiddleware:
    missing = HIGH_RISK_TOOL_NAMES - REVIEW_DESCRIPTIONS.keys()
    if missing:
        # Fail at start-up rather than let a new high-risk tool run unreviewed.
        raise RuntimeError(f"No review configuration for high-risk tools: {sorted(missing)}")
    return HumanInTheLoopMiddleware(
        interrupt_on=cast(Any, {
            name: {"allowed_decisions": ALL_DECISIONS, "description": REVIEW_DESCRIPTIONS[name]}
            for name in sorted(HIGH_RISK_TOOL_NAMES)
        }),
        description_prefix="Officer review required",
    )