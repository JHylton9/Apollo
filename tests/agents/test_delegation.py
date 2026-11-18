from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage

from apollo.agents.delegation import build_delegation_tools
from apollo.retrieval.tables import FineRecord
from apollo.tools import _runtime

from .fakes import scripted


@pytest.fixture(autouse=True)
def fake_records(monkeypatch):
    store = SimpleNamespace(
        fines=[
            FineRecord(115, "Operating Without Driver's Licence", 40000, 14, "Section 20(4)", 3),
            FineRecord(72, "Failing To Yield At Pedestrian Crossing", 10000, 4, "Section 83(3)", 2),
        ],
        divisions=[],
        murder_counts={},
    )
    monkeypatch.setattr(_runtime, "get_records", lambda: store)


def _calls(*calls):
    return AIMessage(
        content="",
        tool_calls=[{"name": n, "args": a, "id": f"c{i}"} for i, (n, a) in enumerate(calls)],
    )


def test_only_the_final_answer_reaches_the_coordinator() -> None:
    model = scripted(
        _calls(
            ("lookup_traffic_fine", {"section": "20(4)", "offence": "without licence"}),
            ("lookup_traffic_fine", {"section": "83(3)", "offence": "yield crossing"}),
        ),
        _calls(("calculate", {"expression": "40000 + 10000"})),
        AIMessage(content="Total: $50,000. Sources: JCF-Fines.pdf p2, p3"),
    )
    ask_traffic, _ = build_delegation_tools(model)

    message = ask_traffic.invoke(
        {
            "type": "tool_call",
            "id": "d1",
            "name": "ask_traffic_specialist",
            "args": {"task": "Combined fine for Section 20(4) and Section 83(3)"},
        }
    )

    # What the coordinator's model reads: one short answer.
    assert message.content == "Total: $50,000. Sources: JCF-Fines.pdf p2, p3"
    assert "No. 115" not in message.content  # raw tool output stayed in the specialist
    # What the UI and report get: proof of what happened inside.
    telemetry = message.artifact
    assert telemetry["subagent"] == "traffic_fine_specialist"
    assert telemetry["tool_calls"] == ["lookup_traffic_fine", "lookup_traffic_fine", "calculate"]
    assert telemetry["quarantined_messages"] == 6
    assert {c["page"] for c in telemetry["citations"]} == {2, 3}


def test_empty_task_is_rejected() -> None:
    ask_traffic, _ = build_delegation_tools(scripted(AIMessage(content="unused")))
    with pytest.raises(ValueError):
        ask_traffic.invoke({"task": "  "})