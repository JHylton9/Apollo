import logging

import openai
import pytest
from langchain_core.messages import AIMessage, ToolMessage

from apollo.agents.coordinator import build_coordinator
from apollo.middleware import coordinator_middleware, specialist_middleware
from apollo.middleware.resilience import RETRYABLE_TOOLS
from apollo.models import SearchHit
from apollo.tools import _runtime

from .fakes import ScriptedModel

CALLS = {"model": 0, "search": 0}


class SimulatedOutage(openai.APIConnectionError):
    """An APIConnectionError that needs no HTTP request object, whichever HTTP library
    the installed openai version uses (httpx or httpx2)."""

    def __init__(self) -> None:
        Exception.__init__(self, "simulated network outage")


def _connection_error() -> openai.APIConnectionError:
    return SimulatedOutage()


class FlakyModel(ScriptedModel):
    """Fails with the given errors first, then answers from its script."""

    failures: list = []

    def _generate(self, messages, *args, **kwargs):
        CALLS["model"] += 1
        if self.failures:
            raise self.failures.pop(0)
        return super()._generate(messages, *args, **kwargs)


@pytest.fixture(autouse=True)
def reset():
    CALLS.update(model=0, search=0)


def _agent(model):
    # retry_delay=0 keeps the tests fast; production uses about 1s, 2s, 4s.
    return build_coordinator(
        model, delegation_tools=[], middleware=coordinator_middleware(retry_delay=0)
    )


def _ask(agent, text="Hello"):
    config = {"configurable": {"thread_id": "r"}}
    return agent.invoke({"messages": [{"role": "user", "content": text}]}, config)


def test_transient_model_errors_are_retried(caplog) -> None:
    model = FlakyModel(
        messages=iter([AIMessage(content="Recovered.")]),
        failures=[_connection_error(), _connection_error()],
    )
    with caplog.at_level(logging.WARNING, logger="apollo.resilience"):
        result = _ask(_agent(model))
    assert result["messages"][-1].content == "Recovered."
    assert CALLS["model"] == 3  # two failures, then success
    assert caplog.text.count("retrying with backoff") == 2


def test_permanent_errors_are_not_retried() -> None:
    model = FlakyModel(messages=iter([]), failures=[ValueError("bad request")])
    with pytest.raises(ValueError):
        _ask(_agent(model))
    assert CALLS["model"] == 1  # failed fast, no pointless retries


def test_persistent_outage_ends_with_a_clear_message() -> None:
    model = FlakyModel(messages=iter([]), failures=[_connection_error() for _ in range(4)])
    result = _ask(_agent(model))
    assert CALLS["model"] == 4  # the first attempt plus 3 retries
    assert "temporarily unavailable" in result["messages"][-1].content
    assert "foundry.test" not in result["messages"][-1].content  # no internal detail


def test_read_only_search_is_retried(monkeypatch) -> None:
    hit = SearchHit(text="Wanted: Dave Edwards (Murder)", score=0.9, source="w.pdf", page=1)

    class LockedOnceStore:
        def query(self, *args, **kwargs):
            CALLS["search"] += 1
            if CALLS["search"] == 1:
                raise TimeoutError("index busy")
            return [hit]

    monkeypatch.setattr(_runtime, "get_store", lambda: LockedOnceStore())
    call = {"name": "search_wanted_persons", "args": {"query": "murder"}, "id": "s1"}
    model = FlakyModel(
        messages=iter([AIMessage(content="", tool_calls=[call]), AIMessage(content="Done.")]),
        failures=[],
    )
    result = _ask(_agent(model))
    search_result = next(m for m in result["messages"] if isinstance(m, ToolMessage))
    assert CALLS["search"] == 2
    assert "Dave Edwards" in search_result.content


def test_actions_are_never_retried() -> None:
    assert "search_wanted_persons" in RETRYABLE_TOOLS
    assert not {"issue_fine_notice", "notify_email", "log_sighting_report"} & set(RETRYABLE_TOOLS)


def test_stack_order() -> None:
    assert [m.name for m in coordinator_middleware()] == [
        "PIIMiddleware[email]",
        "PIIMiddleware[trn]",
        "ModelRetryMiddleware",
        "HumanInTheLoopMiddleware",
        "ToolErrorMiddleware",
        "ToolRetryMiddleware",
    ]
    assert "HumanInTheLoopMiddleware" not in [m.name for m in specialist_middleware()]
