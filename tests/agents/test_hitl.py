import json
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.types import Command

from apollo.agents.coordinator import build_coordinator, thread_config
from apollo.middleware import build_hitl_middleware
from apollo.retrieval.tables import CategoryChange, DivisionStats
from apollo.tools import _runtime

from .fakes import scripted

SIGHTING = {"suspect_name": "Dave Edwards", "location": "Kingston Central", "anonymous": True}


@pytest.fixture(autouse=True)
def fake_runtime(monkeypatch, tmp_path):
    divisions = [
        DivisionStats(name, {"murder": CategoryChange(1, 1)}, ())
        for name in ("Kingston Central", "St. Andrew South")
    ]
    records = SimpleNamespace(fines=[], divisions=divisions, murder_counts={})
    monkeypatch.setattr(_runtime, "get_records", lambda: records)
    monkeypatch.setattr(_runtime, "get_settings", lambda: SimpleNamespace(actions_dir=tmp_path))
    return tmp_path


def _agent(final_reply: str):
    model = scripted(
        AIMessage(
            content="",
            tool_calls=[{"name": "log_sighting_report", "args": SIGHTING, "id": "a1"}],
        ),
        AIMessage(content=final_reply),
    )
    return build_coordinator(model, delegation_tools=[], middleware=[build_hitl_middleware()])


def _start(agent, thread_id):
    config = thread_config(thread_id)
    request = "Log an anonymous sighting of Dave Edwards at Kingston Central."
    result = agent.invoke({"messages": [{"role": "user", "content": request}]}, config)
    return result, config


def _sightings(folder):
    path = folder / "sighting_reports.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def test_high_risk_call_pauses_before_running(fake_runtime) -> None:
    result, _ = _start(_agent("unused"), "pause")
    review = result["__interrupt__"][0].value
    assert review["action_requests"][0]["name"] == "log_sighting_report"
    assert review["action_requests"][0]["args"]["location"] == "Kingston Central"
    assert review["review_configs"][0]["allowed_decisions"] == [
        "approve",
        "edit",
        "reject",
        "respond",
    ]
    assert _sightings(fake_runtime) == []  # nothing has been written yet


def test_approve_runs_the_call(fake_runtime) -> None:
    agent = _agent("Report logged.")
    _, config = _start(agent, "approve")
    agent.invoke(Command(resume={"decisions": [{"type": "approve"}]}), config)
    assert _sightings(fake_runtime)[0]["division"] == "Kingston Central"


def test_edit_runs_the_call_with_corrected_arguments(fake_runtime) -> None:
    # Spec test case: the reviewer changes the location before the report is logged.
    agent = _agent("Report logged for St. Andrew South.")
    _, config = _start(agent, "edit")
    edited = {**SIGHTING, "location": "St. Andrew South"}
    decision = {"type": "edit", "edited_action": {"name": "log_sighting_report", "args": edited}}
    agent.invoke(Command(resume={"decisions": [decision]}), config)
    assert [s["division"] for s in _sightings(fake_runtime)] == ["St. Andrew South"]


def test_reject_skips_the_call_and_tells_the_model(fake_runtime) -> None:
    agent = _agent("The report was not logged.")
    _, config = _start(agent, "reject")
    decision = {"type": "reject", "message": "Duplicate report already on file."}
    result = agent.invoke(Command(resume={"decisions": [decision]}), config)
    assert _sightings(fake_runtime) == []
    feedback = [m for m in result["messages"] if isinstance(m, ToolMessage)][-1]
    assert "Duplicate report" in feedback.content


def test_respond_answers_in_place_of_the_tool(fake_runtime) -> None:
    agent = _agent("An officer has taken over this report.")
    _, config = _start(agent, "respond")
    decision = {"type": "respond", "message": "Officer Brown is handling this sighting directly."}
    result = agent.invoke(Command(resume={"decisions": [decision]}), config)
    assert _sightings(fake_runtime) == []
    tool_result = [m for m in result["messages"] if isinstance(m, ToolMessage)][-1]
    assert tool_result.content == "Officer Brown is handling this sighting directly."


def test_every_high_risk_tool_is_gated() -> None:
    gated = set(build_hitl_middleware().interrupt_on)
    assert gated == {"issue_fine_notice", "notify_email", "log_sighting_report"}
