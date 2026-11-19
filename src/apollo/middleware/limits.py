"""Bounds on how much work one request may do, and compression of long conversations."""

from __future__ import annotations

from langchain.agents.middleware import (
    ModelCallLimitMiddleware,
    SummarizationMiddleware,
    ToolCallLimitMiddleware,
)
from langchain_core.language_models import BaseChatModel

from apollo.tools import HIGH_RISK_TOOL_NAMES

# Phrases in the library-generated final message when a limit ends a run (for telemetry).
# The per-tool variant starts with the tool's name, so match anywhere, ignoring case.
LIMIT_PHRASES = {
    "tool call limit reached": "ToolCallLimitMiddleware",
    "model call limits exceeded": "ModelCallLimitMiddleware",
}


def limit_hit(text: str) -> str | None:
    """The name of the limit middleware that produced `text`, if any."""
    lowered = text.casefold()
    return next((name for phrase, name in LIMIT_PHRASES.items() if phrase in lowered), None)


# Summaries must not blur facts an officer may act on, so the prompt says what to keep.
SUMMARY_PROMPT = """You are compressing the history of a Jamaica Constabulary Force public
safety assistant conversation so that it can continue within its context limit.

Write a short factual summary. Preserve exactly, without rounding or paraphrasing:
- every fine amount, demerit point value and Road Traffic Act section or regulation;
- every crime figure, change and percentage, with its division and year;
- every action reference number (FN-, EM-, SR-) and whether the officer approved, edited,
  rejected or answered it;
- any question from the user that is still unanswered.
Do not add information, and do not include personal data.

Messages to summarize:
{messages}"""


def build_model_call_limit(model_calls: int) -> ModelCallLimitMiddleware:
    return ModelCallLimitMiddleware(run_limit=model_calls, exit_behavior="end")


def build_tool_call_limits(tool_calls: int, per_action: int | None = None) -> list:
    limits: list = [ToolCallLimitMiddleware(run_limit=tool_calls, exit_behavior="end")]
    if per_action is not None:
        limits += [
            ToolCallLimitMiddleware(tool_name=name, run_limit=per_action, exit_behavior="end")
            for name in sorted(HIGH_RISK_TOOL_NAMES)
        ]
    return limits


def build_summarization_middleware(model: BaseChatModel) -> SummarizationMiddleware:
    return SummarizationMiddleware(
        model,
        trigger=("tokens", 6000),  # summarise once the history passes about 6,000 tokens
        keep=("messages", 12),  # always keep the most recent messages word for word
        summary_prompt=SUMMARY_PROMPT,
    )
