from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from apollo.agents.coordinator import build_coordinator
from apollo.agents.delegation import build_delegation_tools
from apollo.agents.session import ApolloSession
from apollo.agents.subagents import build_traffic_specialist
from apollo.middleware import build_hitl_middleware, build_tool_error_middleware
from apollo.middleware.errors import is_handled_tool_error, tool_error_feedback
from apollo.tools import _runtime

from .fakes import scripted

INVALID = {"section": "invalid_section_code_9999"}


@pytest.fixture(autouse=True)
def fake_records(monkeypatch):
    records = SimpleNamespace(fines=[], divisions=[], murder_counts={})
    monkeypatch.setattr(_runtime, "get_records", lambda: records)


def _lookup(args, call_id="c1"):
    return AIMessage(
        content="", tool_calls=[{"name": "lookup_traffic_fine", "args": args, "id": call_id}]
    )


def _request(name="lookup_traffic_fine"):
    return SimpleNamespace(tool_call={"name": name})


def test_feedback_is_given_only_for_expected_errors() -> None:
    feedback = tool_error_feedback(ValueError("bad section"), _request())
    assert feedback is not None
    assert "invalid input" in feedback
    feedback = tool_error_feedback(FileNotFoundError("/x/y.json"), _request())
    assert feedback is not None
    assert "not been ingested" in feedback
    assert "/x/y.json" not in feedback
    assert tool_error_feedback(KeyError("internal bug"), _request()) is None


def test_specialist_recovers_instead_of_crashing() -> None:
    # Spec test case: "Query the traffic fines database for invalid_section_code_9999".
    model = scripted(
        _lookup(INVALID),
        AIMessage(content="invalid_section_code_9999 is not a valid section code."),
    )
    result = build_traffic_specialist(model).invoke(
        {"messages": [{"role": "user", "content": "Look up invalid_section_code_9999"}]}
    )
    error = next(m for m in result["messages"] if isinstance(m, ToolMessage))
    assert error.status == "error"
    assert "not a valid Road Traffic Act section" in error.content
    # The model saw the error and could answer, instead of the run crashing.
    assert result["messages"][-1].content.startswith("invalid_section_code_9999 is not a valid")


def test_unexpected_errors_still_propagate(monkeypatch) -> None:
    def broken():
        raise KeyError("internal bug")

    monkeypatch.setattr(_runtime, "get_records", broken)
    model = scripted(_lookup({"section": "20(4)"}), AIMessage(content="unused"))
    with pytest.raises(KeyError):
        build_traffic_specialist(model).invoke({"messages": [{"role": "user", "content": "q"}]})


def test_error_inside_specialist_is_reported_to_the_session() -> None:
    specialist = scripted(_lookup(INVALID), AIMessage(content="That section code is invalid."))
    coordinator = scripted(
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "ask_traffic_specialist",
                    "args": {"task": "Fine for invalid_section_code_9999"},
                    "id": "d1",
                }
            ],
        ),
        AIMessage(content="That is not a valid section code, so no fine can be found."),
    )
    agent = build_coordinator(
        coordinator,
        delegation_tools=build_delegation_tools(specialist),
        middleware=[build_hitl_middleware(), build_tool_error_middleware()],
    )
    turn = ApolloSession(agent, "errors").ask(
        "Query the fines database for invalid_section_code_9999"
    )
    assert turn.answer is not None
    assert turn.answer.startswith("That is not a valid section code")
    assert turn.middleware_events == [
        {
            "middleware": "ToolErrorMiddleware",
            "tool": "lookup_traffic_fine",
            "subagent": "traffic_fine_specialist",
        }
    ]


def test_hitl_rejection_is_not_counted_as_a_tool_error() -> None:
    rejection = ToolMessage(
        content="User rejected the tool call for `notify_email` with reason: duplicate",
        tool_call_id="x",
        name="notify_email",
        status="error",
    )
    assert not is_handled_tool_error(rejection)
