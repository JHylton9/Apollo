import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage

from apollo.agents.coordinator import build_coordinator
from apollo.agents.delegation import build_delegation_tools
from apollo.agents.session import ApolloSession
from apollo.evaluation import phase2
from apollo.middleware import build_hitl_middleware
from apollo.retrieval.tables import CategoryChange, DivisionStats, FineRecord
from apollo.tools import _runtime

CASES = Path(__file__).parents[2] / "benchmarks" / "phase2_cases.json"


@pytest.fixture(autouse=True)
def fake_runtime(monkeypatch, tmp_path):
    records = SimpleNamespace(
        fines=[FineRecord(115, "Driving Without Licence", 40000, 14, "Section 20(4)", 3)],
        divisions=[
            DivisionStats(n, {"murder": CategoryChange(1, 1)}, ())
            for n in ("Kingston Central", "St. Andrew South")
        ],
        murder_counts={},
    )
    monkeypatch.setattr(_runtime, "get_records", lambda: records)
    monkeypatch.setattr(_runtime, "get_settings", lambda: SimpleNamespace(actions_dir=tmp_path))
    return tmp_path


def _scripted(*messages):
    from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

    class Model(GenericFakeChatModel):
        def bind_tools(self, tools, **kwargs):
            return self

    return Model(messages=iter(messages))


def _call(name, args):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": "c1"}])


def test_case_file_covers_every_phase2_spec_test() -> None:
    ids = {case["id"] for case in phase2.load_cases(CASES)}
    assert {"subagent-traffic", "subagent-crime", "hitl-approve", "hitl-edit"} <= ids
    assert {"pii-redaction", "tool-error", "wanted-murder"} <= ids


def test_passing_case_records_delegation_evidence(fake_runtime) -> None:
    def session():
        specialist = _scripted(
            _call("lookup_traffic_fine", {"section": "20(4)"}),
            AIMessage(content="$40,000"),
        )
        agent = build_coordinator(
            _scripted(_call("ask_traffic_specialist", {"task": "20(4)"}), AIMessage("$40,000")),
            delegation_tools=build_delegation_tools(specialist),
        )
        return ApolloSession(agent, "eval")

    case = {
        "id": "t",
        "category": "Subagents",
        "question": "Fine for 20(4)?",
        "expect": {"subagent": "traffic_fine_specialist", "answer_contains": ["40,000"]},
    }
    result = phase2.run_case(case, session, fake_runtime)
    assert result.passed, result.checks
    assert result.delegations[0]["tool_calls"] == ["lookup_traffic_fine"]
    assert result.delegations[0]["answer_chars"] == len("$40,000")


def test_review_policy_edits_and_failures_are_explained(fake_runtime) -> None:
    sighting = {"suspect_name": "Dave Edwards", "location": "Kingston Central"}

    def session():
        agent = build_coordinator(
            _scripted(_call("log_sighting_report", sighting), AIMessage("Logged.")),
            delegation_tools=[],
            middleware=[build_hitl_middleware()],
        )
        return ApolloSession(agent, "eval")

    case = {
        "id": "edit",
        "category": "HITL",
        "question": "Log a sighting",
        "review": {
            "policy": "edit",
            "tool": "log_sighting_report",
            "args": {"location": "St. Andrew South"},
        },
        "expect": {
            "paused_for": ["log_sighting_report"],
            "records": {"sighting_reports": {"division": "St. Andrew South"}},
            "answer_contains": ["Westmoreland"],  # deliberately wrong, to see a failure
        },
    }
    result = phase2.run_case(case, session, fake_runtime)
    assert result.reviews == [{"tool": "log_sighting_report", "decision": "edit"}]
    failed = [c.name for c in result.checks if not c.passed]
    assert failed == ["answer contains 'Westmoreland'"]
    assert not result.passed


def test_crash_is_recorded_not_raised(fake_runtime) -> None:
    def broken():
        raise RuntimeError("model offline")

    result = phase2.run_case({"id": "x", "category": "c", "question": "q"}, broken, fake_runtime)
    assert result.error == "RuntimeError: model offline" and not result.passed


def test_report_includes_quarantine_totals(fake_runtime) -> None:
    result = phase2.CaseResult("t", "Subagents", "q", passed=True, answer="ok")
    result.delegations = [
        {
            "subagent": "s",
            "tool_calls": ["a"],
            "quarantined_messages": 4,
            "quarantined_chars": 900,
            "answer_chars": 100,
        }
    ]

    def unused_session() -> ApolloSession:
        raise AssertionError("an empty evaluation should not create a session")

    report = phase2.evaluate([], unused_session, fake_runtime)
    report["results"] = [phase2.asdict(result)]
    report["quarantine"] = {
        "delegations": 1,
        "coordinator_received_chars": 100,
        "quarantined_chars": 900,
    }
    text = phase2.markdown_report(report)
    assert (
        "90% of the total" in text and "| t | s | 1 | 100 chars | 4 messages, 900 chars |" in text
    )
    assert json.dumps(report)  # the JSON report is serialisable
