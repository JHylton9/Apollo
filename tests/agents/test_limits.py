from types import SimpleNamespace

import pytest
from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.messages import AIMessage

from apollo.agents.coordinator import build_coordinator
from apollo.agents.delegation import build_delegation_tools
from apollo.agents.session import ApolloSession, approve
from apollo.middleware import coordinator_middleware
from apollo.middleware.limits import SUMMARY_PROMPT
from apollo.retrieval.tables import FineRecord
from apollo.tools import _runtime

from .fakes import scripted

EMAIL = {"to": "traffic.department@jcf.gov.jm", "subject": "Notice", "body": "Stop sign."}


@pytest.fixture(autouse=True)
def fake_runtime(monkeypatch, tmp_path):
    fines = [FineRecord(115, "Driving Without Licence", 40000, 14, "Section 20(4)", 3)]
    records = SimpleNamespace(fines=fines, divisions=[], murder_counts={})
    monkeypatch.setattr(_runtime, "get_records", lambda: records)
    monkeypatch.setattr(_runtime, "get_settings", lambda: SimpleNamespace(actions_dir=tmp_path))
    return tmp_path


def _call(name, args, call_id):
    return {"name": name, "args": args, "id": call_id}


def _session(*coordinator, specialist=(), delegation=False):
    tools = build_delegation_tools(scripted(*specialist)) if delegation else []
    agent = build_coordinator(
        scripted(*coordinator),
        delegation_tools=tools,
        middleware=coordinator_middleware(
            summary_model=scripted(*[AIMessage(content="SUMMARY") for _ in range(20)]),
            retry_delay=0,
        ),
    )
    return ApolloSession(agent, "limits")


def test_a_looping_specialist_is_stopped_and_reported() -> None:
    # The specialist calls the calculator forever; its model-call limit (8) ends the loop.
    loop = [
        AIMessage(content="", tool_calls=[_call("calculate", {"expression": "1+1"}, f"c{i}")])
        for i in range(20)
    ]
    session = _session(
        AIMessage(content="", tool_calls=[_call("ask_traffic_specialist", {"task": "x"}, "d1")]),
        AIMessage(content="The specialist could not finish this request."),
        specialist=loop,
        delegation=True,
    )
    turn = session.ask("Calculate something")
    assert turn.answer == "The specialist could not finish this request."
    [event] = [e for e in turn.middleware_events if e["middleware"].endswith("LimitMiddleware")]
    assert event["subagent"] == "traffic_fine_specialist"
    assert turn.delegations[0]["tool_calls"].count("calculate") <= 10


def test_too_many_actions_are_blocked_before_review(fake_runtime) -> None:
    emails = [_call("notify_email", EMAIL, f"e{i}") for i in range(4)]
    session = _session(AIMessage(content="", tool_calls=emails), AIMessage(content="unused"))
    turn = session.ask("Send four emails")
    assert not turn.awaiting_review  # the officer is never asked to review a blocked call
    assert turn.middleware_events[0]["middleware"] == "ToolCallLimitMiddleware"
    assert "notify_email" in turn.middleware_events[0]["detail"]
    assert not (fake_runtime / "outbox.jsonl").exists()


def test_actions_within_the_cap_still_go_to_review(fake_runtime) -> None:
    emails = [_call("notify_email", EMAIL, f"e{i}") for i in range(2)]
    session = _session(AIMessage(content="", tool_calls=emails), AIMessage(content="Sent."))
    turn = session.ask("Send two emails")
    assert len(turn.pending) == 2
    assert session.review([approve(), approve()]).answer == "Sent."


def test_no_answer_is_lost_when_history_is_summarized() -> None:
    # A tiny trigger forces summarization on every few turns.
    replies = [AIMessage(content=f"Answer {i}") for i in range(8)]
    agent = build_coordinator(
        scripted(*replies),
        delegation_tools=[],
        middleware=[
            SummarizationMiddleware(
                scripted(*[AIMessage(content="SUMMARY")] * 8),
                trigger=("messages", 6),
                keep=("messages", 2),
            )
        ],
    )
    session = ApolloSession(agent, "summary")
    turns = [session.ask(f"Question {i}") for i in range(6)]
    assert [t.answer for t in turns] == [f"Answer {i}" for i in range(6)]
    assert any(
        e["middleware"] == "SummarizationMiddleware" for t in turns for e in t.middleware_events
    )
    history = agent.get_state(session.config).values["messages"]
    assert len(history) < 12  # older messages were replaced by a summary


def test_summary_prompt_protects_facts_officers_act_on() -> None:
    for must_keep in ("fine amount", "demerit point", "reference number", "approved, edited"):
        assert must_keep in SUMMARY_PROMPT
    assert "{messages}" in SUMMARY_PROMPT
