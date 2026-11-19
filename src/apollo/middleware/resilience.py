"""Retries with exponential backoff for transient failures."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable

import openai
from langchain.agents.middleware import ModelRetryMiddleware, ToolRetryMiddleware
from langchain_core.tools import BaseTool

from apollo.tools.retrieval import RETRIEVAL_TOOLS

logger = logging.getLogger("apollo.resilience")

# Network problems, rate limits and 5xx server errors may succeed on a later attempt.
# 4xx errors such as a wrong key or a missing deployment never will. (APITimeoutError
# is a subclass of APIConnectionError, so timeouts are included.)
TRANSIENT_MODEL_ERRORS = (
    openai.APIConnectionError,
    openai.RateLimitError,
    openai.InternalServerError,
)

# Chroma stores its index in SQLite; a briefly locked database is worth retrying.
TRANSIENT_TOOL_ERRORS = (TimeoutError, ConnectionError, sqlite3.OperationalError)

# Only read-only tools are retried. Retrying a high-risk action (a fine notice, an email)
# after an unclear failure could perform it twice, so actions are never in this list.
RETRYABLE_TOOLS: list[BaseTool | str] = [tool.name for tool in RETRIEVAL_TOOLS]


def _transient(kinds: tuple[type[Exception], ...], what: str) -> Callable[[Exception], bool]:
    def should_retry(error: Exception) -> bool:
        retry = isinstance(error, kinds)
        if retry:
            logger.warning(
                "%s failed (%s): transient error, retrying with backoff if attempts remain",
                what,
                type(error).__name__,
            )
        return retry

    return should_retry


def _model_unavailable(error: Exception) -> str:
    # Shown to the user after the last attempt; it names no internal detail.
    return (
        "The AI service is temporarily unavailable after several attempts. "
        "Please try again in a moment."
    )


def _search_unavailable(error: Exception) -> str:
    return (
        "The JCF document search is temporarily unavailable after several attempts. "
        "Tell the user this information cannot be retrieved right now."
    )


def build_model_retry_middleware(initial_delay: float = 1.0) -> ModelRetryMiddleware:
    return ModelRetryMiddleware(
        max_retries=3,  # 4 attempts in all, waiting about 1s, 2s, then 4s
        retry_on=_transient(TRANSIENT_MODEL_ERRORS, "Model call"),
        on_failure=_model_unavailable,
        backoff_factor=2.0,
        initial_delay=initial_delay,
        max_delay=10.0,
        jitter=True,
    )


def build_tool_retry_middleware(initial_delay: float = 0.5) -> ToolRetryMiddleware:
    return ToolRetryMiddleware(
        max_retries=2,
        tools=RETRYABLE_TOOLS,
        retry_on=_transient(TRANSIENT_TOOL_ERRORS, "Tool call"),
        on_failure=_search_unavailable,
        backoff_factor=2.0,
        initial_delay=initial_delay,
        max_delay=5.0,
        jitter=True,
    )
