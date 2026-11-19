from types import SimpleNamespace
from typing import cast

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from apollo.agents.coordinator import build_coordinator
from apollo.agents.delegation import build_delegation_tools
from apollo.agents.session import ApolloSession
from apollo.middleware import build_pii_middleware, coordinator_middleware, redact_text
from apollo.retrieval.tables import FineRecord
from apollo.tools import _runtime

from .fakes import ScriptedModel

JANE = (
    "My name is Jane Doe, TRN 987-654-321, email jane.doe@example.com. "
    "Check if I have any recorded fines for no valid certificate of fitness."
)


class RecordingModel(ScriptedModel):
    """A scripted model that also records every message list it was given."""

    def _generate(self, messages, *args, **kwargs):
        SEEN.append([str(m.content) for m in messages])
        return super()._generate(messages, *args, **kwargs)


SEEN: list[list[str]] = []


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    SEEN.clear()
    fines = [FineRecord(88, "No Valid Certificate Of Fitness", 15000, 0, "Section 7(3)", 2)]
    records = SimpleNamespace(fines=fines, divisions=[], murder_counts={})
    monkeypatch.setattr(_runtime, "get_records", lambda: records)


def test_trn_and_email_are_redacted_but_other_numbers_are_not() -> None:
    text, found = redact_text(JANE + " Tip line 876-838-3589, fine $40,000 in 2025, 20(4).")
    assert "987-654-321" not in text and "jane.doe@example.com" not in text
    assert "[REDACTED_TRN]" in text and "[REDACTED_EMAIL]" in text
    assert "876-838-3589" in text and "$40,000" in text and "2025" in text
    assert found == ["email", "trn"]
    assert redact_text("987654321 and 987 654 321")[0] == "[REDACTED_TRN] and [REDACTED_TRN]"


def test_no_model_and_no_checkpoint_ever_holds_raw_pii() -> None:
    # Spec test case: Jane Doe's TRN and email are redacted; the fine is still answered.
    specialist = RecordingModel(
        messages=iter(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "lookup_traffic_fine",
                            "args": {"offence": "no valid certificate of fitness"},
                            "id": "s1",
                        }
                    ],
                ),
                AIMessage(content="Section 7(3): $15,000. Sources: JCF-Fines.pdf p2"),
            ]
        )
    )
    coordinator = RecordingModel(
        messages=iter(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "ask_traffic_specialist",
                            "args": {"task": "Fine for no valid certificate of fitness"},
                            "id": "d1",
                        }
                    ],
                ),
                AIMessage(content="The fine under Section 7(3) is $15,000."),
            ]
        )
    )
    agent = build_coordinator(
        coordinator,
        delegation_tools=build_delegation_tools(specialist),
        middleware=coordinator_middleware(),
    )
    session = ApolloSession(agent, "pii")

    turn = session.ask(JANE)

    assert turn.answer == "The fine under Section 7(3) is $15,000."
    assert turn.middleware_events[0] == {"middleware": "PII", "redacted": ["email", "trn"]}
    everything_models_saw = " ".join(" ".join(call) for call in SEEN)
    history = " ".join(
        str(m.content)
        for snapshot in agent.get_state_history(cast(RunnableConfig, session.config))
        for m in snapshot.values.get("messages", [])
    )
    for raw in ("987-654-321", "jane.doe@example.com"):
        assert raw not in everything_models_saw
        assert raw not in history  # every checkpoint, not just the latest


def test_in_graph_middleware_still_protects_direct_use() -> None:
    # Defence in depth: code that bypasses ApolloSession is still protected at the model.
    model = RecordingModel(messages=iter([AIMessage(content="ok")]))
    agent = build_coordinator(model, delegation_tools=[], middleware=build_pii_middleware())
    agent.invoke(
        {"messages": [{"role": "user", "content": JANE}]}, {"configurable": {"thread_id": "x"}}
    )
    assert "987-654-321" not in SEEN[0][-1] and "[REDACTED_TRN]" in SEEN[0][-1]


def test_stacks_put_pii_first() -> None:
    names = [m.name for m in coordinator_middleware()]
    assert names[:2] == ["PIIMiddleware[email]", "PIIMiddleware[trn]"]
