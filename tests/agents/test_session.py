import json
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage

from apollo.agents.coordinator import build_coordinator
from apollo.agents.delegation import build_delegation_tools
from apollo.agents.session import ApolloSession, approve, edit, reject
from apollo.middleware import build_hitl_middleware
from apollo.retrieval.tables import CategoryChange, DivisionStats, FineRecord
from apollo.tools import _runtime

from .fakes import scripted


@pytest.fixture(autouse=True)
def fake_runtime(monkeypatch, tmp_path):
    records = SimpleNamespace(
        fines=[FineRecord(15, "Disobeying Stop Sign", 10000, 6, "Section 52(2)(a)", 1)],
        divisions=[DivisionStats("Kingston Central", {"murder": CategoryChange(1, 1)}, ())],
        murder_counts={},
    )
    monkeypatch.setattr(_runtime, "get_records", lambda: records)
    monkeypatch.setattr(_runtime, "get_settings", lambda: SimpleNamespace(actions_dir=tmp_path))
    return tmp_path


def _calls(*calls):
    return AIMessage(
        content="",
        tool_calls=[{"name": n, "args": a, "id": f"c{i}"} for i, (n, a) in enumerate(calls)],
    )


NOTICE = {"section": "52(2)(a)", "offence": "disobeyed stop sign", "location": "Kingston"}
EMAIL = {"to": "traffic.department@jcf.gov.jm", "subject": "Notice", "body": "Stop sign."}


def _session(*coordinator_messages, specialist=()):
    agent = build_coordinator(
        scripted(*coordinator_messages),
        delegation_tools=build_delegation_tools(scripted(*specialist)),
        middleware=[build_hitl_middleware()],
    )
    return ApolloSession(agent, thread_id="test")


def test_plain_question_reports_delegation_and_citations() -> None:
    session = _session(
        _calls(("ask_traffic_specialist", {"task": "Fine for 52(2)(a)?"})),
        AIMessage(content="$10,000 and 6 points."),
        specialist=(
            _calls(("lookup_traffic_fine", {"section": "52(2)(a)"})),
            AIMessage(content="$10,000, 6 points. Sources: JCF-Fines.pdf p1"),
        ),
    )
    turn = session.ask("What is the stop sign fine?")
    assert turn.answer == "$10,000 and 6 points."
    assert not turn.awaiting_review
    assert turn.delegations[0]["subagent"] == "traffic_fine_specialist"
    assert turn.citations == [{"source": "JCF-Fines.pdf", "page": 1, "pipeline": "docling-table"}]


def test_two_actions_pause_together_and_resume_in_order(fake_runtime) -> None:
    # Spec test case: issue a stop-sign notice and email the traffic department.
    session = _session(
        _calls(("issue_fine_notice", NOTICE), ("notify_email", EMAIL)),
        AIMessage(content="Notice issued; the email was not sent."),
    )
    turn = session.ask("Issue a stop sign notice and notify the traffic department.")
    assert turn.answer is None
    assert [a.name for a in turn.pending] == ["issue_fine_notice", "notify_email"]

    turn = session.review([approve(), reject("Department already informed by phone.")])
    assert turn.answer == "Notice issued; the email was not sent."
    assert (fake_runtime / "fine_notices.jsonl").exists()
    assert not (fake_runtime / "outbox.jsonl").exists()
    assert session.pending == []
    assert turn.middleware_events == [
        {
            "middleware": "HumanInTheLoopMiddleware",
            "tool": "issue_fine_notice",
            "decision": "approve",
        },
        {"middleware": "HumanInTheLoopMiddleware", "tool": "notify_email", "decision": "reject"},
    ]


def test_edit_decision_changes_what_is_recorded(fake_runtime) -> None:
    session = _session(
        _calls(("notify_email", EMAIL)),
        AIMessage(content="Email sent."),
    )
    session.ask("Email the traffic department.")
    corrected = {**EMAIL, "subject": "Stop sign notice FN-1"}
    session.review([edit("notify_email", corrected)])
    sent = json.loads((fake_runtime / "outbox.jsonl").read_text())
    assert sent["subject"] == "Stop sign notice FN-1"


def test_review_rules_are_enforced() -> None:
    session = _session(_calls(("notify_email", EMAIL)), AIMessage(content="Sent."))
    with pytest.raises(RuntimeError):
        session.review([approve()])  # nothing pending yet
    session.ask("Email the traffic department.")
    with pytest.raises(RuntimeError):
        session.ask("Another question")  # must review first
    with pytest.raises(ValueError):
        session.review([approve(), approve()])  # wrong number of decisions
