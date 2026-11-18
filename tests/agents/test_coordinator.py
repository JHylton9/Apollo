from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from apollo.agents.coordinator import build_coordinator, thread_config
from apollo.agents.delegation import build_delegation_tools
from apollo.retrieval.tables import FineRecord
from apollo.tools import _runtime

from .fakes import scripted


@pytest.fixture(autouse=True)
def fake_records(monkeypatch):
    store = SimpleNamespace(
        fines=[FineRecord(15, "Disobeying Stop Sign", 10000, 6, "Section 52(2)(a)", 1)],
        divisions=[],
        murder_counts={},
    )
    monkeypatch.setattr(_runtime, "get_records", lambda: store)


def _call(name, args, call_id):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


def test_coordinator_delegates_and_receives_only_the_answer() -> None:
    specialist_model = scripted(
        _call("lookup_traffic_fine", {"section": "52(2)(a)"}, "s1"),
        AIMessage(content="Section 52(2)(a): $10,000, 6 points. Sources: JCF-Fines.pdf p1"),
    )
    coordinator_model = scripted(
        _call("ask_traffic_specialist", {"task": "Fine for Section 52(2)(a)?"}, "d1"),
        AIMessage(content="The fine is $10,000 with 6 points. Sources: JCF-Fines.pdf p1"),
    )
    agent = build_coordinator(
        coordinator_model, delegation_tools=build_delegation_tools(specialist_model)
    )

    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What is the stop sign fine?"}]},
        thread_config("t1"),
    )

    tool_results = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    assert [m.name for m in tool_results] == ["ask_traffic_specialist"]
    # The specialist's lookup ran, but its raw output is not in the coordinator's history.
    assert tool_results[0].artifact["tool_calls"] == ["lookup_traffic_fine"]
    assert not any("No. 15 |" in str(m.content) for m in result["messages"])
    assert result["messages"][-1].content.startswith("The fine is $10,000")


def test_checkpointer_remembers_earlier_turns() -> None:
    agent = build_coordinator(
        scripted(AIMessage(content="Hello."), AIMessage(content="You asked about fines.")),
        delegation_tools=[],
    )
    config = thread_config("officer-42")
    agent.invoke({"messages": [{"role": "user", "content": "Hi"}]}, config)
    result = agent.invoke({"messages": [{"role": "user", "content": "What did I ask?"}]}, config)
    # Both turns are in the thread's saved state: 2 user + 2 assistant messages.
    assert [m.type for m in result["messages"]] == ["human", "ai", "human", "ai"]


def test_coordinator_owns_registry_and_action_tools() -> None:
    agent = build_coordinator(scripted(AIMessage(content="ok")), delegation_tools=[])
    names = set(agent.get_graph().nodes["tools"].data.tools_by_name)
    assert {"search_wanted_persons", "issue_fine_notice", "log_sighting_report"} <= names
    assert "lookup_traffic_fine" not in names  # traffic lookups go through the specialist

def test_prompt_explains_every_review_outcome() -> None:
    from apollo.agents.coordinator import COORDINATOR_PROMPT

    for outcome in ("Approved:", "Edited:", "Rejected:", "Responded:"):
        assert outcome in COORDINATOR_PROMPT
    assert "Never invent values" in COORDINATOR_PROMPT