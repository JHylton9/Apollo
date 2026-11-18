from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from apollo.agents.subagents import build_crime_analyst, build_traffic_specialist
from apollo.retrieval.tables import CategoryChange, DivisionStats, FineRecord
from apollo.tools import _runtime

from .fakes import scripted


@pytest.fixture(autouse=True)
def fake_records(monkeypatch):
    store = SimpleNamespace(
        fines=[
            FineRecord(
                115,
                "Operating Motor Vehicle Without Driver's Licence/Permit",
                40000,
                14,
                "Section 20(4)",
                3,
            ),
        ],
        divisions=[
            DivisionStats("St. Andrew North", {"grand_total": CategoryChange(250, 101)}, ())
        ],
        murder_counts={},
    )
    monkeypatch.setattr(_runtime, "get_records", lambda: store)


def _tool_call(name, args, call_id="c1"):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


def test_traffic_specialist_runs_its_own_tools() -> None:
    model = scripted(
        _tool_call("lookup_traffic_fine", {"section": "20(4)", "offence": "without licence"}),
        AIMessage(content="Section 20(4): $40,000, 14 points. Sources: JCF-Fines.pdf p3"),
    )
    result = build_traffic_specialist(model).invoke(
        {"messages": [{"role": "user", "content": "Fine for driving without a licence?"}]}
    )
    tool_messages = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    assert tool_messages[0].name == "lookup_traffic_fine"
    assert "$40,000" in tool_messages[0].content
    assert result["messages"][-1].content.startswith("Section 20(4): $40,000")


def test_specialists_only_get_their_domain_tools() -> None:
    traffic = build_traffic_specialist(scripted(AIMessage(content="ok")))
    crime = build_crime_analyst(scripted(AIMessage(content="ok")))
    traffic_tools = set(getattr(traffic.get_graph().nodes["tools"].data, "tools_by_name", {}))
    crime_tools = set(getattr(crime.get_graph().nodes["tools"].data, "tools_by_name", {}))
    assert "lookup_traffic_fine" in traffic_tools
    assert "rank_divisions_by_change" not in traffic_tools
    assert "rank_divisions_by_change" in crime_tools
    assert "lookup_traffic_fine" not in crime_tools
    # Neither specialist can take high-risk actions; those stay with the coordinator.
    assert not {"issue_fine_notice", "notify_email"} & (traffic_tools | crime_tools)