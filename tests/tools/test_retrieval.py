import pytest

from apollo.models import SearchHit
from apollo.tools import _runtime, retrieval


class FakeStore:
    """Stands in for Chroma so the tool logic is tested without a built index."""

    def __init__(self, hits: list[SearchHit]) -> None:
        self.hits = hits
        self.calls: list[dict] = []

    def query(self, pipeline, query, top_k=5, sources=None):
        self.calls.append({"pipeline": pipeline, "query": query, "sources": sources})
        return self.hits


def _call(tool, query: str):
    # Invoking with a full tool call returns a ToolMessage, which carries the artifact.
    call = {"type": "tool_call", "id": "t1", "name": tool.name, "args": {"query": query}}
    return tool.invoke(call)


def test_fine_search_is_scoped_and_cited(monkeypatch) -> None:
    hit = SearchHit(
        text="No Driver's Licence $40,000 Section 20(4)",
        score=0.91,
        source="JCF-Fines.pdf",
        page=1,
    )
    store = FakeStore([hit])
    monkeypatch.setattr(_runtime, "get_store", lambda: store)

    message = _call(retrieval.search_traffic_fines, "no licence")

    assert store.calls[0]["sources"] == ["JCF-Fines.pdf"]
    assert store.calls[0]["pipeline"] == "docling"
    assert "JCF-Fines.pdf, page 1" in message.content
    assert message.artifact == [
        {"rank": 1, "source": "JCF-Fines.pdf", "page": 1, "score": 0.91, "pipeline": "docling"}
    ]


def test_no_hits_returns_readable_message(monkeypatch) -> None:
    monkeypatch.setattr(_runtime, "get_store", lambda: FakeStore([]))
    message = _call(retrieval.search_wanted_persons, "unknown person")
    assert "No matching records" in message.content
    assert message.artifact == []


def test_empty_query_is_rejected() -> None:
    with pytest.raises(ValueError):
        retrieval.search_traffic_fines.invoke({"query": "   "})


def test_missing_persons_use_baseline_ocr(monkeypatch) -> None:
    store = FakeStore([])
    monkeypatch.setattr(_runtime, "get_store", lambda: store)
    monkeypatch.delenv("APOLLO_RETRIEVER", raising=False)
    _call(retrieval.search_missing_persons, "Tiana Williams")
    assert store.calls[0]["pipeline"] == "baseline"


def test_environment_can_force_one_pipeline(monkeypatch) -> None:
    store = FakeStore([])
    monkeypatch.setattr(_runtime, "get_store", lambda: store)
    monkeypatch.setenv("APOLLO_RETRIEVER", "docling")
    _call(retrieval.search_missing_persons, "Tiana Williams")
    assert store.calls[0]["pipeline"] == "docling"
